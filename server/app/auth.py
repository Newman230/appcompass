"""API-key authentication. One key belongs to exactly one app (tenant).

Keys look like `ac_<32 url-safe chars>`. Only a sha256 hash is stored, so a
database leak does not leak usable keys. Keys are long random tokens, so a
fast hash is appropriate here (unlike passwords).
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from fastapi import Header

from .db import get_pool
from .errors import ApiError

KEY_PREFIX = "ac_"


@dataclass(frozen=True)
class CallerApp:
    app_id: str
    name: str


def new_api_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(24)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def caller_app(x_appcompass_key: str | None = Header(default=None)) -> CallerApp:
    """FastAPI dependency: resolve the calling app from its API key, or 401."""
    if not x_appcompass_key or not x_appcompass_key.startswith(KEY_PREFIX):
        raise ApiError(401, "unauthorized", "Missing or invalid API key")
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT app_id, name FROM apps WHERE key_hash = %s AND disabled_at IS NULL",
            (hash_key(x_appcompass_key),),
        ).fetchone()
    if row is None:
        raise ApiError(401, "unauthorized", "Missing or invalid API key")
    return CallerApp(app_id=row["app_id"], name=row["name"])


def require_same_app(caller: CallerApp, app_id: str) -> None:
    if caller.app_id != app_id:
        raise ApiError(403, "forbidden", "This API key does not belong to that app")
