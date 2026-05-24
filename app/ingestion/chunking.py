from __future__ import annotations

import hashlib
import re


WHITESPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    return WHITESPACE_RE.sub(" ", text).strip()


def sha256_text(*parts: str | None) -> str:
    value = "\n".join(part or "" for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in WORD_RE.finditer(text)]


def chunk_text(text: str, target_words: int = 180, overlap_words: int = 35) -> list[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []

    words = cleaned.split()
    if len(words) <= target_words:
        return [cleaned]

    chunks: list[str] = []
    start = 0
    step = max(1, target_words - overlap_words)
    while start < len(words):
        window = words[start : start + target_words]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + target_words >= len(words):
            break
        start += step
    return chunks

