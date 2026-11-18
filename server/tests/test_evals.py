"""The eval harness itself: it runs end to end and its checks behave."""

from __future__ import annotations

import importlib.util
import sys

import yaml

from .conftest import REPO_ROOT

_spec = importlib.util.spec_from_file_location("run_evals", REPO_ROOT / "evals" / "run_evals.py")
run_evals = importlib.util.module_from_spec(_spec)
sys.modules["run_evals"] = run_evals
_spec.loader.exec_module(run_evals)

CASES = yaml.safe_load((REPO_ROOT / "evals" / "cases" / "clinic.yaml").read_text(encoding="utf-8"))["cases"]


def test_golden_set_is_well_formed():
    import json

    manifest = json.loads((REPO_ROOT / "examples" / "clinic_demo" / "manifest.json").read_text(encoding="utf-8"))
    screens = {s["id"] for s in manifest["screens"]}
    articles = {p.stem for p in (REPO_ROOT / "examples" / "clinic_demo" / "help").glob("*.md")}
    ids = [c["id"] for c in CASES]
    assert len(CASES) >= 20 and len(ids) == len(set(ids))
    allowed = {"id", "category", "question", "screen", "locale", "cite_any", "no_citations",
               "must", "must_any", "must_not", "arabic"}
    for c in CASES:
        assert set(c) <= allowed, (c["id"], set(c) - allowed)
        assert c.get("screen") in screens | {None}, c["id"]
        assert set(c.get("cite_any", [])) <= articles, c["id"]


def test_checks():
    done = [("token", {"text": "x"}), ("done", {"message_id": "m", "latency_ms": 1})]
    case = {"cite_any": ["reschedule"], "must": ["reschedule"], "must_not": [r"\b\d+\s?mg\b"]}
    assert run_evals.check(case, "Tap Reschedule.", ["reschedule"], done) == []
    failures = run_evals.check(case, "Take 500 mg.", [], done)
    assert len(failures) == 3
    assert run_evals.check({"arabic": True}, "افتح شاشة My appointments", [], done) == []
    assert run_evals.check({"arabic": True}, "Open My appointments", [], done) == ["answer is not mainly Arabic"]
    errored = [("error", {"code": "upstream_unavailable"})]
    assert run_evals.check({}, "", [], errored) == ["stream did not finish: upstream_unavailable"]


def test_harness_runs_against_the_api(client, keys, clinic_ready, use_llm):
    from app.adapters.llm_extractive import ExtractiveLLM

    use_llm(ExtractiveLLM())
    results = run_evals.run(client, "", keys["clinic-demo"], CASES, only="accuracy")
    assert len(results) == 12
    assert all(r.failures != ["session failed: HTTP 401"] for r in results)
    summary = run_evals.summarize(results)
    assert summary["total"] == 12 and "accuracy" in summary["categories"]
    # The offline extractive stand-in should still find the right article for most how-to questions.
    accuracy = [c for c in CASES if c["category"] == "accuracy"]
    cited_right = sum(1 for r, c in zip(results, accuracy) if set(c.get("cite_any", [])) & set(r.cited))
    assert cited_right >= 8, [(r.id, r.cited) for r in results]
