from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SourceCreate(BaseModel):
    source_type: str = Field(pattern="^(rss|webpage|pdf|conversation)$")
    name: str
    url: str | None = None
    local_path: str | None = None


class SourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    local_path: str | None = None
    status: str | None = Field(default=None, pattern="^(active|paused|failed)$")


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
    source_ids: list[int] | None = None
    source_type: str | None = Field(default=None, pattern="^(rss|webpage|pdf|conversation)$")
    collection_id: int | None = None
    tags: list[str] | None = None


class SearchHit(BaseModel):
    chunk_id: int
    document_id: int
    source_id: int
    title: str
    source_name: str
    source_type: str
    url: str | None
    local_path: str | None
    score: float
    snippet: str
    citation: str
    metadata: dict


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


class DocumentRead(BaseModel):
    id: int
    source_id: int
    title: str
    url: str | None
    author: str | None
    published_at: str | None
    fetched_at: datetime
    content_hash: str
    clean_text: str | None = None
    source_name: str | None = None
    source_type: str | None = None

    model_config = {"from_attributes": True}


class ChunkRead(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    chunk_text: str
    chunk_hash: str
    token_estimate: int
    metadata_json: str
    embedding_id: str | None

    model_config = {"from_attributes": True}


class CollectionCreate(BaseModel):
    name: str
    description: str | None = None


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class CollectionRead(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str
    color: str | None = None


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class TagRead(BaseModel):
    id: int
    name: str
    color: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ItemLink(BaseModel):
    item_type: str = Field(pattern="^(source|document)$")
    item_id: int


class ConversationSaveRequest(BaseModel):
    title: str
    markdown: str


class ConversationSaveResponse(BaseModel):
    source_id: int
    status: str
    documents_found: int
    documents_inserted: int
    chunks_inserted: int
    duplicates_skipped: int
