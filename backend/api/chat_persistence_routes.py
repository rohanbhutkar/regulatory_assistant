"""Postgres-backed regulatory chat: visitors (cookie), sessions, messages, complete-turn."""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from api.chat_rate_limit import limiter
from db.chat_deps import ChatSessionDep
from db.chat_models import ChatMessage, ChatSession, Visitor

logger = logging.getLogger(__name__)

router = APIRouter()

VISITOR_COOKIE = "regulatory_visitor_id"
MAX_MESSAGE_CHARS = int(os.getenv("CHAT_MAX_MESSAGE_CHARS", "120000"))
MAX_METADATA_JSON_CHARS = int(os.getenv("CHAT_MAX_METADATA_CHARS", "200000"))
MAX_MESSAGES_PER_SESSION = int(os.getenv("CHAT_MAX_MESSAGES_PER_SESSION", "5000"))


def _cookie_secure(request: Request) -> bool:
    if os.getenv("CHAT_COOKIE_SECURE", "").strip().lower() in ("1", "true", "yes"):
        return True
    return request.url.scheme == "https"


def _set_visitor_cookie(response: Response, visitor_id: UUID, request: Request) -> None:
    response.set_cookie(
        key=VISITOR_COOKIE,
        value=str(visitor_id),
        httponly=True,
        secure=_cookie_secure(request),
        samesite="lax",
        max_age=60 * 60 * 24 * 365 * 5,
        path="/",
    )


def _parse_uuid(val: str | None, field: str) -> UUID:
    if not val:
        raise HTTPException(status_code=400, detail={field: "required"})
    try:
        return UUID(val)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={field: "invalid uuid"}) from e


async def _visitor_from_cookie(session: ChatSessionDep, request: Request) -> UUID:
    raw = request.cookies.get(VISITOR_COOKIE)
    vid = _parse_uuid(raw, VISITOR_COOKIE)
    row = await session.get(Visitor, vid)
    if row is None:
        raise HTTPException(status_code=401, detail={"code": "unknown_visitor", "message": "Bootstrap required."})
    return vid


async def _get_session_for_visitor(
    session: ChatSessionDep, visitor_id: UUID, session_id: UUID
) -> ChatSession:
    q = await session.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.visitor_id == visitor_id)
    )
    row = q.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "session_not_found", "message": "Session not found."})
    return row


async def _message_count(session: ChatSessionDep, sid: UUID) -> int:
    r = await session.execute(select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == sid))
    return int(r.scalar_one())


def _check_message_body(content: str, meta: dict[str, Any] | None) -> None:
    if len(content) > MAX_MESSAGE_CHARS:
        raise HTTPException(
            status_code=413,
            detail={"code": "message_too_large", "max_chars": MAX_MESSAGE_CHARS},
        )
    if meta is not None:
        import json

        try:
            dumped = json.dumps(meta)
        except (TypeError, ValueError) as e:
            raise HTTPException(status_code=400, detail={"metadata": "must be JSON-serializable"}) from e
        if len(dumped) > MAX_METADATA_JSON_CHARS:
            raise HTTPException(
                status_code=413,
                detail={"code": "metadata_too_large", "max_chars": MAX_METADATA_JSON_CHARS},
            )


def _msg_out(m: ChatMessage) -> dict[str, Any]:
    return {
        "id": (m.idempotency_key or str(m.id)),
        "role": m.role,
        "content": m.content,
        "metadata": m.metadata_ if m.metadata_ is not None else {},
        "created_at": m.created_at.isoformat(),
    }


class BootstrapResponse(BaseModel):
    visitor_id: str
    created: bool = False


@limiter.limit("20/minute")
@router.post("/visitors/bootstrap", response_model=BootstrapResponse)
async def visitors_bootstrap(request: Request, response: Response, session: ChatSessionDep):
    """Ensure visitor cookie exists and matches a DB row."""
    raw = request.cookies.get(VISITOR_COOKIE)
    if raw:
        try:
            vid = UUID(raw)
        except ValueError:
            vid = None
        if vid:
            row = await session.get(Visitor, vid)
            if row is not None:
                _set_visitor_cookie(response, vid, request)
                logger.info("chat_bootstrap visitor_id=%s reused=1", vid)
                return BootstrapResponse(visitor_id=str(vid), created=False)

    ua = (request.headers.get("user-agent") or "")[:512]
    ua_hash = hashlib.sha256(ua.encode("utf-8", errors="ignore")).hexdigest()[:64] if ua else None
    v = Visitor(ua_hash=ua_hash)
    session.add(v)
    await session.flush()
    _set_visitor_cookie(response, v.id, request)
    logger.info("chat_bootstrap visitor_id=%s reused=0", v.id)
    return BootstrapResponse(visitor_id=str(v.id), created=True)


