from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import Briefing
from app.retrieval.search import search_documents
from app.services.citations import format_sources, serialize_citations


def generate_briefing(db: Session, topic: str, top_k: int = 8) -> Briefing:
    hits = search_documents(db, topic, top_k=top_k)
    if not hits:
        answer = (
            f"# Briefing: {topic}\n\n"
            "No relevant indexed evidence was found. Ingest sources related to this topic before generating a briefing."
        )
        citations: list[dict] = []
    else:
        bullets = [f"- {hit.snippet} [{index}]" for index, hit in enumerate(hits, start=1)]
        answer = "\n".join([f"# Briefing: {topic}", "", "## Evidence Summary", *bullets, "", format_sources(hits)])
        citations = serialize_citations(hits)

    briefing = Briefing(query=topic, answer_markdown=answer, citation_json=json.dumps(citations, ensure_ascii=False))
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    return briefing

