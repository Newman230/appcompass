"""Week 2 end to end: ingestion, retrieval, streamed answers, citations, history, feedback."""

from __future__ import annotations

from .conftest import parse_sse
from .fakes import FailingLLM, ScriptedLLM


def _session(client, headers, locale="en"):
    r = client.post("/v1/sessions", json={"locale": locale}, headers=headers)
    assert r.status_code == 201
    return r.json()["session_id"]


def _ask(client, headers, sid, text, screen_id=None, locale=None):
    body = {"text": text}
    if screen_id:
        body["screen_id"] = screen_id
    if locale:
        body["locale"] = locale
    r = client.post(f"/v1/sessions/{sid}/messages", json=body, headers=headers)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    return parse_sse(r.text)


# ---------- ingestion ----------


def test_docs_upload_reports_counts(clinic_ready):
    assert clinic_ready["articles"] == 16
    assert clinic_ready["chunks"] >= 16
    assert clinic_ready["embedder"] == "hash-512"


def test_reupload_replaces_instead_of_duplicating(client, clinic_headers, clinic_ready):
    article = {"id": "reschedule", "title": "Reschedule an appointment", "screens": ["appointments"],
               "body": "Open My appointments and tap Reschedule."}
    r = client.post("/v1/apps/clinic-demo/docs", json={"articles": [article]}, headers=clinic_headers)
    assert r.status_code == 202 and r.json()["chunks"] == 1
    from app.db import get_pool

    with get_pool().connection() as conn:
        n = conn.execute("SELECT count(*) AS n FROM doc_chunks WHERE article_id = 'reschedule'").fetchone()["n"]
    assert n == 1


def test_docs_with_unknown_screen_rejected(client, clinic_headers, clinic_ready):
    article = {"id": "x-article", "title": "X", "screens": ["checkout"], "body": "Body text."}
    r = client.post("/v1/apps/clinic-demo/docs", json={"articles": [article]}, headers=clinic_headers)
    assert r.status_code == 422
    assert "checkout" in r.json()["details"][0]


def test_docs_cross_app_forbidden(client, other_headers):
    article = {"id": "a", "title": "A", "body": "B"}
    assert client.post("/v1/apps/clinic-demo/docs", json={"articles": [article]}, headers=other_headers).status_code == 403


# ---------- answering ----------


def test_streamed_answer_with_citation(client, clinic_headers, clinic_ready, use_llm):
    llm = ScriptedLLM("Open **My appointments**, tap the visit, then **Reschedule** [", "[resch", "edule]].")
    use_llm(llm)
    sid = _session(client, clinic_headers)
    events = _ask(client, clinic_headers, sid, "How do I reschedule my appointment?", screen_id="appointments")

    names = [e for e, _ in events]
    assert names[0] == "token" and names[-1] == "done"
    answer = "".join(d["text"] for e, d in events if e == "token")
    assert answer == "Open **My appointments**, tap the visit, then **Reschedule**."
    assert ("citation", {"article_id": "reschedule", "title": "Reschedule an appointment"}) in events
    done = events[-1][1]
    assert set(done) == {"message_id", "latency_ms"}

    system = llm.calls[0]["system"]
    assert '<article id="reschedule"' in system, "retrieval should find the reschedule article"
    assert "currently on the My appointments screen" in system


def test_citation_to_unretrieved_article_is_dropped(client, clinic_headers, clinic_ready, use_llm):
    use_llm(ScriptedLLM("Answer [[made-up-article]]."))
    sid = _session(client, clinic_headers)
    events = _ask(client, clinic_headers, sid, "How do I cancel an appointment?")
    assert not [e for e, _ in events if e == "citation"]
    assert "".join(d["text"] for e, d in events if e == "token") == "Answer."


def test_history_is_sent_on_follow_up(client, clinic_headers, clinic_ready, use_llm):
    llm = ScriptedLLM("Tap **Cancel appointment** [[cancel-appointment]].")
    use_llm(llm)
    sid = _session(client, clinic_headers)
    _ask(client, clinic_headers, sid, "How do I cancel an appointment?")
    _ask(client, clinic_headers, sid, "Is there a fee if I do that late?")
    second = llm.calls[1]["messages"]
    assert [m.role for m in second] == ["user", "assistant", "user"]
    assert second[0].text == "How do I cancel an appointment?"
    assert second[1].text == "Tap **Cancel appointment**."


def test_history_does_not_leak_between_sessions(client, clinic_headers, clinic_ready, use_llm):
    llm = ScriptedLLM("Ok [[book-appointment]].")
    use_llm(llm)
    _ask(client, clinic_headers, _session(client, clinic_headers), "How do I book?")
    _ask(client, clinic_headers, _session(client, clinic_headers), "How do I book?")
    assert len(llm.calls[1]["messages"]) == 1


def test_arabic_session_asks_for_arabic(client, clinic_headers, clinic_ready, use_llm):
    llm = ScriptedLLM("افتح **My appointments** [[reschedule]].")
    use_llm(llm)
    sid = _session(client, clinic_headers, locale="ar")
    events = _ask(client, clinic_headers, sid, "كيف أغير موعدي؟ reschedule")
    assert "Reply in Arabic" in llm.calls[0]["system"]
    assert events[-1][0] == "done"


def test_unknown_screen_is_ignored(client, clinic_headers, clinic_ready, use_llm):
    llm = ScriptedLLM("Ok.")
    use_llm(llm)
    sid = _session(client, clinic_headers)
    _ask(client, clinic_headers, sid, "How do I book?", screen_id="admin_panel")
    assert "currently on" not in llm.calls[0]["system"]


def test_llm_failure_becomes_error_event(client, clinic_headers, clinic_ready, use_llm):
    use_llm(FailingLLM())
    sid = _session(client, clinic_headers)
    events = _ask(client, clinic_headers, sid, "How do I book?")
    assert events[-1][0] == "error"
    assert events[-1][1]["code"] == "upstream_unavailable"
    assert "done" not in [e for e, _ in events]


def test_offline_extractive_mode_answers_from_articles(client, clinic_headers, clinic_ready, use_llm):
    from app.adapters.llm_extractive import ExtractiveLLM

    use_llm(ExtractiveLLM())
    sid = _session(client, clinic_headers)
    events = _ask(client, clinic_headers, sid, "How do I add a family member to my profile?", screen_id="profile")
    cited = [d["article_id"] for e, d in events if e == "citation"]
    assert cited == ["add-family-member"]


def test_messages_need_a_manifest(client, clinic_headers, clean_manifests):
    sid = _session(client, clinic_headers)
    r = client.post(f"/v1/sessions/{sid}/messages", json={"text": "hi"}, headers=clinic_headers)
    assert r.status_code == 409


# ---------- feedback ----------


def test_feedback_on_answer(client, clinic_headers, clinic_ready, use_llm):
    use_llm(ScriptedLLM("Ok [[book-appointment]]."))
    sid = _session(client, clinic_headers)
    message_id = _ask(client, clinic_headers, sid, "How do I book?")[-1][1]["message_id"]
    url = f"/v1/sessions/{sid}/feedback"
    assert client.post(url, json={"message_id": message_id, "rating": "up"}, headers=clinic_headers).status_code == 204
    assert client.post(url, json={"message_id": message_id, "rating": "down", "comment": "too short"},
                       headers=clinic_headers).status_code == 204
    other = _session(client, clinic_headers)
    r = client.post(f"/v1/sessions/{other}/feedback", json={"message_id": message_id, "rating": "up"},
                    headers=clinic_headers)
    assert r.status_code == 404