class SessionOut(BaseModel):
    id: str
    variant: str
    title: str
    starred: bool
    title_pinned: bool
    updated_at: str
    created_at: str


class SessionCreate(BaseModel):
    id: Optional[UUID] = None
    title: str = Field(default="New chat", max_length=512)
    variant: str = Field(default="regulatory", max_length=64)


class SessionPatch(BaseModel):
    title: Optional[str] = Field(default=None, max_length=512)
    starred: Optional[bool] = None
    title_pinned: Optional[bool] = Field(default=None, validation_alias=AliasChoices("title_pinned", "titlePinned"))

    model_config = ConfigDict(populate_by_name=True)


def _session_out(s: ChatSession) -> SessionOut:
    return SessionOut(
        id=str(s.id),
        variant=s.variant,
        title=s.title,
        starred=s.starred,
        title_pinned=s.title_pinned,
        updated_at=s.updated_at.isoformat(),
        created_at=s.created_at.isoformat(),
    )


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    session: ChatSessionDep,
    request: Request,
    variant: Optional[str] = None,
):
    visitor_id = await _visitor_from_cookie(session, request)
    stmt = select(ChatSession).where(ChatSession.visitor_id == visitor_id).order_by(ChatSession.updated_at.desc())
    if variant:
        stmt = stmt.where(ChatSession.variant == variant)
    rows = (await session.execute(stmt)).scalars().all()
    return [_session_out(s) for s in rows]


@limiter.limit("30/minute")
@router.post("/sessions", response_model=SessionOut)
async def create_session(request: Request, session: ChatSessionDep, body: SessionCreate):
    visitor_id = await _visitor_from_cookie(session, request)
    s = ChatSession(
        id=body.id or uuid.uuid4(),
        visitor_id=visitor_id,
        variant=body.variant,
        title=body.title,
    )
    session.add(s)
    await session.flush()
    logger.info("chat_session_create session_id=%s visitor_id=%s", s.id, visitor_id)
    return _session_out(s)


@router.patch("/sessions/{session_id}", response_model=SessionOut)
async def patch_session(
    session: ChatSessionDep,
    request: Request,
    session_id: str,
    body: SessionPatch,
):
    sid = _parse_uuid(session_id, "session_id")
    visitor_id = await _visitor_from_cookie(session, request)
    s = await _get_session_for_visitor(session, visitor_id, sid)
    if body.title is not None:
        s.title = body.title
    if body.starred is not None:
        s.starred = body.starred
    if body.title_pinned is not None:
        s.title_pinned = body.title_pinned
    await session.flush()
    logger.info("chat_session_patch session_id=%s", sid)
    return _session_out(s)


@router.delete("/sessions/{session_id}")
async def delete_session(session: ChatSessionDep, request: Request, session_id: str):
    sid = _parse_uuid(session_id, "session_id")
    visitor_id = await _visitor_from_cookie(session, request)
    await _get_session_for_visitor(session, visitor_id, sid)
    await session.execute(delete(ChatMessage).where(ChatMessage.session_id == sid))
    await session.execute(delete(ChatSession).where(ChatSession.id == sid))
    logger.info("chat_session_delete session_id=%s", sid)
    return {"ok": True, "id": str(sid)}


class MessageCreate(BaseModel):
    content: str = Field(..., max_length=MAX_MESSAGE_CHARS)
    metadata: dict[str, Any] = Field(default_factory=dict)
    client_message_id: Optional[str] = Field(default=None, max_length=128)


@router.get("/sessions/{session_id}/messages")
async def list_messages(session: ChatSessionDep, request: Request, session_id: str):
    sid = _parse_uuid(session_id, "session_id")
    visitor_id = await _visitor_from_cookie(session, request)
    await _get_session_for_visitor(session, visitor_id, sid)
    q = await session.execute(
        select(ChatMessage).where(ChatMessage.session_id == sid).order_by(ChatMessage.created_at.asc())
    )
    rows = q.scalars().all()
    return {"messages": [_msg_out(m) for m in rows]}


