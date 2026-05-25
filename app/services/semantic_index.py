from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DocumentChunk
from app.retrieval.semantic import embed_texts
from app.retrieval.vector_store import (
    LocalIndexStatus,
    build_status,
    delete_embeddings,
    save_embeddings,
    search_similar,
    upsert_embeddings,
)
from app.services.user_settings import effective_openai_key


def semantic_index_enabled() -> bool:
    return bool(effective_openai_key())


def semantic_index_status(db: Session) -> LocalIndexStatus:
    total_chunks = db.scalar(select(func.count(DocumentChunk.id))) or 0
    return build_status(total_chunks=total_chunks, enabled=semantic_index_enabled())


def rebuild_semantic_index(db: Session) -> dict:
    key = effective_openai_key()
    if not key:
        status = semantic_index_status(db)
        return {
            "status": "disabled",
            "indexed_chunks": status.indexed_chunks,
            "total_chunks": status.total_chunks,
            "pending_chunks": status.pending_chunks,
            "detail": "No OpenAI API key configured. Semantic indexing is disabled.",
        }

    chunks = db.scalars(select(DocumentChunk).order_by(DocumentChunk.id)).all()
    embeddings = _build_chunk_embedding_map(chunks, api_key=key)
    save_embeddings({str(chunk_id): vector for chunk_id, vector in embeddings.items()})
    indexed = len(embeddings)
    status = semantic_index_status(db)
    return {
        "status": "rebuilt",
        "indexed_chunks": indexed,
        "total_chunks": status.total_chunks,
        "pending_chunks": status.pending_chunks,
    }


def index_new_chunks(db: Session, chunk_ids: list[int]) -> dict:
    key = effective_openai_key()
    if not key:
        return {"status": "disabled", "indexed_chunks": 0}
    if not chunk_ids:
        return {"status": "noop", "indexed_chunks": 0}
    chunks = db.scalars(
        select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids)).order_by(DocumentChunk.id)
    ).all()
    indexed = _embed_and_store_chunks(chunks, api_key=key)
    return {"status": "indexed", "indexed_chunks": indexed}


def remove_chunk_embeddings(chunk_ids: list[int]) -> int:
    return delete_embeddings(chunk_ids)


def embed_query_text(query: str) -> list[float] | None:
    key = effective_openai_key()
    if not key or not query.strip():
        return None
    embeddings = embed_texts([query], api_key=key)
    return embeddings[0] if embeddings else None


def semantic_chunk_scores(query: str, *, allowed_chunk_ids: set[int] | None = None, top_k: int = 5) -> list[tuple[int, float]]:
    query_embedding = embed_query_text(query)
    if not query_embedding:
        return []
    return search_similar(query_embedding, top_k=top_k, allowed_chunk_ids=allowed_chunk_ids)


def _embed_and_store_chunks(chunks: list[DocumentChunk], *, api_key: str, batch_size: int = 32) -> int:
    embeddings = _build_chunk_embedding_map(chunks, api_key=api_key, batch_size=batch_size)
    return upsert_embeddings(embeddings)


def _build_chunk_embedding_map(
    chunks: list[DocumentChunk],
    *,
    api_key: str,
    batch_size: int = 32,
) -> dict[int, list[float]]:
    if not chunks:
        return {}
    embeddings: dict[int, list[float]] = {}
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = embed_texts([chunk.chunk_text for chunk in batch], api_key=api_key)
        if len(vectors) != len(batch):
            raise ValueError("Embedding response length did not match chunk batch size")
        embeddings.update({chunk.id: vector for chunk, vector in zip(batch, vectors)})
    return embeddings
