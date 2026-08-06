"""Admin API — document source management and system stats."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.database import DocumentSource, SourceStatus
from app.models.schemas import IngestRequest, SourceResponse, SystemStats, ReindexResponse
from app.services.pipeline import ingest_file

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/ingest")
async def ingest(req: IngestRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingest a single file from gxu-wjxt into the vector store.

    The caller (ingestion script) sends the file metadata and raw HTML.
    """
    try:
        source = await ingest_file(req, db)
        return ReindexResponse(
            source_id=source.id,
            status=source.status.value,
            message=f"Indexed '{source.title}' with {source.chunk_count} chunks",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db)) -> list[SourceResponse]:
    """List all document sources."""
    result = await db.execute(
        select(DocumentSource).order_by(DocumentSource.created_at.desc())
    )
    sources = result.scalars().all()
    return [
        SourceResponse(
            id=s.id,
            file_id=s.file_id,
            title=s.title,
            department=s.department,
            date=s.date,
            status=s.status.value,
            chunk_count=s.chunk_count,
            indexed_at=s.indexed_at,
            created_at=s.created_at,
        )
        for s in sources
    ]


@router.post("/reindex/{source_id}")
async def reindex(source_id: str, db: AsyncSession = Depends(get_db)):
    """
    Trigger re-indexing of a source. Currently requires re-sending the HTML.
    For a full reindex, delete and re-ingest via the ingest endpoint.
    """
    source = await db.get(DocumentSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source.status = SourceStatus.pending
    await db.commit()

    return ReindexResponse(
        source_id=source.id,
        status="pending",
        message="Source marked for re-indexing. Please re-send via POST /api/admin/ingest.",
    )


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a document source and its vector chunks."""
    from app.services.vector_store import vector_store

    source = await db.get(DocumentSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    vector_store.delete_by_file_id(source.file_id)
    await db.delete(source)
    await db.commit()

    return {"message": f"Deleted source '{source.title}'"}


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)) -> SystemStats:
    """Get system statistics."""
    total_result = await db.execute(select(func.count(DocumentSource.id)))
    total_sources = total_result.scalar() or 0

    indexed_result = await db.execute(
        select(func.count(DocumentSource.id)).where(DocumentSource.status == SourceStatus.indexed)
    )
    indexed_sources = indexed_result.scalar() or 0

    error_result = await db.execute(
        select(func.count(DocumentSource.id)).where(DocumentSource.status == SourceStatus.error)
    )
    error_sources = error_result.scalar() or 0

    from app.services.vector_store import vector_store
    total_chunks = vector_store.count()

    return SystemStats(
        total_sources=total_sources,
        indexed_sources=indexed_sources,
        total_chunks=total_chunks,
        error_sources=error_sources,
    )
