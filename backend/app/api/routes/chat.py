"""Chat API — SSE streaming endpoint for document Q&A."""

import json
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.db.session import get_db
from app.models.database import Conversation, Message
from app.models.schemas import ChatRequest
from app.services.query_engine import query, get_sources
from app.services.agent import is_complex_query

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat endpoint with SSE streaming. Auto-routes to Workflow or Agent mode."""
    conversation_id = req.conversation_id or str(uuid.uuid4())
    result = await db.get(Conversation, conversation_id)
    if not result:
        conversation = Conversation(id=conversation_id, title=req.question[:50])
        db.add(conversation)
        await db.commit()

    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=req.question,
    )
    db.add(user_msg)
    await db.commit()

    use_agent = is_complex_query(req.question)

    async def event_stream():
        # Announce the conversation id so the frontend can track it
        yield {"event": "conversation", "data": json.dumps({"id": conversation_id})}

        sources_data = []

        if use_agent:
            # Agent mode: sources come inline as __SOURCES__: marker
            full_answer = ""
            sources_sent = False

            async for token in query(req.question, force_mode="agent"):
                if token.startswith("__SOURCES__:"):
                    # Parse inline sources from agent
                    try:
                        sources_data = json.loads(token[len("__SOURCES__:"):])
                        yield {"event": "sources", "data": json.dumps(sources_data, ensure_ascii=False)}
                        sources_sent = True
                    except json.JSONDecodeError:
                        pass
                else:
                    full_answer += token
                    yield {"event": "token", "data": token}

            if not sources_sent:
                yield {"event": "sources", "data": "[]"}

        else:
            # Workflow mode: pre-fetch sources
            sources = get_sources(req.question)
            sources_data = [
                {
                    "file_id": s.file_id,
                    "title": s.title,
                    "department": s.department,
                    "date": s.date,
                    "snippet": s.text[:200] + "..." if len(s.text) > 200 else s.text,
                }
                for s in sources
            ]
            yield {"event": "sources", "data": json.dumps(sources_data, ensure_ascii=False)}

            full_answer = ""
            async for token in query(req.question, force_mode="workflow"):
                full_answer += token
                yield {"event": "token", "data": token}

        # Save assistant message
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_answer,
            sources=json.dumps(sources_data, ensure_ascii=False),
        )
        db.add(assistant_msg)
        await db.commit()

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_stream())


@router.get("/api/conversations")
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """List all conversations."""
    from sqlalchemy import select
    result = await db.execute(select(Conversation).order_by(Conversation.created_at.desc()))
    conversations = result.scalars().all()
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
        for c in conversations
    ]


@router.get("/api/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get all messages for a conversation."""
    from sqlalchemy import select
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": json.loads(m.sources) if m.sources else [],
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.get("/api/conversations")
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """List all conversations."""
    from sqlalchemy import select
    result = await db.execute(select(Conversation).order_by(Conversation.created_at.desc()))
    conversations = result.scalars().all()
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
        for c in conversations
    ]


@router.get("/api/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, db: AsyncSession = Depends(get_db)):
    """Get all messages for a conversation."""
    from sqlalchemy import select
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": json.loads(m.sources) if m.sources else [],
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
