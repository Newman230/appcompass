from __future__ import annotations

from fastapi import APIRouter

from .. import __version__
from ..db import get_pool
from .schemas import Health

router = APIRouter(tags=["system"])


@router.get("/health", response_model=Health, operation_id="getHealth")
def get_health() -> Health:
    try:
        with get_pool().connection(timeout=2) as conn:
            conn.execute("SELECT 1")
        db = "ok"
    except Exception:  # noqa: BLE001 - health must never raise
        db = "unavailable"
    return Health(status="ok", database=db, version=__version__)
