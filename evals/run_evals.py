"""Run the AppCompass golden set against a running server.

  python evals/run_evals.py --base-url http://localhost:8080 --key $APPCOMPASS_EVAL_KEY

Prints a score per category, writes a JSON report, and exits non-zero when
the overall pass rate is below --min-pass. Deterministic checks only for now
(citations and patterns); a Claude-graded accuracy check arrives in Week 4.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml

HERE = Path(__file__).resolve().parent
_ARABIC = re.compile(r"[؀-ۿ]")
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


class HttpClient(Protocol):
    def post(self, url: str, json: Any = ..., headers: Any = ...) -> Any: ...


@dataclass
class Result:
    id: str
    category: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    answer: str = ""
    cited: list[str] = field(default_factory=list)
    latency_ms: int = 0


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for frame in text.strip().split("\n\n"):
        name = data = None
        for line in frame.splitlines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if name:
            events.append((name, data or {}))
    return events


def _mostly_arabic(text: str) -> bool:
    """Arabic answers keep English screen names, so count words, not letters: at least 40% Arabic words."""
    words = [w for w in re.findall(r"\w+", text) if _LETTER.search(w)]
    return bool(words) and sum(1 for w in words if _ARABIC.search(w)) / len(words) >= 0.4


def check(case: dict, answer: str, cited: list[str], events: list[tuple[str, dict]]) -> list[str]:
    failures: list[str] = []
    names = [e for e, _ in events]
    if not names or names[-1] != "done":
        err = next((d for e, d in events if e == "error"), {})
        return [f"stream did not finish: {err.get('code', names[-1] if names else 'no events')}"]
    if not answer.strip():
        failures.append("empty answer")
    if case.get("cite_any") and not set(case["cite_any"]) & set(cited):
        failures.append(f"expected a citation from {case['cite_any']}, got {cited or 'none'}")
    if case.get("no_citations") and cited:
        failures.append(f"expected no citations, got {cited}")
    for pattern in case.get("must", []):
        if not re.search(pattern, answer, re.I):
            failures.append(f"missing /{pattern}/")
    if case.get("must_any") and not any(re.search(p, answer, re.I) for p in case["must_any"]):
        failures.append(f"none of {case['must_any']} matched")
    for pattern in case.get("must_not", []):
        if re.search(pattern, answer, re.I):
            failures.append(f"forbidden /{pattern}/ matched")
    if case.get("arabic") and not _mostly_arabic(answer):
        failures.append("answer is not mainly Arabic")
    return failures


def run_case(client: HttpClient, base_url: str, key: str, case: dict) -> Result:
    headers = {"X-AppCompass-Key": key}
    session = client.post(f"{base_url}/v1/sessions", json={"locale": case.get("locale", "en")}, headers=headers)
    if session.status_code != 201:
        return Result(case["id"], case["category"], False, [f"session failed: HTTP {session.status_code}"])
    sid = session.json()["session_id"]
    body = {"text": case["question"]}
    if case.get("screen"):
        body["screen_id"] = case["screen"]
    started = time.monotonic()
    r = client.post(f"{base_url}/v1/sessions/{sid}/messages", json=body, headers=headers)
    latency = int((time.monotonic() - started) * 1000)
    if r.status_code != 200:
        return Result(case["id"], case["category"], False, [f"message failed: HTTP {r.status_code}"])
    events = parse_sse(r.text)
    answer = "".join(d.get("text", "") for e, d in events if e == "token")
    cited = [d["article_id"] for e, d in events if e == "citation"]
    failures = check(case, answer, cited, events)
    return Result(case["id"], case["category"], not failures, failures, answer, cited, latency)


def run(client: HttpClient, base_url: str, key: str, cases: list[dict], only: str | None = None) -> list[Result]:
    selected = [c for c in cases if not only or c["id"] == only or c["category"] == only]
    return [run_case(client, base_url, key, c) for c in selected]


def summarize(results: list[Result]) -> dict:
    by_cat: dict[str, list[Result]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)
    categories = {
        cat: {"passed": sum(r.passed for r in rs), "total": len(rs)} for cat, rs in sorted(by_cat.items())
    }
    total = len(results)
    passed = sum(r.passed for r in results)
    latencies = sorted(r.latency_ms for r in results if r.latency_ms)
    return {
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "categories": categories,
        "latency_ms_p50": latencies[len(latencies) // 2] if latencies else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default=os.environ.get("APPCOMPASS_BASE_URL", "http://localhost:8080"))
    parser.add_argument("--key", default=os.environ.get("APPCOMPASS_EVAL_KEY"), help="app API key")
    parser.add_argument("--cases", type=Path, default=HERE / "cases" / "clinic.yaml")
    parser.add_argument("--report", type=Path, default=HERE / "reports" / "latest.json")
    parser.add_argument("--min-pass", type=float, default=0.0, help="fail below this pass rate (0-1)")
    parser.add_argument("--only", help="run one case id or one category")
    args = parser.parse_args(argv)
    if not args.key:
        parser.error("--key or APPCOMPASS_EVAL_KEY is required")

    import httpx  # imported here so the harness can be tested with any client

    cases = yaml.safe_load(args.cases.read_text(encoding="utf-8"))["cases"]
    with httpx.Client(timeout=60) as client:
        results = run(client, args.base_url.rstrip("/"), args.key, cases, args.only)

    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        print(f"{mark}  {r.category:<12} {r.id:<32} {r.latency_ms:>6} ms  cited={r.cited}")
        for f in r.failures:
            print(f"        - {f}")
        if not r.passed:
            print(f"        answer: {r.answer[:300]!r}")
    summary = summarize(results)
    print()
    for cat, s in summary["categories"].items():
        print(f"{cat:<14} {s['passed']}/{s['total']}")
    print(f"{'overall':<14} {summary['passed']}/{summary['total']}  ({summary['pass_rate']:.0%})"
          f"  p50 latency {summary['latency_ms_p50']} ms")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"summary": summary, "results": [asdict(r) for r in results]},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report: {args.report}")
    return 0 if summary["pass_rate"] >= args.min_pass else 1


if __name__ == "__main__":
    sys.exit(main())
