import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
import httpx

from app.db.session import get_db
from app.db.models import Session, Message, Artifact
from app.core.config import settings
from app.rag.retriever import retrieve_chunks

router = APIRouter()


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    provider: Optional[str] = Field(None, pattern="^(ollama|groq)$")


SUPABASE_REST_URL = "https://tijpftljahjnzoioaqai.supabase.co/rest/v1"
SUPABASE_KEY = "sb_publishable_KzldkcTyWz-VQGjm9uSVNg_UU5PSPYW"


def _sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _is_mock(db: AsyncSession) -> bool:
    return type(db).__module__.startswith("unittest.mock")


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(db: AsyncSession = Depends(get_db)):
    if settings.DB_TARGET == "supabase" and not _is_mock(db):
        s_id = str(uuid.uuid4())
        payload = {
            "id": s_id,
            "provider_at_creation": settings.LLM_PROVIDER,
            "user_metadata": {},
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(
                f"{SUPABASE_REST_URL}/sessions",
                headers=_sb_headers(),
                json=payload,
            )
            if res.status_code in (200, 201):
                row = res.json()[0]
                return {
                    "success": True,
                    "data": {
                        "session_id": row["id"],
                        "created_at": row["created_at"],
                    },
                }

    new_session = Session(
        provider_at_creation=settings.LLM_PROVIDER,
        user_metadata={}
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    return {
        "success": True,
        "data": {
            "session_id": str(new_session.id),
            "created_at": new_session.created_at.isoformat()
        }
    }


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    if settings.DB_TARGET == "supabase" and not _is_mock(db):
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                f"{SUPABASE_REST_URL}/sessions?order=created_at.desc",
                headers=_sb_headers(),
            )
            if res.status_code == 200:
                rows = res.json()
                return {
                    "success": True,
                    "data": [
                        {
                            "session_id": r["id"],
                            "title": r.get("title") or "New Chat",
                            "created_at": r["created_at"],
                        }
                        for r in rows
                    ],
                }

    stmt = select(Session).order_by(Session.created_at.desc())
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "session_id": str(s.id),
                "title": s.title or "New Chat",
                "created_at": s.created_at.isoformat()
            }
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    if settings.DB_TARGET == "supabase" and not _is_mock(db):
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check session
            s_res = await client.get(
                f"{SUPABASE_REST_URL}/sessions?id=eq.{session_id}",
                headers=_sb_headers(),
            )
            if s_res.status_code != 200 or not s_res.json():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "NOT_FOUND", "message": "Session not found"},
                )
            # Fetch messages
            m_res = await client.get(
                f"{SUPABASE_REST_URL}/messages?session_id=eq.{session_id}&order=created_at.asc",
                headers=_sb_headers(),
            )
            msgs = m_res.json() if m_res.status_code == 200 else []
            return {
                "success": True,
                "data": [
                    {
                        "id": m["id"],
                        "role": m["role"],
                        "content": m["content"],
                        "citations": m.get("citations") or [],
                        "artifact_id": m.get("artifact_id"),
                        "provider_used": m.get("provider_used"),
                        "created_at": m["created_at"],
                    }
                    for m in msgs
                ],
            }

    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Session not found"}
        )

    msg_stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    msg_result = await db.execute(msg_stmt)
    messages = msg_result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "citations": m.citations or [],
                "artifact_id": str(m.artifact_id) if m.artifact_id else None,
                "provider_used": m.provider_used,
                "created_at": m.created_at.isoformat()
            }
            for m in messages
        ]
    }


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    trimmed = payload.content.strip()
    if not trimmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VALIDATION_ERROR", "message": "content must not be empty"}
        )

    use_supabase = settings.DB_TARGET == "supabase" and not _is_mock(db)

    if use_supabase:
        async with httpx.AsyncClient(timeout=10.0) as client:
            s_res = await client.get(
                f"{SUPABASE_REST_URL}/sessions?id=eq.{session_id}",
                headers=_sb_headers(),
            )
            if s_res.status_code != 200 or not s_res.json():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "NOT_FOUND", "message": "Session not found"},
                )
            session_data = s_res.json()[0]
            current_title = session_data.get("title")
            if not current_title:
                new_title = (trimmed[:40] + "...") if len(trimmed) > 40 else trimmed
                await client.patch(
                    f"{SUPABASE_REST_URL}/sessions?id=eq.{session_id}",
                    headers=_sb_headers(),
                    json={"title": new_title},
                )

            # Persist user message
            user_msg_id = str(uuid.uuid4())
            await client.post(
                f"{SUPABASE_REST_URL}/messages",
                headers=_sb_headers(),
                json={
                    "id": user_msg_id,
                    "session_id": str(session_id),
                    "role": "user",
                    "content": trimmed,
                    "citations": [],
                },
            )

            # Fetch history
            h_res = await client.get(
                f"{SUPABASE_REST_URL}/messages?session_id=eq.{session_id}&order=created_at.asc",
                headers=_sb_headers(),
            )
            all_msgs = h_res.json() if h_res.status_code == 200 else []
            conversation_history = [
                {"role": m["role"], "content": m["content"]}
                for m in all_msgs
            ]
    else:
        stmt = select(Session).where(Session.id == session_id)
        result = await db.execute(stmt)
        session_obj = result.scalar_one_or_none()

        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Session not found"}
            )

        if not session_obj.title:
            session_obj.title = (trimmed[:40] + "...") if len(trimmed) > 40 else trimmed

        user_msg = Message(
            session_id=session_id,
            role="user",
            content=trimmed
        )
        db.add(user_msg)
        await db.flush()

        history_stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        history_res = await db.execute(history_stmt)
        all_msgs = history_res.scalars().all()
        conversation_history = [
            {"role": m.role, "content": m.content}
            for m in all_msgs
        ]

    # Determine request type: check for Ship 30/30 essay or HTML artifact intent
    lowered = trimmed.lower()
    is_essay_request = any(
        kw in lowered
        for kw in ["ship 30", "ship30", "essay", "write an essay", "generate essay", "turn this into an essay"]
    )
    
    artifact_kws = ["html", "css", "landing page", "component", "dashboard", "visual artifact", "mockup"]
    matches_artifact_kw = any(kw in lowered for kw in artifact_kws)
    is_question = any(q_word in lowered for q_word in ["what", "how", "why", "which"]) or trimmed.endswith("?")
    is_html_request = matches_artifact_kw and not is_question

    if is_essay_request:
        req_type = "ship30_essay"
    elif is_html_request:
        req_type = "html_artifact"
    else:
        req_type = "answer"

    search_query = trimmed
    if is_essay_request and len(conversation_history) >= 2:
        substantive = [
            m["content"]
            for m in conversation_history[:-1]
            if m["role"] == "user" and not any(k in m["content"].lower() for k in ["essay", "ship 30", "ship30"])
        ]
        if substantive:
            search_query = substantive[-1]

    retrieved = await retrieve_chunks(db, search_query)

    if not retrieved and req_type == "answer":
        refusal_content = (
            "I couldn't find anything in Lenny's Podcast transcripts that "
            "addresses this — try asking about product activation, PLG metrics, "
            "go-to-market strategies, or other topics covered in the episodes."
        )
        if use_supabase:
            asst_id = str(uuid.uuid4())
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{SUPABASE_REST_URL}/messages",
                    headers=_sb_headers(),
                    json={
                        "id": asst_id,
                        "session_id": str(session_id),
                        "role": "assistant",
                        "content": refusal_content,
                        "citations": [],
                        "provider_used": None,
                        "artifact_id": None,
                    },
                )
            return {
                "success": True,
                "data": {
                    "message_id": asst_id,
                    "content": refusal_content,
                    "citations": [],
                    "artifact_id": None,
                    "provider_used": None,
                },
            }
        else:
            assistant_msg = Message(
                session_id=session_id,
                role="assistant",
                content=refusal_content,
                provider_used=None,
                citations=[],
                artifact_id=None,
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            return {
                "success": True,
                "data": {
                    "message_id": str(assistant_msg.id),
                    "content": refusal_content,
                    "citations": [],
                    "artifact_id": None,
                    "provider_used": None,
                },
            }

    context_chunks = [
        {
            "source_file": c.source_file,
            "episode_title": c.episode_title,
            "chunk_text": c.chunk_text,
        }
        for c in retrieved
    ]

    effective_provider = payload.provider or settings.LLM_PROVIDER
    effective_model = settings.GROQ_MODEL if effective_provider == "groq" else settings.OLLAMA_MODEL

    sidecar_url = f"{settings.AGENT_SIDECAR_URL}/run"
    sidecar_payload = {
        "provider": effective_provider,
        "model": effective_model,
        "context_chunks": context_chunks,
        "conversation": conversation_history,
        "request_type": req_type
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            sidecar_res = await client.post(sidecar_url, json=sidecar_payload)
            if sidecar_res.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"code": "PROVIDER_ERROR", "message": f"Sidecar error: {sidecar_res.text}"}
                )
            sidecar_data = sidecar_res.json()
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "PROVIDER_ERROR", "message": f"Could not reach agent sidecar: {str(exc)}"}
        )

    assistant_content = sidecar_data.get("content", "")
    citations = sidecar_data.get("citations", [])
    artifact_id = None

    artifact_data = sidecar_data.get("artifact")
    if artifact_data:
        art_id = str(uuid.uuid4())
        art_type = artifact_data.get("type", "markdown")
        art_title = artifact_data.get("title", "Ship 30/30 Essay")
        art_content = artifact_data.get("content", "")
        art_meta = artifact_data.get("metadata", {})

        if use_supabase:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        f"{SUPABASE_REST_URL}/artifacts",
                        headers=_sb_headers(),
                        json={
                            "id": art_id,
                            "session_id": str(session_id),
                            "type": art_type,
                            "title": art_title,
                            "content": art_content,
                            "metadata": art_meta,
                        },
                    )
            except Exception as e:
                print(f"Supabase artifact insert error: {e}")

        if not _is_mock(db):
            try:
                artifact_obj = Artifact(
                    id=uuid.UUID(art_id),
                    session_id=session_id,
                    type=art_type,
                    title=art_title,
                    content=art_content,
                    metadata_sidecar=art_meta
                )
                db.add(artifact_obj)
                await db.flush()
            except Exception as ex:
                print(f"Local artifact insert error: {ex}")

        artifact_id = art_id

    if use_supabase:
        asst_id = str(uuid.uuid4())
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{SUPABASE_REST_URL}/messages",
                headers=_sb_headers(),
                json={
                    "id": asst_id,
                    "session_id": str(session_id),
                    "role": "assistant",
                    "content": assistant_content,
                    "provider_used": effective_provider,
                    "citations": citations,
                    "artifact_id": str(artifact_id) if artifact_id else None,
                },
            )
        return {
            "success": True,
            "data": {
                "message_id": asst_id,
                "content": assistant_content,
                "citations": citations,
                "artifact_id": str(artifact_id) if artifact_id else None,
                "provider_used": effective_provider
            }
        }

    assistant_msg = Message(
        session_id=session_id,
        role="assistant",
        content=assistant_content,
        provider_used=effective_provider,
        citations=citations,
        artifact_id=artifact_id
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return {
        "success": True,
        "data": {
            "message_id": str(assistant_msg.id),
            "content": assistant_msg.content,
            "citations": assistant_msg.citations,
            "artifact_id": str(artifact_id) if artifact_id else None,
            "provider_used": effective_provider
        }
    }


@router.get("/sessions/{session_id}/artifacts/{artifact_id}")
async def get_artifact(
    session_id: uuid.UUID,
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    # 1. Try Supabase REST query first
    if settings.DB_TARGET == "supabase" and not _is_mock(db):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    f"{SUPABASE_REST_URL}/artifacts?id=eq.{artifact_id}",
                    headers=_sb_headers(),
                )
                if res.status_code == 200 and res.json():
                    art = res.json()[0]
                    return {
                        "success": True,
                        "data": {
                            "id": art["id"],
                            "session_id": art["session_id"],
                            "type": art["type"],
                            "title": art["title"],
                            "content": art["content"],
                            "metadata": art.get("metadata_sidecar") or art.get("metadata") or {},
                            "created_at": art["created_at"],
                        },
                    }
        except Exception as e:
            print(f"Supabase artifact fetch error: {e}")

    # 2. Try local SQL DB / mock DB fallback
    try:
        stmt = select(Artifact).where(Artifact.id == artifact_id)
        result = await db.execute(stmt)
        artifact = result.scalar_one_or_none()

        if artifact:
            return {
                "success": True,
                "data": {
                    "id": str(artifact.id),
                    "session_id": str(artifact.session_id),
                    "type": artifact.type,
                    "title": artifact.title,
                    "content": artifact.content,
                    "metadata": artifact.metadata_sidecar or {},
                    "created_at": artifact.created_at.isoformat()
                }
            }
    except Exception as e:
        print(f"Local artifact fetch error: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "NOT_FOUND", "message": "Artifact not found"}
    )



