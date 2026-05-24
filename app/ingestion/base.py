from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExtractedDocument:
    title: str
    raw_text: str
    clean_text: str
    url: str | None = None
    author: str | None = None
    published_at: str | None = None
    metadata: dict[str, str | int | None] = field(default_factory=dict)

