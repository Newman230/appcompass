from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from psycopg.types.json import Jsonb

from ..auth import CallerApp, caller_app, require_same_app
from ..config import get_settings
from ..db import get_pool
from ..errors import ApiError
from ..manifest import validate_manifest
from .schemas import ManifestStored

router = APIRouter(prefix="/v1/apps", tags=["apps"])


@router.get("/{app_id}/manifest", operation_id="getManifest")
def get_manifest(app_id: str, caller: CallerApp = Depends(caller_app)) -> dict:
    require_same_app(caller, app_id)
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT body FROM manifests WHERE app_id = %s ORDER BY version DESC LIMIT 1", (app_id,)
        ).fetchone()
    if row is None:
        raise ApiError(404, "not_found", "No manifest uploaded for this app yet")
    return row["body"]


@router.post("/{app_id}/manifest", status_code=201, response_model=ManifestStored, operation_id="putManifest")
def put_manifest(app_id: str, manifest: dict = Body(...), caller: CallerApp = Depends(caller_app)) -> ManifestStored:
    require_same_app(caller, app_id)
    problems = validate_manifest(manifest, get_settings().spec_dir)
    if problems:
        raise ApiError(422, "validation_error", "Manifest does not match spec/manifest.schema.json", problems)
    if manifest["app_id"] != app_id:
        raise ApiError(422, "validation_error", "Manifest app_id must match the URL",
                       [f"manifest app_id '{manifest['app_id']}' != '{app_id}'"])

    with get_pool().connection() as conn, conn.transaction():
        # Lock the app row so two concurrent uploads cannot both pass the version check.
        conn.execute("SELECT 1 FROM apps WHERE app_id = %s FOR UPDATE", (app_id,))
        latest = conn.execute(
            "SELECT max(version) AS v FROM manifests WHERE app_id = %s", (app_id,)
        ).fetchone()["v"]
        if latest is not None and manifest["version"] <= latest:
            raise ApiError(409, "conflict", f"Manifest version must be higher than {latest}")
        row = conn.execute(
            "INSERT INTO manifests (app_id, version, body) VALUES (%s, %s, %s) RETURNING stored_at",
            (app_id, manifest["version"], Jsonb(manifest)),
        ).fetchone()
    return ManifestStored(app_id=app_id, version=manifest["version"], stored_at=row["stored_at"])


@router.post("/{app_id}/docs", status_code=202, operation_id="uploadDocs")
def upload_docs(app_id: str, caller: CallerApp = Depends(caller_app)):
    require_same_app(caller, app_id)
    raise ApiError(501, "not_implemented", "Doc ingestion arrives in Week 2")
