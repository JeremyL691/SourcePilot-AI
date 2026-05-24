from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Source


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


def test_health_reports_ready_and_empty_stats():
    client, _ = _client()
    try:
        response = client.get("/health")
        payload = response.json()

        assert response.status_code == 200
        assert payload["status"] == "ready"
        assert payload["stats"]["sources"] == 0
        assert payload["stats"]["documents"] == 0
        assert payload["stats"]["chunks"] == 0
    finally:
        app.dependency_overrides.clear()


def test_demo_seed_is_idempotent():
    client, Session = _client()
    try:
        first = client.post("/demo/seed")
        second = client.post("/demo/seed")

        assert first.status_code == 200
        assert second.status_code == 200
        assert len(first.json()["sources"]) == 3
        assert len(second.json()["sources"]) == 3
        with Session() as db:
            assert len(db.query(Source).all()) == 3
    finally:
        app.dependency_overrides.clear()


def test_save_conversation_indexes_markdown():
    client, _ = _client()
    try:
        response = client.post(
            "/conversations/save",
            json={
                "title": "Research chat about retrieval",
                "markdown": "# Conversation Summary\n\nThe user asked about retrieval and citations.",
            },
        )
        payload = response.json()

        assert response.status_code == 200
        assert payload["documents_inserted"] == 1
        assert payload["chunks_inserted"] >= 1

        search = client.post("/search", json={"query": "retrieval citations", "source_type": "conversation"})
        assert search.status_code == 200
        assert search.json()["hits"]
    finally:
        app.dependency_overrides.clear()