@router.post("/sessions/{session_id}/messages")
async def append_user_message(
    session: ChatSessionDep,
    request: Request,
    session_id: str,
    body: MessageCreate,
):
    sid = _parse_uuid(session_id, "session_id")
    visitor_id = await _visitor_from_cookie(session, request)
    chat_row = await _get_session_for_visitor(session, visitor_id, sid)
    _check_message_body(body.content, body.metadata if body.metadata else None)
    n = await _message_count(session, sid)
    if n >= MAX_MESSAGES_PER_SESSION:
        raise HTTPException(
            status_code=400,
            detail={"code": "session_message_cap", "max": MAX_MESSAGES_PER_SESSION},
        )
    idem = (body.client_message_id or "").strip() or None
    now = datetime.now(timezone.utc)
    t = ChatMessage.__table__

    if idem:
        mid = uuid.uuid4()
        stmt = (
            pg_insert(t)
            .values(
                id=mid,
                session_id=sid,
                role="user",
                content=body.content,
                metadata=body.metadata or None,
                idempotency_key=idem,
                created_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_chat_messages_session_idempotency")
            .returning(t.c.id)
        )
        res = await session.execute(stmt)
        new_id = res.scalar_one_or_none()
        if new_id is None:
            q = await session.execute(
                select(ChatMessage).where(ChatMessage.session_id == sid, ChatMessage.idempotency_key == idem)
            )
            existing = q.scalar_one()
            logger.info("chat_user_message_dedup session_id=%s", sid)
            return {"message": _msg_out(existing), "deduplicated": True}
        q2 = await session.execute(select(ChatMessage).where(ChatMessage.id == new_id))
        msg = q2.scalar_one()
    else:
        msg = ChatMessage(
            session_id=sid,
            role="user",
            content=body.content,
            metadata_=body.metadata or None,
            idempotency_key=None,
        )
        session.add(msg)
        await session.flush()

    chat_row.updated_at = now
    await session.flush()
    logger.info("chat_user_message session_id=%s msg_id=%s len=%s", sid, msg.id, len(body.content))
    return {"message": _msg_out(msg), "deduplicated": False}


class CompleteTurnBody(BaseModel):
    content: str = Field(..., max_length=MAX_MESSAGE_CHARS)
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = Field(default=None, max_length=128)


@router.post("/sessions/{session_id}/complete-turn")
async def complete_turn(
    session: ChatSessionDep,
    request: Request,
    session_id: str,
    body: CompleteTurnBody,
):
    sid = _parse_uuid(session_id, "session_id")
    visitor_id = await _visitor_from_cookie(session, request)
    chat_row = await _get_session_for_visitor(session, visitor_id, sid)
    _check_message_body(body.content, body.metadata if body.metadata else None)
    header_key = (request.headers.get("Idempotency-Key") or "").strip() or None
    idem = (body.idempotency_key or header_key or "").strip() or None
    if not idem:
        raise HTTPException(
            status_code=400,
            detail={"idempotency_key": "Provide body.idempotency_key or Idempotency-Key header."},
        )
    n = await _message_count(session, sid)
    if n >= MAX_MESSAGES_PER_SESSION:
        raise HTTPException(
            status_code=400,
            detail={"code": "session_message_cap", "max": MAX_MESSAGES_PER_SESSION},
        )
    now = datetime.now(timezone.utc)
    t = ChatMessage.__table__
    mid = uuid.uuid4()
    stmt = (
        pg_insert(t)
        .values(
            id=mid,
            session_id=sid,
            role="assistant",
            content=body.content,
            metadata=body.metadata or None,
            idempotency_key=idem,
            created_at=now,
        )
        .on_conflict_do_nothing(constraint="uq_chat_messages_session_idempotency")
        .returning(t.c.id)
    )
    res = await session.execute(stmt)
    new_id = res.scalar_one_or_none()
    if new_id is None:
        q = await session.execute(
            select(ChatMessage).where(ChatMessage.session_id == sid, ChatMessage.idempotency_key == idem)
        )
        existing = q.scalar_one()
        logger.info("chat_complete_turn_dedup session_id=%s", sid)
        return {"message": _msg_out(existing), "duplicate": True}
    q2 = await session.execute(select(ChatMessage).where(ChatMessage.id == new_id))
    msg = q2.scalar_one()
    chat_row.updated_at = now
    await session.flush()
    logger.info("chat_complete_turn session_id=%s msg_id=%s len=%s", sid, msg.id, len(body.content))
    return {"message": _msg_out(msg), "duplicate": False}
