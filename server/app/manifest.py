"""Manifest validation: JSON Schema first, then rules a schema cannot express."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator


@lru_cache(maxsize=4)
def _validator(schema_path: str) -> Draft202012Validator:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_manifest(manifest: object, spec_dir: Path) -> list[str]:
    """Return a list of human-readable problems; empty means valid."""
    validator = _validator(str(spec_dir / "manifest.schema.json"))
    problems = [
        f"{'/'.join(str(p) for p in err.absolute_path) or '(root)'}: {err.message}"
        for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path))
    ]
    if problems or not isinstance(manifest, dict):
        return problems

    screen_ids = [s["id"] for s in manifest["screens"]]
    action_ids = [a["id"] for a in manifest["actions"]]
    for kind, ids in (("screen", screen_ids), ("action", action_ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            problems.append(f"{kind}s: duplicate ids {dupes}")
    return problems
