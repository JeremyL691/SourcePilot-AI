from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Collection, Source, Tag
from app.services.library import add_collection_item, add_item_tag, create_collection, create_tag
from app.services.pipeline import create_source


DEMO_COLLECTION = "Demo Knowledge Base"
DEMO_TAGS = [
    ("demo", "#2563eb"),
    ("python", "#16a34a"),
    ("ai", "#9333ea"),
]
DEMO_SOURCES = [
    {
        "source_type": "webpage",
        "name": "FastAPI Documentation",
        "url": "https://fastapi.tiangolo.com/",
    },
    {
        "source_type": "webpage",
        "name": "Streamlit Documentation",
        "url": "https://docs.streamlit.io/",
    },
    {
        "source_type": "rss",
        "name": "Hacker News Front Page",
        "url": "https://hnrss.org/frontpage",
    },
]


def seed_demo_data(db: Session) -> dict:
    collection = _get_or_create_collection(db)
    tags = [_get_or_create_tag(db, name, color) for name, color in DEMO_TAGS]
    sources = [_get_or_create_source(db, payload) for payload in DEMO_SOURCES]

    created_links = 0
    for source in sources:
        created_links += _safe_collection_link(db, collection.id, source.id)
        for tag in tags:
            created_links += _safe_tag_link(db, tag.id, source.id)

    return {
        "collection": {"id": collection.id, "name": collection.name},
        "tags": [{"id": tag.id, "name": tag.name} for tag in tags],
        "sources": [{"id": source.id, "name": source.name, "source_type": source.source_type} for source in sources],
        "created_links": created_links,
        "message": "Demo sources are ready. Run ingestion from the Start or Sources page when you want to index them.",
    }


def _get_or_create_collection(db: Session) -> Collection:
    collection = db.scalar(select(Collection).where(func.lower(Collection.name) == DEMO_COLLECTION.lower()))
    if collection:
        return collection
    return create_collection(db, DEMO_COLLECTION, "Opt-in demo sources for first-run exploration.")


def _get_or_create_tag(db: Session, name: str, color: str) -> Tag:
    tag = db.scalar(select(Tag).where(func.lower(Tag.name) == name.lower()))
    if tag:
        return tag
    return create_tag(db, name, color)


def _get_or_create_source(db: Session, payload: dict) -> Source:
    existing = db.scalar(select(Source).where(Source.url == payload["url"]))
    if existing:
        return existing
    return create_source(
        db,
        source_type=payload["source_type"],
        name=payload["name"],
        url=payload["url"],
    )


def _safe_collection_link(db: Session, collection_id: int, source_id: int) -> int:
    try:
        add_collection_item(db, collection_id, "source", source_id)
        return 1
    except ValueError:
        return 0


def _safe_tag_link(db: Session, tag_id: int, source_id: int) -> int:
    try:
        add_item_tag(db, tag_id, "source", source_id)
        return 1
    except ValueError:
        return 0
