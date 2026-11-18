from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse
from psycopg.types.json import Jsonb

from .. import wiring
from ..auth import CallerApp, caller_app
from ..config import get_settings
from ..core.answer import AnswerTrace, Event
from ..core.ports import ChatMessage
from ..db import get_pool
from ..errors import ApiError
from .schemas import Feedback, MessageCreate, Session, SessionCreate

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])
log = logging.getLogger("appcompass.sessions")


def sse(event: Event) -> str:
    """One Server-Sent Event frame (spec/events.md)."""
    return f"event: {event.name}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"


def _current_manifest(conn, app_id: str) -> dict | None:
    row = conn.execute(
        "SELECT body FROM manifests WHERE app_id = %s ORDER BY version DESC LIMIT 1", (app_id,)
    ).fetchone()
    return row["body"] if row else None


def _live_session(conn, app_id: str, session_id: uuid.UUID) -> dict:
    row = conn.execute(
        "SELECT session_id, locale, expires_at FROM sessions WHERE session_id = %s AND app_id = %s",
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
    settings = get_settings()
    with get_pool().connection() as conn:
        session = _live_session(conn, caller.app_id, session_id)
        manifest = _current_manifest(conn, caller.app_id)
        if manifest is None:
            raise ApiError(409, "conflict", "Upload a manifest for this app before asking questions")
        locale = body.locale or session["locale"]
        if locale not in manifest["locales"]:
            raise ApiError(422, "validation_error", f"Locale '{locale}' is not enabled for this app")
        screen_ids = {sc["id"] for sc in manifest["screens"]}
        screen_id = body.screen_id if body.screen_id in screen_ids else None  # unknown screens are ignored
        rows = conn.execute(
            "SELECT role, text FROM messages WHERE session_id = %s ORDER BY created_at DESC LIMIT %s",
            (session_id, settings.history_turns * 2),
        ).fetchall()
        history = [ChatMessage(r["role"], r["text"]) for r in reversed(rows)]
        conn.execute(
            "INSERT INTO messages (message_id, session_id, app_id, role, text, screen_id)"
            " VALUES (%s, %s, %s, 'user', %s, %s)",
            (uuid.uuid4(), session_id, caller.app_id, body.text, screen_id),
        )

    message_id = uuid.uuid4()

    def stream() -> Iterator[str]:
        try:
            service = wiring.answer_service()
        except wiring.ConfigError as exc:
            log.error("answering is not configured: %s", exc)
            yield sse(Event("error", {"code": "upstream_unavailable",
                                      "message": "The assistant is not configured on this server."}))
            return
        trace = AnswerTrace()
        yield from (sse(e) for e in service.answer(
            app_id=caller.app_id, manifest=manifest, question=body.text, screen_id=screen_id,
            locale=locale, history=history, message_id=str(message_id), trace=trace,
        ))
        if trace.error:
            log.warning("answer failed for app %s: %s", caller.app_id, trace.error)
        if trace.answer:
            with get_pool().connection() as conn:
                conn.execute(
                    "INSERT INTO messages (message_id, session_id, app_id, role, text, screen_id, cited)"
                    " VALUES (%s, %s, %s, 'assistant', %s, %s, %s)",
                    (message_id, session_id, caller.app_id, trace.answer, screen_id, trace.cited),
                )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{session_id}/feedback", status_code=204, operation_id="sendFeedback")
def send_feedback(session_id: uuid.UUID, body: Feedback, caller: CallerApp = Depends(caller_app)) -> Response:
    with get_pool().connection() as conn:
        _live_session(conn, caller.app_id, session_id)
        found = conn.execute(
            "SELECT 1 FROM messages WHERE message_id = %s AND session_id = %s AND role = 'assistant'",
            (body.message_id, session_id),
        ).fetchone()
        if found is None:
            raise ApiError(404, "not_found", "No answer with that message_id in this session")
        conn.execute(
            "INSERT INTO feedback (message_id, app_id, rating, comment) VALUES (%s, %s, %s, %s)"
            " ON CONFLICT (message_id) DO UPDATE SET rating = EXCLUDED.rating, comment = EXCLUDED.comment,"
            " created_at = now()",
            (body.message_id, caller.app_id, body.rating, body.comment),
        )
    return Response(status_code=204)
