"""Ingestion pipeline — orchestrates: parse → chunk → embed → store."""

import hashlib
import logging

from app.models.database import DocumentSource, SourceStatus
from app.models.schemas import IngestRequest
from app.services.parser import extract_text
from app.services.chunker import chunk_text
from app.services.embedder import embedder
from app.services.vector_store import vector_store
from app.core.config import settings

logger = logging.getLogger(__name__)


async def ingest_file(
    req: IngestRequest,
    db_session,
) -> DocumentSource:
    """
    Full ingestion pipeline for a single file from gxu-wjxt.

    1. Parse HTML → clean text
    2. Hash content (for change detection)
    3. Chunk text → list[Chunk]
    4. Embed chunks → vectors
    5. Store in ChromaDB
    6. Save metadata in SQLite

    Args:
        req: IngestRequest with file_id, title, department, date, raw_html.
        db_session: Async SQLAlchemy session.

    Returns:
        Updated DocumentSource record.
    """
    from sqlalchemy import select

    # Compute content hash for change detection
    content_hash = hashlib.sha256(req.raw_html.encode()).hexdigest()

    # Check if this file was already indexed with the same hash
    result = await db_session.execute(
        select(DocumentSource).where(DocumentSource.file_id == req.file_id)
    )
    existing = result.scalar_one_or_none()

    if existing and existing.content_hash == content_hash and existing.status == SourceStatus.indexed:
        logger.info(f"File {req.file_id} unchanged, skipping.")
        return existing

    # Create or update source record
    if existing:
        source = existing
        source.status = SourceStatus.indexing
    else:
        source = DocumentSource(
            file_id=req.file_id,
            title=req.title,
            department=req.department,
            date=req.date,
            content_hash=content_hash,
            status=SourceStatus.indexing,
        )
        db_session.add(source)
    await db_session.commit()

    try:
        # Step 1: Parse
        text = extract_text(req.raw_html)
        if not text or len(text) < 50:
            raise ValueError(f"Extracted text too short ({len(text)} chars)")

        # Step 2: Chunk
        chunks = chunk_text(
            text=text,
            file_id=req.file_id,
            title=req.title,
            department=req.department,
            date=req.date,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        if not chunks:
            raise ValueError("No chunks produced")

        # Step 3: Embed
        texts = [c.text for c in chunks]
        vectors = embedder.embed_texts(texts)

        # Step 4: Remove old chunks from vector store
        vector_store.delete_by_file_id(req.file_id)

        # Step 5: Store in vector store
        chunk_dicts = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"file{req.file_id}_chunk{i}"
            chunk_dicts.append({
                "id": chunk_id,
                "text": chunk.text,
                "embedding": vectors[i],
                "metadata": chunk.metadata,
            })

        added = vector_store.add_chunks(chunk_dicts)

        # Step 6: Update source record
        source.content_hash = content_hash
        source.status = SourceStatus.indexed
        source.chunk_count = added
        source.error_message = ""
        from datetime import datetime, timezone
        source.indexed_at = datetime.now(timezone.utc)
        await db_session.commit()

        logger.info(f"Indexed file {req.file_id} '{req.title}': {added} chunks")
        return source

    except Exception as e:
        source.status = SourceStatus.error
        source.error_message = str(e)
        await db_session.commit()
        logger.error(f"Failed to index file {req.file_id}: {e}")
        raise
