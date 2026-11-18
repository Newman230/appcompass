from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from psycopg.types.json import Jsonb

from ..auth import CallerApp, caller_app, require_same_app
from ..config import get_settings
from ..db import get_pool
from ..errors import ApiError
from ..manifest import validate_manifest
from ..core.ports import Article
from ..ingest import check_screens, ingest
from .. import wiring
from .schemas import DocsIngested, DocsUpload, ManifestStored

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


@router.post("/{app_id}/docs", status_code=202, response_model=DocsIngested, operation_id="uploadDocs")
def upload_docs(app_id: str, body: DocsUpload, caller: CallerApp = Depends(caller_app)) -> DocsIngested:
    """Chunk, embed and store help articles. Re-uploading an article replaces it."""
    require_same_app(caller, app_id)
    articles = [
        Article(article_id=a.id, title=a.title, body=a.body, locale=a.locale, screen_ids=tuple(a.screens))
        for a in body.articles
    ]
    ids = [a.article_id for a in articles]
    if len(set(ids)) != len(ids):
        raise ApiError(422, "validation_error", "Duplicate article ids in upload")
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT body FROM manifests WHERE app_id = %s ORDER BY version DESC LIMIT 1", (app_id,)
        ).fetchone()
    problems = check_screens(articles, row["body"] if row else None)
    if problems:
        raise ApiError(422, "validation_error", "Articles reference screens that are not in the manifest", problems)
    embedder = wiring.embedder()
    n_articles, n_chunks = ingest(app_id, articles, embedder, wiring.build_store(get_settings()))
    return DocsIngested(app_id=app_id, articles=n_articles, chunks=n_chunks, embedder=embedder.name)
