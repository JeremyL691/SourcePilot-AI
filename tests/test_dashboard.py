from __future__ import annotations

from streamlit.testing.v1 import AppTest

import requests


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status_code = 200
        self.text = str(payload)

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_dashboard_renders_without_streamlit_widget_id_errors(monkeypatch):
    source = {
        "id": 1,
        "source_type": "webpage",
        "name": "Example Source",
        "url": "https://example.com",
        "local_path": None,
        "status": "active",
        "created_at": "2026-01-01T00:00:00",
        "last_ingested_at": None,
    }
    document = {
        "id": 1,
        "source_id": 1,
        "title": "Example Document",
        "url": "https://example.com",
        "author": None,
        "published_at": None,
        "fetched_at": "2026-01-01T00:00:00",
        "content_hash": "abc",
        "clean_text": "Example indexed text.",
        "source_name": "Example Source",
        "source_type": "webpage",
    }

    def fake_get(url, params=None, timeout=None):
        if url.endswith("/health"):
            return FakeResponse(
                {
                    "status": "ready",
                    "stats": {"sources": 1, "documents": 1, "chunks": 1, "ingestion_runs": 1},
                    "openai_configured": False,
                    "data_dir": "/tmp/fake",
                }
            )
        if url.endswith("/collections"):
            return FakeResponse([{"id": 1, "name": "Research", "description": "", "created_at": "2026-01-01T00:00:00"}])
        if url.endswith("/tags"):
            return FakeResponse([{"id": 1, "name": "demo", "color": "#4f46e5", "created_at": "2026-01-01T00:00:00"}])
        if url.endswith("/sources"):
            return FakeResponse([source])
        if url.endswith("/ingestion-runs"):
            return FakeResponse(
                [
                    {
                        "id": 1,
                        "source_id": 1,
                        "started_at": "2026-01-01T00:00:00",
                        "ended_at": "2026-01-01T00:00:01",
                        "status": "failed",
                        "documents_found": 0,
                        "documents_inserted": 0,
                        "chunks_inserted": 0,
                        "duplicates_skipped": 0,
                        "error_message": "403 Client Error: Forbidden",
                    }
                ]
            )
        if url.endswith("/documents"):
            return FakeResponse([document | {"clean_text": None}])
        if url.endswith("/documents/1"):
            return FakeResponse(document)
        if url.endswith("/documents/1/chunks"):
            return FakeResponse(
                [
                    {
                        "id": 1,
                        "document_id": 1,
                        "chunk_index": 0,
                        "chunk_text": "Example indexed text.",
                        "chunk_hash": "chunk",
                        "token_estimate": 3,
                        "metadata_json": "{}",
                        "embedding_id": None,
                    }
                ]
            )
        if url.endswith("/briefings"):
            return FakeResponse([])
        if url.endswith("/schedules"):
            return FakeResponse([])
        if url.endswith("/index/status"):
            return FakeResponse(
                {
                    "backend": "openai_embeddings_file_index",
                    "persisted": False,
                    "enabled": False,
                    "ready": False,
                    "embedding_model": "text-embedding-3-small",
                    "indexed_chunks": 0,
                    "total_chunks": 1,
                    "pending_chunks": 1,
                    "note": "Embeddings are stored locally in the app data directory and searched without an external vector database.",
                }
            )
        if url.endswith("/settings"):
            return FakeResponse(
                {
                    "openai_configured": False,
                    "openai_key_preview": None,
                    "openai_key_source": None,
                    "openai_model": "gpt-5.4-mini",
                    "data_dir": "/tmp/fake",
                }
            )
        return FakeResponse([])

    monkeypatch.setattr(requests, "get", fake_get)

    app = AppTest.from_file("dashboard/streamlit_app.py")
    app.run(timeout=60)

    assert not app.exception
    assert not app.error
