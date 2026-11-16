"""Admin commands.

  python -m app.cli create-app clinic-demo "Clinic Demo"   # prints the API key once
  python -m app.cli rotate-key clinic-demo                  # new key, old one stops working
  python -m app.cli load-manifest path/to/manifest.json     # validate and store
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from psycopg.types.json import Jsonb

from .auth import hash_key, new_api_key
from .config import get_settings
from .db import close_pool, migrate, open_pool
from .manifest import validate_manifest


def _create_app(pool, app_id: str, name: str) -> None:
    key = new_api_key()
    with pool.connection() as conn:
        exists = conn.execute("SELECT 1 FROM apps WHERE app_id = %s", (app_id,)).fetchone()
        if exists:
            sys.exit(f"App '{app_id}' already exists; use rotate-key to get a new key.")
        conn.execute(
            "INSERT INTO apps (app_id, name, key_prefix, key_hash) VALUES (%s, %s, %s, %s)",
            (app_id, name, key[:8], hash_key(key)),
        )
    print(f"Created app '{app_id}'. API key (shown once, store it safely):\n{key}")


def _rotate_key(pool, app_id: str) -> None:
    key = new_api_key()
    with pool.connection() as conn:
        cur = conn.execute(
            "UPDATE apps SET key_prefix = %s, key_hash = %s WHERE app_id = %s",
            (key[:8], hash_key(key), app_id),
        )
        if cur.rowcount == 0:
            sys.exit(f"No app '{app_id}'.")
    print(f"New API key for '{app_id}' (old key no longer works):\n{key}")


def _load_manifest(pool, path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    problems = validate_manifest(manifest, get_settings().spec_dir)
    if problems:
        sys.exit("Manifest is invalid:\n  " + "\n  ".join(problems))
    with pool.connection() as conn:
        if not conn.execute("SELECT 1 FROM apps WHERE app_id = %s", (manifest["app_id"],)).fetchone():
            sys.exit(f"No app '{manifest['app_id']}'; run create-app first.")
        conn.execute(
            "INSERT INTO manifests (app_id, version, body) VALUES (%s, %s, %s)"
            " ON CONFLICT (app_id, version) DO UPDATE SET body = EXCLUDED.body, stored_at = now()",
            (manifest["app_id"], manifest["version"], Jsonb(manifest)),
        )
    print(f"Stored manifest v{manifest['version']} for '{manifest['app_id']}'.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="appcompass")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-app")
    p.add_argument("app_id")
    p.add_argument("name")
    p = sub.add_parser("rotate-key")
    p.add_argument("app_id")
    p = sub.add_parser("load-manifest")
    p.add_argument("path", type=Path)
    args = parser.parse_args(argv)

    pool = open_pool(get_settings().database_url)
    try:
        migrate(pool)
        if args.cmd == "create-app":
            _create_app(pool, args.app_id, args.name)
        elif args.cmd == "rotate-key":
            _rotate_key(pool, args.app_id)
        else:
            _load_manifest(pool, args.path)
    finally:
        close_pool()


if __name__ == "__main__":
    main()
