"""Pydantic schemas for API request/response."""

from datetime import datetime
from pydantic import BaseModel


# --- Chat ---

class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class SourceInfo(BaseModel):
    file_id: int
    title: str
    department: str
    date: str
    snippet: str


class ChatEvent(BaseModel):
    type: str  # "token" | "sources" | "done" | "error"
    data: str | list[SourceInfo] | None = None


# --- Admin ---

class IngestRequest(BaseModel):
    file_id: int
    title: str
    department: str
    date: str
    raw_html: str


class SourceResponse(BaseModel):
    id: str
    file_id: int
    title: str
    department: str
    date: str
    status: str
    chunk_count: int
    indexed_at: datetime | None
    created_at: datetime


class SystemStats(BaseModel):
    total_sources: int
    indexed_sources: int
    total_chunks: int
    error_sources: int


class ReindexResponse(BaseModel):
    source_id: str
    status: str
    message: str
