from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.pdf import ingest_pdf
from app.ingestion.quality import store_extracted_documents
from app.ingestion.rss import ingest_rss
from app.ingestion.webpage import ingest_webpage
from app.models import Document, DocumentChunk, IngestionRun, Source


def create_source(db: Session, source_type: str, name: str, url: str | None = None, local_path: str | None = None) -> Source:
    if source_type in {"rss", "webpage"} and not url:
        raise ValueError(f"{source_type} source requires a URL")
    if source_type == "pdf" and not local_path:
        raise ValueError("pdf source requires local_path")
    source = Source(source_type=source_type, name=name, url=url, local_path=local_path)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def ingest_source(db: Session, source_id: int) -> IngestionRun:
    source = db.get(Source, source_id)
    if not source:
        raise ValueError(f"Source not found: {source_id}")

    run = IngestionRun(source_id=source.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        if source.source_type == "rss":
            docs = ingest_rss(source.url or "")
        elif source.source_type == "webpage":
            docs = ingest_webpage(source.url or "")
        elif source.source_type == "pdf":
            docs = ingest_pdf(source.local_path or "")
        else:
            raise ValueError(f"Unsupported source type: {source.source_type}")

        stats = store_extracted_documents(db, source, docs)
        run.documents_found = stats["documents_found"]
        run.documents_inserted = stats["documents_inserted"]
        run.chunks_inserted = stats["chunks_inserted"]
        run.duplicates_skipped = stats["duplicates_skipped"]
        run.status = "success"
        run.ended_at = datetime.utcnow()
        source.last_ingested_at = run.ended_at
        source.status = "active"
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(IngestionRun, run.id)
        source = db.get(Source, source_id)
        if run:
            run.status = "failed"
            run.ended_at = datetime.utcnow()
            run.error_message = str(exc)
        if source:
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

