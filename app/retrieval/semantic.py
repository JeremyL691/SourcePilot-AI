from __future__ import annotations

from collections.abc import Callable

from app.openai_models import DEFAULT_EMBEDDING_MODEL


def embed_texts(
    texts: list[str],
    api_key: str | None,
    model: str = DEFAULT_EMBEDDING_MODEL,
    client_factory: Callable | None = None,
) -> list[list[float]]:
    if not texts or not api_key:
        return []
    client = client_factory(api_key) if client_factory else _default_client(api_key)
    response = client.embeddings.create(model=model, input=texts)
    data = getattr(response, "data", []) or []
    return [item.embedding for item in data]


def _default_client(api_key: str):
    from openai import OpenAI

    return OpenAI(api_key=api_key)
