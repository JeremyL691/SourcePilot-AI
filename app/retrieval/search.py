from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.chunking import clean_text, tokenize
from app.models import Document, DocumentChunk, Source
from app.services.library import document_filter_ids


@dataclass
class SearchResult:
    chunk_id: int
    document_id: int
    source_id: int
    title: str
    source_name: str
    source_type: str
    url: str | None
    local_path: str | None
    score: float
    snippet: str
    chunk_text: str
    metadata: dict


def search_documents(
    db: Session,
    query: str,
    top_k: int = 5,
    source_ids: list[int] | None = None,
    source_type: str | None = None,
    collection_id: int | None = None,
    tags: list[str] | None = None,
) -> list[SearchResult]:
    query_terms = tokenize(query)
    if not query_terms:
        return []

    allowed_doc_ids = document_filter_ids(db, source_ids, source_type, collection_id, tags)
    if allowed_doc_ids is not None and not allowed_doc_ids:
        return []

    stmt = (
        select(DocumentChunk, Document, Source)
        .join(Document, DocumentChunk.document_id == Document.id)
        .join(Source, Document.source_id == Source.id)
    )
    rows = db.execute(stmt).all()
    if allowed_doc_ids is not None:
        rows = [row for row in rows if row[1].id in allowed_doc_ids]
    if not rows:
        return []

    chunk_terms = [(row, Counter(tokenize(row[0].chunk_text))) for row in rows]
    doc_freq: Counter[str] = Counter()
    for _, terms in chunk_terms:
        doc_freq.update(terms.keys())

    query_counts = Counter(query_terms)
    total_docs = len(chunk_terms)
    scored: list[SearchResult] = []
    for (chunk, document, source), terms in chunk_terms:
        if not terms:
            continue
        score = 0.0
        for term, q_count in query_counts.items():
            if term not in terms:
                continue
            idf = math.log((1 + total_docs) / (1 + doc_freq[term])) + 1
            score += q_count * terms[term] * idf
        if score <= 0:
            continue
        score = score / math.sqrt(sum(v * v for v in terms.values()))
        metadata = json.loads(chunk.metadata_json or "{}")
        scored.append(
            SearchResult(
                chunk_id=chunk.id,
                document_id=document.id,
                source_id=source.id,
                title=document.title,
                source_name=source.name,
                source_type=source.source_type,
                url=document.url or source.url,
                local_path=metadata.get("local_path") or source.local_path,
                score=round(score, 4),
                snippet=_snippet(chunk.chunk_text, query_terms),
                chunk_text=chunk.chunk_text,
                metadata=metadata,
            )
        )

    return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]


def _snippet(text: str, query_terms: list[str], max_chars: int = 360) -> str:
    cleaned = clean_text(text)
    lower = cleaned.lower()
    positions = [lower.find(term.lower()) for term in query_terms if lower.find(term.lower()) >= 0]
    start = max(0, min(positions) - 90) if positions else 0
    snippet = cleaned[start : start + max_chars]
    prefix = "..." if start > 0 else ""
    suffix = "..." if start + max_chars < len(cleaned) else ""
    return f"{prefix}{snippet}{suffix}"
