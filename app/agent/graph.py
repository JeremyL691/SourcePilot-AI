from __future__ import annotations


def classify_intent(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["ingest", "add source", "rss", "pdf", "url"]):
        return "ingestion"
    if any(word in lowered for word in ["briefing", "weekly", "report", "summary"]):
        return "briefing"
    if any(word in lowered for word in ["status", "failed", "logs"]):
        return "status"
    return "search"

