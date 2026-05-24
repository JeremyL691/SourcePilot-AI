from __future__ import annotations

import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db
from app.models import Briefing, Collection, Document, DocumentChunk, IngestionRun, Source, Tag
from app.retrieval.search import search_documents
from app.schemas import (
    BriefingRead,
    BriefingRequest,
    ChunkRead,
    CollectionCreate,
    CollectionRead,
    CollectionUpdate,
    ConversationSaveRequest,
    ConversationSaveResponse,
    DocumentRead,
    IngestionRunRead,
    ItemLink,
    SearchHit,
    SearchRequest,
    SearchResponse,
    SourceCreate,
    SourceRead,
    SourceUpdate,
    TagCreate,
    TagRead,
    TagUpdate,
)
from app.services.briefing import generate_briefing
from app.services.citations import answer_with_citations, citation_label
from app.services.conversations import save_conversation_markdown
from app.services.demo import seed_demo_data
from app.services.library import (
    add_collection_item,
    add_item_tag,
    create_collection,
    create_tag,
    delete_collection,
    delete_tag,
    list_documents as list_library_documents,
    remove_collection_item,
    remove_item_tag,
    update_collection,
    update_tag,
)
from app.services.pipeline import create_source, delete_source, ingest_source, platform_stats, update_source


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="SourcePilot AI", version="0.3.0", lifespan=lifespan)

@app.get("/")
def root() -> dict:
    return {"name": "SourcePilot AI", "status": "ready"}


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    return {
        "name": "SourcePilot AI",
        "status": "ready",
        "version": app.version,
        "api_port": settings.api_port,
        "dashboard_port": settings.dashboard_port,
        "database_url": settings.database_url,
        "stats": platform_stats(db),
    }


@app.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    return platform_stats(db)


@app.post("/demo/seed")
def seed_demo(db: Session = Depends(get_db)) -> dict:
    return seed_demo_data(db)


