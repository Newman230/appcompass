"""Week 1 behaviour: auth, tenant isolation, sessions, manifests, and 501s for later weeks."""

from __future__ import annotations

import copy
import uuid


def test_health_reports_database(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["database"] == "ok"


# ---------- auth ----------


def test_missing_key_is_401_in_contract_shape(client):
    r = client.post("/v1/sessions")
    assert r.status_code == 401
    assert r.json() == {"code": "unauthorized", "message": "Missing or invalid API key"}


def test_wrong_key_is_401(client):
    r = client.post("/v1/sessions", headers={"X-AppCompass-Key": "ac_not-a-real-key"})
    assert r.status_code == 401


# ---------- sessions ----------


def test_create_session_defaults_to_english_without_manifest(client, clinic_headers, clean_manifests):
    r = client.post("/v1/sessions", headers=clinic_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["app_id"] == "clinic-demo"
    assert body["locale"] == "en"
    uuid.UUID(body["session_id"])
    assert body["expires_at"] > body["created_at"]


def test_session_locale_must_be_enabled_in_manifest(client, clinic_headers, clean_manifests, clinic_manifest):
    assert client.post("/v1/apps/clinic-demo/manifest", json=clinic_manifest, headers=clinic_headers).status_code == 201
    ok = client.post("/v1/sessions", json={"locale": "ar"}, headers=clinic_headers)
    assert ok.status_code == 201 and ok.json()["locale"] == "ar"
    bad = client.post("/v1/sessions", json={"locale": "fr"}, headers=clinic_headers)
    assert bad.status_code == 422
    assert bad.json()["code"] == "validation_error"


def test_session_rejects_unknown_fields(client, clinic_headers):
    r = client.post("/v1/sessions", json={"locale": "en", "user_email": "a@b.c"}, headers=clinic_headers)
    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"


# ---------- manifests ----------


def test_manifest_round_trip(client, clinic_headers, clean_manifests, clinic_manifest):
    r = client.post("/v1/apps/clinic-demo/manifest", json=clinic_manifest, headers=clinic_headers)
    assert r.status_code == 201
    assert r.json()["version"] == clinic_manifest["version"]
    got = client.get("/v1/apps/clinic-demo/manifest", headers=clinic_headers)
    assert got.status_code == 200
    assert got.json() == clinic_manifest


def test_manifest_version_must_increase(client, clinic_headers, clean_manifests, clinic_manifest):
    assert client.post("/v1/apps/clinic-demo/manifest", json=clinic_manifest, headers=clinic_headers).status_code == 201
    again = client.post("/v1/apps/clinic-demo/manifest", json=clinic_manifest, headers=clinic_headers)
    assert again.status_code == 409
    newer = copy.deepcopy(clinic_manifest)
    newer["version"] += 1
    assert client.post("/v1/apps/clinic-demo/manifest", json=newer, headers=clinic_headers).status_code == 201


def test_invalid_manifest_lists_problems(client, clinic_headers, clean_manifests, clinic_manifest):
    bad = copy.deepcopy(clinic_manifest)
    del bad["screens"]
    bad["actions"][0]["params"] = {"screen_id": "not-a-type"}
    r = client.post("/v1/apps/clinic-demo/manifest", json=bad, headers=clinic_headers)
    assert r.status_code == 422
    details = " ".join(r.json()["details"])
    assert "screens" in details and "not-a-type" in details


def test_duplicate_screen_ids_rejected(client, clinic_headers, clean_manifests, clinic_manifest):
    bad = copy.deepcopy(clinic_manifest)
    bad["screens"].append(copy.deepcopy(bad["screens"][0]))
    r = client.post("/v1/apps/clinic-demo/manifest", json=bad, headers=clinic_headers)
    assert r.status_code == 422
    assert any("duplicate" in d for d in r.json()["details"])


def test_manifest_app_id_must_match_url(client, other_headers, clean_manifests, clinic_manifest):
    r = client.post("/v1/apps/other-app/manifest", json=clinic_manifest, headers=other_headers)
    assert r.status_code == 422


# ---------- tenant isolation ----------


def test_key_cannot_touch_another_apps_manifest(client, other_headers, clinic_manifest):
    assert client.get("/v1/apps/clinic-demo/manifest", headers=other_headers).status_code == 403
    assert client.post("/v1/apps/clinic-demo/manifest", json=clinic_manifest, headers=other_headers).status_code == 403


def test_key_cannot_use_another_apps_session(client, clinic_headers, other_headers):
    sid = client.post("/v1/sessions", headers=clinic_headers).json()["session_id"]
    r = client.post(f"/v1/sessions/{sid}/messages", json={"text": "hi"}, headers=other_headers)
    assert r.status_code == 404


# ---------- sessions ----------


def test_unknown_session_is_404(client, clinic_headers):
    r = client.post(f"/v1/sessions/{uuid.uuid4()}/messages", json={"text": "hi"}, headers=clinic_headers)
    assert r.status_code == 404
