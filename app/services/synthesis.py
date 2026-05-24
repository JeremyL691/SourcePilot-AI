from __future__ import annotations

from collections.abc import Callable

from app.retrieval.search import SearchResult
def synthesize_with_openai(
    query: str,
    hits: list[SearchResult],
    api_key: str | None,
    model: str | None,
    client_factory: Callable | None = None,
) -> str | None:
    if not api_key or not model or not hits:
        return None

    try:
        client = client_factory(api_key) if client_factory else _default_client(api_key)
        context = "\n\n".join(
            f"[{index}] {hit.title}\n{hit.chunk_text}" for index, hit in enumerate(hits, start=1)
        )
        prompt = "\n".join(
            [
                "Answer the user using only the indexed evidence below.",
                "Every factual claim must cite one or more source numbers like [1].",
                "If the evidence is insufficient, say so clearly.",
                "",
                f"Question: {query}",
                "",
                "Indexed evidence:",
                context,
            ]
        )
        response = client.responses.create(model=model, input=prompt)
        answer = getattr(response, "output_text", None)
        if not answer:
            return None
        if "Sources:" not in answer:
            answer = f"{answer.strip()}\n\n{_format_sources(hits)}"
        return answer
    except Exception:
        return None


def _default_client(api_key: str):
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def _format_sources(hits: list[SearchResult]) -> str:
    lines = ["Sources:"]
    for index, hit in enumerate(hits, start=1):
        if hit.source_type == "pdf":
            page = hit.metadata.get("page")
            location = hit.local_path or "local PDF"
            if page:
                location = f"{location} page {page}"
        else:
            location = hit.url or hit.source_name
        lines.append(f"[{index}] {hit.title} - {location}")
    return "\n".join(lines)
