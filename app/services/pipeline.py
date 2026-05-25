from __future__ import annotations

import logging
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.pdf import ingest_pdf
from app.ingestion.quality import store_extracted_documents
from app.ingestion.rss import ingest_rss
from app.ingestion.webpage import ingest_webpage
from app.models import Document, DocumentChunk, IngestionRun, Source, utc_now
from app.services.library import cleanup_item_links
from app.services.semantic_index import index_new_chunks, remove_chunk_embeddings

logger = logging.getLogger(__name__)


class SourcePausedError(Exception):
    """Raised when ingestion is attempted on a paused source."""


_HTTP_CODE_RE = re.compile(r"\b(\d{3})\b")


def _sanitize_error(exc: Exception) -> str:
    """Distill an exception into something user-readable.

    Stores full repr to the logger so we can debug; only the short version
    is persisted to the DB and shown in the UI.
    """
    logger.exception("Ingestion failed", exc_info=exc)

    name = exc.__class__.__name__
    text = str(exc).strip()
    lowered = text.lower()

    # Order matters: network-level failures often embed port numbers (e.g., port=443)
    # that look like HTTP status codes. Check transport problems first.
    if "timeout" in lowered or "timed out" in lowered:
        return "Request timed out."
    if "name or service not known" in lowered or "nodename nor servname" in lowered:
        return "DNS lookup failed for that URL."
    if "ssl" in lowered or "certificate" in lowered:
        return "TLS / certificate error."
    if "encrypted" in lowered and "pdf" in lowered:
        return "PDF is encrypted and cannot be parsed."
    if "max retries exceeded" in lowered or "connection refused" in lowered or "connectionerror" in lowered:
        return "Could not reach the host. Check your network and the URL."

    # Only treat HTTP status codes when we have a real client-error-ish marker
    # (e.g., "403 Client Error", "HTTP 404 ...") — not bare numbers.
    http_match = re.search(r"(?:HTTP[/ ]|status(?:\s+code)?\s*[:=]?\s*|\b)(\d{3})\b\s*(?:Client Error|Server Error|Forbidden|Not Found|Unauthorized)", text, re.IGNORECASE)
    if not http_match:
        http_match = re.search(r"\b(\d{3})\s+(?:Client Error|Server Error|Forbidden|Not Found|Unauthorized)", text, re.IGNORECASE)
    if http_match:
        code = http_match.group(1)
        if code == "403":
            return "HTTP 403 — the site blocks automated readers."
        if code == "404":
            return "HTTP 404 — the page no longer exists."
        if code.startswith("5"):
            return f"HTTP {code} — the server returned an error."
        if code == "401":
            return "HTTP 401 — authentication required."
        if code == "429":
            return "HTTP 429 — rate limited. Try again later."

    # Fallback — keep it short, no traceback noise.
    short = text.splitlines()[0][:200] if text else name
    return f"{name}: {short}" if short and name not in short else short


def create_source(db: Session, source_type: str, name: str, url: str | None = None, local_path: str | None = None) -> Source:
    if source_type in {"rss", "webpage"} and not url:
        raise ValueError(f"{source_type} source requires a URL")
    if source_type == "pdf" and not local_path:
        raise ValueError("pdf source requires local_path")
    if source_type not in {"rss", "webpage", "pdf", "conversation"}:
        raise ValueError(f"Unsupported source type: {source_type}")
    source = Source(source_type=source_type, name=name, url=url, local_path=local_path)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def update_source(
    db: Session,
    source_id: int,
    name: str | None = None,
    url: str | None = None,
    local_path: str | None = None,
    status: str | None = None,
) -> Source:
    source = db.get(Source, source_id)
    if not source:
        raise ValueError(f"Source not found: {source_id}")
    if name is not None:
        source.name = name
    if url is not None:
        source.url = url
    if local_path is not None:
        source.local_path = local_path
    if status is not None:
        source.status = status
    if source.source_type in {"rss", "webpage"} and not source.url:
        raise ValueError(f"{source.source_type} source requires a URL")
    if source.source_type == "pdf" and not source.local_path:
        raise ValueError("pdf source requires local_path")
    db.commit()
    db.refresh(source)
    return source


def delete_source(db: Session, source_id: int) -> None:
    source = db.get(Source, source_id)
    if not source:
        raise ValueError(f"Source not found: {source_id}")
    document_ids = db.scalars(select(Document.id).where(Document.source_id == source_id)).all()
    chunk_ids = db.scalars(select(DocumentChunk.id).where(DocumentChunk.document_id.in_(document_ids))).all() if document_ids else []
    cleanup_item_links(db, "source", [source_id])
    cleanup_item_links(db, "document", list(document_ids))
    db.delete(source)
    db.commit()
    remove_chunk_embeddings(list(chunk_ids))


def ingest_source(db: Session, source_id: int) -> IngestionRun:
    source = db.get(Source, source_id)
    if not source:
        raise ValueError(f"Source not found: {source_id}")
    if source.status == "paused":
        raise SourcePausedError(
            f"Source {source_id} ({source.name!r}) is paused. Activate it before running ingestion."
        )

    previous_status = source.status
    run = IngestionRun(source_id=source.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        if source.source_type == "rss":
            docs = ingest_rss(source.url or "", fetch_full_articles=True)
        elif source.source_type == "webpage":
            docs = ingest_webpage(source.url or "")
        elif source.source_type == "pdf":
            docs = ingest_pdf(source.local_path or "")
        elif source.source_type == "conversation":
            docs = []
        else:
            raise ValueError(f"Unsupported source type: {source.source_type}")

        stats = store_extracted_documents(db, source, docs)
        run.documents_found = stats["documents_found"]
        run.documents_inserted = stats["documents_inserted"]
        run.chunks_inserted = stats["chunks_inserted"]
        run.duplicates_skipped = stats["duplicates_skipped"]
        run.status = "success"
        run.ended_at = utc_now()
        source.last_ingested_at = run.ended_at
        # Preserve a user-set "paused" if it sneaked in via a concurrent edit; otherwise mark active.
        if previous_status != "paused":
            source.status = "active"
        db.commit()
        try:
            index_new_chunks(db, [chunk_id for chunk_id in stats.get("chunk_ids_inserted", []) if chunk_id is not None])
        except Exception as exc:
            logger.warning("Semantic indexing failed after ingest for source %s: %s", source_id, exc)
    except Exception as exc:
        db.rollback()
        run = db.get(IngestionRun, run.id)
        source = db.get(Source, source_id)
        if run:
            run.status = "failed"
            run.ended_at = utc_now()
            run.error_message = _sanitize_error(exc)
        # Don't trample a user's pause: re-read current status (it could have been
        # paused while we were running) instead of trusting the pre-flight snapshot.
        if source and source.status != "paused" and previous_status != "paused":
            source.status = "failed"
        db.commit()
    db.refresh(run)
    return run


def platform_stats(db: Session) -> dict[str, int]:
    return {
        "sources": db.scalar(select(func.count(Source.id))) or 0,
        "documents": db.scalar(select(func.count(Document.id))) or 0,
        "chunks": db.scalar(select(func.count(DocumentChunk.id))) or 0,
        "ingestion_runs": db.scalar(select(func.count(IngestionRun.id))) or 0,
    }
