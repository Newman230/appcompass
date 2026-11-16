from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from psycopg.types.json import Jsonb

from ..auth import CallerApp, caller_app
from ..config import get_settings
from ..db import get_pool
from ..errors import ApiError
from .schemas import Feedback, MessageCreate, Session, SessionCreate

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


def _current_manifest(conn, app_id: str) -> dict | None:
    row = conn.execute(
        "SELECT body FROM manifests WHERE app_id = %s ORDER BY version DESC LIMIT 1", (app_id,)
    ).fetchone()
    return row["body"] if row else None


def _live_session(conn, app_id: str, session_id: uuid.UUID) -> dict:
    row = conn.execute(
        "SELECT session_id, expires_at FROM sessions WHERE session_id = %s AND app_id = %s",
        (session_id, app_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, "not_found", "Session not found for this app")
    if row["expires_at"] <= datetime.now(timezone.utc):
        raise ApiError(404, "session_expired", "Session has expired; start a new one")
    return row


@router.post("", status_code=201, response_model=Session, operation_id="createSession")
def create_session(body: SessionCreate | None = None, caller: CallerApp = Depends(caller_app)) -> Session:
    body = body or SessionCreate()
    settings = get_settings()
    with get_pool().connection() as conn:
        manifest = _current_manifest(conn, caller.app_id)
        allowed = manifest["locales"] if manifest else None
        if body.locale and allowed and body.locale not in allowed:
            raise ApiError(422, "validation_error", f"Locale '{body.locale}' is not enabled for this app",
                           [f"enabled locales: {', '.join(allowed)}"])
        locale = body.locale or (allowed[0] if allowed else "en")
        now = datetime.now(timezone.utc)
        session_id = uuid.uuid4()
        expires = now + timedelta(minutes=settings.session_ttl_minutes)
        client = body.client.model_dump(exclude_none=True) if body.client else {}
        conn.execute(
            "INSERT INTO sessions (session_id, app_id, locale, client, created_at, expires_at)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (session_id, caller.app_id, locale, Jsonb(client), now, expires),
        )
    return Session(session_id=session_id, app_id=caller.app_id, locale=locale, created_at=now, expires_at=expires)


@router.post("/{session_id}/messages", operation_id="sendMessage")
def send_message(session_id: uuid.UUID, body: MessageCreate, caller: CallerApp = Depends(caller_app)):
    with get_pool().connection() as conn:
        _live_session(conn, caller.app_id, session_id)
    raise ApiError(501, "not_implemented", "Answering arrives in Week 2 (retrieval + Claude + SSE)")


@router.post("/{session_id}/feedback", status_code=204, operation_id="sendFeedback")
def send_feedback(session_id: uuid.UUID, body: Feedback, caller: CallerApp = Depends(caller_app)):
    with get_pool().connection() as conn:
        _live_session(conn, caller.app_id, session_id)
    raise ApiError(501, "not_implemented", "Feedback storage arrives with answers in Week 2")
