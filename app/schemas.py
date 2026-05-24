from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SourceCreate(BaseModel):
    source_type: str = Field(pattern="^(rss|webpage|pdf)$")
    name: str
    url: str | None = None
    local_path: str | None = None


class SourceRead(BaseModel):
    id: int
    source_type: str
    name: str
    url: str | None
    local_path: str | None
    status: str
    created_at: datetime
    last_ingested_at: datetime | None

    model_config = {"from_attributes": True}


class IngestionRunRead(BaseModel):
    id: int
    source_id: int
    started_at: datetime
    ended_at: datetime | None
    status: str
    documents_found: int
    documents_inserted: int
    chunks_inserted: int
    duplicates_skipped: int
    error_message: str | None

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchHit(BaseModel):
    chunk_id: int
    title: str
    source_name: str
    url: str | None
    local_path: str | None
    score: float
    snippet: str
    citation: str


class SearchResponse(BaseModel):
    query: str
    answer_markdown: str
    hits: list[SearchHit]


class BriefingRequest(BaseModel):
    topic: str
    top_k: int = 8


class BriefingRead(BaseModel):
    id: int
    query: str
    answer_markdown: str
    citation_json: str
    created_at: datetime

    model_config = {"from_attributes": True}

