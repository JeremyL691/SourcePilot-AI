from __future__ import annotations

from app.retrieval.search import SearchResult


def citation_label(hit: SearchResult, index: int) -> str:
    if hit.source_type == "pdf":
        page = hit.metadata.get("page")
        location = f"{hit.local_path or 'local PDF'}"
        if page:
            location = f"{location} page {page}"
    else:
        location = hit.url or hit.source_name
    return f"[{index}] {hit.title} - {location}"


def format_sources(hits: list[SearchResult]) -> str:
    if not hits:
        return ""
    lines = ["Sources:"]
    for index, hit in enumerate(hits, start=1):
        lines.append(citation_label(hit, index))
    return "\n".join(lines)


def answer_with_citations(query: str, hits: list[SearchResult]) -> str:
    if not hits:
        return (
            "I do not have enough indexed evidence to answer this question yet. "
            "Add or ingest relevant sources, then try again."
        )

    bullets = []
    for index, hit in enumerate(hits[:4], start=1):
        bullets.append(f"- {hit.snippet} [{index}]")
    return "\n".join(
        [
            f"### Answer: {query}",
            "Based only on indexed evidence:",
            *bullets,
            "",
            format_sources(hits),
        ]
    )


def serialize_citations(hits: list[SearchResult]) -> list[dict]:
    return [
        {
            "index": index,
            "chunk_id": hit.chunk_id,
            "title": hit.title,
            "source_name": hit.source_name,
            "url": hit.url,
            "local_path": hit.local_path,
            "page": hit.metadata.get("page"),
            "score": hit.score,
        }
        for index, hit in enumerate(hits, start=1)
    ]

