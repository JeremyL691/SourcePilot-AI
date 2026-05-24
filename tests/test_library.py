import pytest

from app.ingestion.chunking import sha256_text
from app.models import Document, DocumentChunk, Source
from app.retrieval.search import search_documents
from app.services.library import (
    add_collection_item,
    add_item_tag,
    create_collection,
    create_tag,
    list_documents,
)
from app.services.pipeline import delete_source, update_source


def _seed_document(db, source_type="webpage", title="Vector Notes", text="vector search retrieval evaluation"):
    source = Source(source_type=source_type, name=f"{source_type} source", url="https://example.com")
    db.add(source)
    db.commit()
    db.refresh(source)
    document = Document(
        source_id=source.id,
        title=title,
        url=source.url,
        author=None,
        published_at=None,
        content_hash=sha256_text(title, text),
        raw_text=text,
        clean_text=text,
    )
    db.add(document)
    db.flush()
    db.add(
        DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            chunk_text=text,
            chunk_hash=sha256_text("chunk", title, text),
            token_estimate=10,
            metadata_json="{}",
            embedding_id="test",
        )
    )
    db.commit()
    db.refresh(document)
    return source, document


def test_collection_and_tag_names_are_unique(db_session):
    create_collection(db_session, "Research")
    create_tag(db_session, "AI")
    with pytest.raises(ValueError):
        create_collection(db_session, "Research")
    with pytest.raises(ValueError):
        create_tag(db_session, "AI")


def test_attach_items_and_filter_documents(db_session):
    source, document = _seed_document(db_session)
    collection = create_collection(db_session, "RAG")
    tag = create_tag(db_session, "retrieval")
    add_collection_item(db_session, collection.id, "source", source.id)
    add_item_tag(db_session, tag.id, "document", document.id)

    by_collection = list_documents(db_session, collection_id=collection.id)
    by_tag = list_documents(db_session, tags=["retrieval"])

    assert [row[0].id for row in by_collection] == [document.id]
    assert [row[0].id for row in by_tag] == [document.id]


def test_search_filters_by_collection_and_tag(db_session):
    source, document = _seed_document(db_session, text="alpha vector retrieval")
    other_source, _ = _seed_document(db_session, title="Other", text="alpha unrelated material")
    collection = create_collection(db_session, "Selected")
    tag = create_tag(db_session, "keeper")
    add_collection_item(db_session, collection.id, "source", source.id)
    add_item_tag(db_session, tag.id, "source", source.id)

    hits = search_documents(db_session, "alpha", collection_id=collection.id, tags=["keeper"])

    assert hits
    assert {hit.source_id for hit in hits} == {source.id}
    assert other_source.id not in {hit.source_id for hit in hits}


def test_update_and_delete_source_cleans_library_links(db_session):
    source, document = _seed_document(db_session)
    collection = create_collection(db_session, "Cleanup")
    tag = create_tag(db_session, "cleanup")
    add_collection_item(db_session, collection.id, "source", source.id)
    add_item_tag(db_session, tag.id, "document", document.id)

    updated = update_source(db_session, source.id, name="Updated", status="paused")
    delete_source(db_session, updated.id)

    assert updated.name == "Updated"
    assert list_documents(db_session, collection_id=collection.id) == []
    assert list_documents(db_session, tags=["cleanup"]) == []

