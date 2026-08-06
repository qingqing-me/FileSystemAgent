"""SQLAlchemy models for SQLite storage."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class SourceStatus(str, enum.Enum):
    pending = "pending"
    indexing = "indexing"
    indexed = "indexed"
    error = "error"


class DocumentSource(Base):
    __tablename__ = "document_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(Integer, unique=True, nullable=False)  # gxu-wjxt file ID
    title = Column(String(512), nullable=False)
    department = Column(String(256), default="")
    date = Column(String(32), default="")  # YYYY-MM-DD
    content_hash = Column(String(64), default="")
    status = Column(SAEnum(SourceStatus), default=SourceStatus.pending)
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, default="")
    indexed_at = Column(DateTime(timezone=True), default=None)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(256), default="新对话")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), nullable=False)
    role = Column(String(16), nullable=False)  # "user" or "assistant"
    content = Column(Text, default="")
    sources = Column(Text, default="[]")  # JSON string
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
