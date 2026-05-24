from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db
from app.models import Briefing, IngestionRun, Source
from app.retrieval.search import search_documents
from app.schemas import (
    BriefingRead,
    BriefingRequest,
    IngestionRunRead,
    SearchHit,
    SearchRequest,
    SearchResponse,
    SourceCreate,
    SourceRead,
)
from app.services.briefing import generate_briefing
from app.services.citations import answer_with_citations, citation_label
from app.services.pipeline import create_source, ingest_source, platform_stats


app = FastAPI(title="SourcePilot AI", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def root() -> dict:
    return {"name": "SourcePilot AI", "status": "ready"}


@app.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    return platform_stats(db)


@app.post("/sources", response_model=SourceRead)
def add_source(payload: SourceCreate, db: Session = Depends(get_db)):
    try:
        return create_source(db, payload.source_type, payload.name, payload.url, payload.local_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/sources", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)):
    return db.scalars(select(Source).order_by(desc(Source.created_at))).all()


@app.post("/sources/{source_id}/ingest", response_model=IngestionRunRead)
def run_ingestion(source_id: int, db: Session = Depends(get_db)):
    try:
        return ingest_source(db, source_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/ingestion-runs", response_model=list[IngestionRunRead])
def list_ingestion_runs(db: Session = Depends(get_db)):
    return db.scalars(select(IngestionRun).order_by(desc(IngestionRun.started_at))).all()


@app.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, db: Session = Depends(get_db)):
    hits = search_documents(db, payload.query, top_k=payload.top_k)
    return SearchResponse(
        query=payload.query,
        answer_markdown=answer_with_citations(payload.query, hits),
        hits=[
            SearchHit(
                chunk_id=hit.chunk_id,
                title=hit.title,
                source_name=hit.source_name,
                url=hit.url,
                local_path=hit.local_path,
                score=hit.score,
                snippet=hit.snippet,
                citation=citation_label(hit, index),
            )
            for index, hit in enumerate(hits, start=1)
        ],
    )


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

