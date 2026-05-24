from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LocalIndexStatus:
    backend: str = "deterministic_tfidf"
    persisted: bool = False
    note: str = "MVP builds the lexical index from SQLite at query time so it works without external vector services."

