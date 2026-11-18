"""Tests run against a real Postgres with pgvector (as in CI and Docker Compose).

Set APPCOMPASS_TEST_DATABASE_URL to point at a throwaway database; every test
session drops and rebuilds its schema.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DB = os.environ.get(
    "APPCOMPASS_TEST_DATABASE_URL",
    "postgresql://appcompass:appcompass@localhost:5432/appcompass_test",
)
os.environ["APPCOMPASS_DATABASE_URL"] = TEST_DB
os.environ["APPCOMPASS_SPEC_DIR"] = str(REPO_ROOT / "spec")
# Tests never download models or call paid APIs: hash embeddings, offline LLM.
os.environ["APPCOMPASS_EMBEDDER"] = "hash"
os.environ["APPCOMPASS_LLM_PROVIDER"] = "extractive"

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import hash_key, new_api_key  # noqa: E402
from app.db import close_pool  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def keys() -> dict[str, str]:
    """Fresh schema plus two apps, so tenant isolation can be tested."""
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    client_app = create_app()
    with TestClient(client_app):  # runs lifespan -> migrations
        pass
    close_pool()
    out: dict[str, str] = {}
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        for app_id, name in (("clinic-demo", "Clinic Demo"), ("other-app", "Other App")):
            key = new_api_key()
            conn.execute(
                "INSERT INTO apps (app_id, name, key_prefix, key_hash) VALUES (%s, %s, %s, %s)",
                (app_id, name, key[:8], hash_key(key)),
            )
            out[app_id] = key
    return out


@pytest.fixture()
def client(keys):
    with TestClient(create_app()) as c:
        yield c
    close_pool()


@pytest.fixture()
def clinic_headers(keys) -> dict[str, str]:
    return {"X-AppCompass-Key": keys["clinic-demo"]}


@pytest.fixture()
def other_headers(keys) -> dict[str, str]:
    return {"X-AppCompass-Key": keys["other-app"]}


@pytest.fixture()
def clean_manifests(keys):
    with psycopg.connect(TEST_DB, autocommit=True) as conn:
        conn.execute("DELETE FROM manifests")
    yield


@pytest.fixture()
def clinic_manifest() -> dict:
    import json

    return json.loads((REPO_ROOT / "examples" / "clinic_demo" / "manifest.json").read_text(encoding="utf-8"))


def parse_sse(text: str) -> list[tuple[str, dict]]:
    """Turn an SSE body into [(event, data), ...]."""
    import json

    events = []
    for frame in text.strip().split("\n\n"):
        name = data = None
        for line in frame.splitlines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if name:
            events.append((name, data))
    return events


@pytest.fixture()
def clinic_ready(client, clinic_headers, clean_manifests, clinic_manifest):
    """Clinic manifest and all 16 help articles loaded."""
    from app.ingest import load_directory

    assert client.post("/v1/apps/clinic-demo/manifest", json=clinic_manifest, headers=clinic_headers).status_code == 201
    articles = [
        {"id": a.article_id, "title": a.title, "screens": list(a.screen_ids), "locale": a.locale, "body": a.body}
        for a in load_directory(REPO_ROOT / "examples" / "clinic_demo" / "help")
    ]
    r = client.post("/v1/apps/clinic-demo/docs", json={"articles": articles}, headers=clinic_headers)
    assert r.status_code == 202, r.text
    return r.json()


@pytest.fixture()
def use_llm():
    """Swap the LLM adapter for one test: use_llm(fake)."""
    from app import wiring
    from app.adapters.embed_hash import HashEmbedder
    from app.core.answer import AnswerService, RetrievalSettings

    def _install(llm):
        settings = wiring.get_settings()
        service = AnswerService(HashEmbedder(), wiring.build_store(settings), llm,
                                RetrievalSettings(min_score=settings.effective_min_score()))
        wiring.answer_service.cache_clear()
        wiring.answer_service = lambda: service  # type: ignore[assignment]
        return service

    original = wiring.answer_service
    yield _install
    wiring.answer_service = original
