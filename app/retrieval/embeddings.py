from __future__ import annotations

from collections import Counter

from app.ingestion.chunking import tokenize


def term_vector(text: str) -> Counter[str]:
    return Counter(tokenize(text))

