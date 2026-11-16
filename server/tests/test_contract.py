"""The contract in spec/ and the code must never drift apart."""

from __future__ import annotations

import json
import re

import yaml
from jsonschema import Draft202012Validator

from app.main import create_app
from app.manifest import validate_manifest

from .conftest import REPO_ROOT

SPEC = REPO_ROOT / "spec"
EXAMPLE = REPO_ROOT / "examples" / "clinic_demo"


def _spec_operations() -> set[tuple[str, str]]:
    doc = yaml.safe_load((SPEC / "openapi.yaml").read_text(encoding="utf-8"))
    return {
        (method.upper(), path)
        for path, item in doc["paths"].items()
        for method in item
        if method in {"get", "post", "put", "patch", "delete"}
    }


def _app_openapi_paths() -> dict:
    """Use the app's own generated OpenAPI, so this works however routers are mounted."""
    return {p: item for p, item in create_app().openapi()["paths"].items() if p == "/health" or p.startswith("/v1/")}


def _app_operations() -> set[tuple[str, str]]:
    return {(m.upper(), p) for p, item in _app_openapi_paths().items() for m in item}


def test_every_spec_operation_is_implemented_and_vice_versa():
    assert _spec_operations() == _app_operations()


def test_operation_ids_match_spec():
    doc = yaml.safe_load((SPEC / "openapi.yaml").read_text(encoding="utf-8"))
    spec_ids = {op["operationId"] for item in doc["paths"].values() for op in item.values() if isinstance(op, dict)}
    app_ids = {op["operationId"] for item in _app_openapi_paths().values() for op in item.values()}
    assert spec_ids == app_ids


def test_manifest_schema_is_valid_json_schema():
    Draft202012Validator.check_schema(json.loads((SPEC / "manifest.schema.json").read_text(encoding="utf-8")))


def test_clinic_example_manifest_is_valid():
    manifest = json.loads((EXAMPLE / "manifest.json").read_text(encoding="utf-8"))
    assert validate_manifest(manifest, SPEC) == []


def _front_matter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    assert match, f"{path.name}: missing front matter"
    return yaml.safe_load(match.group(1)), match.group(2)


def test_help_articles_reference_real_screens():
    manifest = json.loads((EXAMPLE / "manifest.json").read_text(encoding="utf-8"))
    screens = {s["id"] for s in manifest["screens"]}
    articles = sorted((EXAMPLE / "help").glob("*.md"))
    assert len(articles) >= 15
    ids = set()
    for path in articles:
        meta, body = _front_matter(path)
        assert meta["id"] == path.stem, path.name
        assert meta["locale"] in manifest["locales"], path.name
        assert set(meta["screens"]) <= screens, f"{path.name}: unknown screens {set(meta['screens']) - screens}"
        assert len(body.strip()) > 80, f"{path.name}: body too short"
        ids.add(meta["id"])
    assert len(ids) == len(articles)


def test_core_imports_no_vendor_sdks():
    """Design rule 1: the core reaches the outside world only through ports."""
    banned = ("anthropic", "psycopg", "pgvector", "openai", "boto3", "sentence_transformers", "fastapi")
    for path in (REPO_ROOT / "server" / "app" / "core").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for name in banned:
            assert not re.search(rf"^\s*(import|from)\s+{name}\b", source, re.M), f"{path.name} imports {name}"