@app.post("/sources", response_model=SourceRead)
def add_source(payload: SourceCreate, db: Session = Depends(get_db)):
    try:
        return create_source(db, payload.source_type, payload.name, payload.url, payload.local_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/sources", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)):
    return db.scalars(select(Source).order_by(desc(Source.created_at))).all()


@app.patch("/sources/{source_id}", response_model=SourceRead)
def patch_source(source_id: int, payload: SourceUpdate, db: Session = Depends(get_db)):
    try:
        return update_source(db, source_id, payload.name, payload.url, payload.local_path, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/sources/{source_id}")
def remove_source(source_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        delete_source(db, source_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "source_id": source_id}


@app.post("/sources/{source_id}/ingest", response_model=IngestionRunRead)
def run_ingestion(source_id: int, db: Session = Depends(get_db)):
    try:
        return ingest_source(db, source_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/ingestion-runs", response_model=list[IngestionRunRead])
def list_ingestion_runs(db: Session = Depends(get_db)):
    return db.scalars(select(IngestionRun).order_by(desc(IngestionRun.started_at))).all()


@app.get("/documents", response_model=list[DocumentRead])
def list_documents(
    source_ids: list[int] | None = Query(default=None),
    source_type: str | None = None,
    collection_id: int | None = None,
    tags: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return [
        _document_read(document, source, include_text=False)
        for document, source in list_library_documents(db, source_ids, source_type, collection_id, tags)
    ]


@app.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        select(Document, Source).join(Source, Document.source_id == Source.id).where(Document.id == document_id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
    document, source = row
    return _document_read(document, source, include_text=True)


@app.get("/documents/{document_id}/chunks", response_model=list[ChunkRead])
def get_document_chunks(document_id: int, db: Session = Depends(get_db)):
    if not db.get(Document, document_id):
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
    return db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index)
    ).all()


@app.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    hits = search_documents(
        db,
        payload.query,
        top_k=payload.top_k,
        source_ids=payload.source_ids,
        source_type=payload.source_type,
        collection_id=payload.collection_id,
        tags=payload.tags,
    )
    return SearchResponse(
        query=payload.query,
        answer_markdown=answer_with_citations(payload.query, hits),
        hits=[
            SearchHit(
                chunk_id=hit.chunk_id,
                document_id=hit.document_id,
                source_id=hit.source_id,
                title=hit.title,
                source_name=hit.source_name,
                source_type=hit.source_type,
                url=hit.url,
                local_path=hit.local_path,
                score=hit.score,
                snippet=hit.snippet,
                citation=citation_label(hit, index),
                metadata=hit.metadata,
            )
            for index, hit in enumerate(hits, start=1)
        ],
    )


@app.post("/conversations/save", response_model=ConversationSaveResponse)
def save_conversation(payload: ConversationSaveRequest, db: Session = Depends(get_db)):
    try:
        return save_conversation_markdown(db, payload.title, payload.markdown)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/collections", response_model=list[CollectionRead])
def list_collections(db: Session = Depends(get_db)):
    return db.scalars(select(Collection).order_by(Collection.name)).all()


@app.post("/collections", response_model=CollectionRead)
def add_collection(payload: CollectionCreate, db: Session = Depends(get_db)):
    try:
        return create_collection(db, payload.name, payload.description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/collections/{collection_id}", response_model=CollectionRead)
def patch_collection(collection_id: int, payload: CollectionUpdate, db: Session = Depends(get_db)):
    try:
        return update_collection(db, collection_id, payload.name, payload.description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/collections/{collection_id}")
def remove_collection(collection_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        delete_collection(db, collection_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "collection_id": collection_id}


@app.post("/collections/{collection_id}/items")
def link_collection_item(collection_id: int, payload: ItemLink, db: Session = Depends(get_db)) -> dict:
    try:
        link = add_collection_item(db, collection_id, payload.item_type, payload.item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": link.id, "collection_id": collection_id, "item_type": payload.item_type, "item_id": payload.item_id}


@app.delete("/collections/{collection_id}/items")
def unlink_collection_item(collection_id: int, item_type: str, item_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        remove_collection_item(db, collection_id, item_type, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "deleted", "collection_id": collection_id, "item_type": item_type, "item_id": item_id}


@app.get("/tags", response_model=list[TagRead])
def list_tags(db: Session = Depends(get_db)):
    return db.scalars(select(Tag).order_by(Tag.name)).all()


@app.post("/tags", response_model=TagRead)
def add_tag(payload: TagCreate, db: Session = Depends(get_db)):
    try:
        return create_tag(db, payload.name, payload.color)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/tags/{tag_id}", response_model=TagRead)
def patch_tag(tag_id: int, payload: TagUpdate, db: Session = Depends(get_db)):
    try:
        return update_tag(db, tag_id, payload.name, payload.color)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/tags/{tag_id}")
def remove_tag(tag_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        delete_tag(db, tag_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted", "tag_id": tag_id}


@app.post("/tags/{tag_id}/items")
def link_tag_item(tag_id: int, payload: ItemLink, db: Session = Depends(get_db)) -> dict:
    try:
        link = add_item_tag(db, tag_id, payload.item_type, payload.item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": link.id, "tag_id": tag_id, "item_type": payload.item_type, "item_id": payload.item_id}


@app.delete("/tags/{tag_id}/items")
def unlink_tag_item(tag_id: int, item_type: str, item_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        remove_item_tag(db, tag_id, item_type, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "deleted", "tag_id": tag_id, "item_type": item_type, "item_id": item_id}


@app.post("/briefings", response_model=BriefingRead)
def create_briefing(payload: BriefingRequest, db: Session = Depends(get_db)):
    return generate_briefing(db, payload.topic, top_k=payload.top_k)


@app.get("/briefings", response_model=list[BriefingRead])
def list_briefings(db: Session = Depends(get_db)):
    return db.scalars(select(Briefing).order_by(desc(Briefing.created_at))).all()


@app.post("/upload-pdf", response_model=SourceRead)
def upload_pdf(name: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")
    settings.ensure_dirs()
    safe_name = Path(file.filename).name
    target = settings.raw_dir / safe_name
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return create_source(db, "pdf", name=name or safe_name, local_path=str(target))


def _document_read(document: Document, source: Source, include_text: bool) -> dict:
    return {
        "id": document.id,
        "source_id": document.source_id,
        "title": document.title,
        "url": document.url,
        "author": document.author,
        "published_at": document.published_at,
        "fetched_at": document.fetched_at,
        "content_hash": document.content_hash,
        "clean_text": document.clean_text if include_text else None,
        "source_name": source.name,
        "source_type": source.source_type,
    }
