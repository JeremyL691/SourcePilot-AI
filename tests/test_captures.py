from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Document, Source
from app.services.captures import CapturePreview, QUICK_CAPTURE_SOURCE_NAME


def _client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)

    def override_db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), Session


def test_capture_parse_detects_empty_url_text_and_excerpt_cases():
    client, _ = _client()
    try:
        assert client.post("/captures/parse", json={"raw_text": ""}).json()["mode"] == "empty"
        assert client.post("/captures/parse", json={"raw_text": "https://example.com/post"}).json()["mode"] == "url_only"
        assert client.post("/captures/parse", json={"raw_text": "A saved note about retrieval"}).json()["mode"] == "text_only"
        mixed = client.post(
            "/captures/parse",
            json={"raw_text": "https://example.com/post\n\nThis quote matters for retrieval quality."},
        ).json()
        assert mixed["mode"] == "url_plus_excerpt"
        assert mixed["source_url"] == "https://example.com/post"
        assert "retrieval quality" in mixed["excerpt_text"]
    finally:
        app.dependency_overrides.clear()


def test_capture_parse_only_recognizes_http_and_https():
    client, _ = _client()
    try:
        payload = client.post("/captures/parse", json={"raw_text": "ftp://example.com/archive"}).json()
        assert payload["mode"] == "text_only"
        assert payload["source_url"] is None
    finally:
        app.dependency_overrides.clear()


def test_clip_capture_creates_quick_capture_source_and_is_searchable():
    client, Session = _client()
    try:
        response = client.post("/captures", json={"title": "Retrieval note", "excerpt_text": "Hybrid retrieval improves recall."})
        payload = response.json()

        assert response.status_code == 200
        assert payload["status"] == "saved"
        assert payload["capture_kind"] == "text_only"
        assert payload["document_id"] is not None

        with Session() as db:
            source = db.query(Source).filter_by(source_type="clip", name=QUICK_CAPTURE_SOURCE_NAME).one()
            assert source.id == payload["source_id"]

        search = client.post("/search", json={"query": "hybrid recall", "source_type": "clip"})
        assert search.status_code == 200
        assert search.json()["hits"]
    finally:
        app.dependency_overrides.clear()


def test_duplicate_clip_capture_returns_existing_document():
    client, _ = _client()
    try:
        first = client.post(
            "/captures",
            json={"title": "Retrieval note", "excerpt_text": "Hybrid retrieval improves recall."},
        ).json()
        second = client.post(
            "/captures",
            json={"title": "Retrieval note", "excerpt_text": "Hybrid retrieval improves recall."},
        ).json()

        assert second["status"] == "duplicate"
        assert second["duplicate"] is True
        assert second["document_id"] == first["document_id"]
    finally:
        app.dependency_overrides.clear()


def test_url_plus_excerpt_stays_as_clip_without_creating_webpage_source():
    client, Session = _client()
    try:
        response = client.post(
            "/captures",
            json={
                "title": "Useful quote",
                "source_url": "https://example.com/article#section",
                "excerpt_text": "This exact excerpt should be kept as a clip.",
            },
        )
        payload = response.json()

        assert response.status_code == 200
        assert payload["capture_kind"] == "url_plus_excerpt"

        with Session() as db:
            assert db.query(Source).filter_by(source_type="webpage").count() == 0
            assert db.query(Document).filter(Document.source_id == payload["source_id"]).count() == 1
    finally:
        app.dependency_overrides.clear()


def test_url_only_capture_upserts_existing_source_and_runs_ingest(monkeypatch):
    client, Session = _client()
    try:
        with Session() as db:
            source = Source(source_type="webpage", name="Example", url="https://example.com/article/")
            db.add(source)
            db.commit()
            source_id = source.id

        monkeypatch.setattr(
            "app.services.captures.ingest_source",
            lambda db, source_id: SimpleNamespace(
                id=9,
                status="success",
                documents_inserted=1,
                chunks_inserted=4,
                error_message=None,
            ),
        )

        payload = client.post("/captures", json={"source_url": "https://example.com/article"}).json()
        assert payload["status"] == "ingested"
        assert payload["source_created"] is False
        assert payload["source_id"] == source_id

        with Session() as db:
            assert db.query(Source).filter_by(source_type="webpage").count() == 1
    finally:
        app.dependency_overrides.clear()


def test_url_only_capture_respects_paused_source_status():
    client, Session = _client()
    try:
        with Session() as db:
            source = Source(source_type="webpage", name="Paused", url="https://example.com/article", status="paused")
            db.add(source)
            db.commit()
            source_id = source.id

        payload = client.post("/captures", json={"source_url": "https://example.com/article"}).json()
        assert payload["status"] == "paused"
        assert payload["source_id"] == source_id

        with Session() as db:
            source = db.get(Source, source_id)
            assert source.status == "paused"
    finally:
        app.dependency_overrides.clear()


def test_capture_clipboard_endpoint_returns_preview(monkeypatch):
    client, _ = _client()
    try:
        monkeypatch.setattr(
            "app.main.preview_clipboard",
            lambda: CapturePreview(
                mode="url_plus_excerpt",
                raw_text="https://example.com\nImportant note",
                source_url="https://example.com",
                excerpt_text="Important note",
                suggested_title="Important note",
            ),
        )
        response = client.get("/capture/clipboard")
        payload = response.json()

        assert response.status_code == 200
        assert payload["mode"] == "url_plus_excerpt"
        assert payload["source_url"] == "https://example.com"
    finally:
        app.dependency_overrides.clear()
