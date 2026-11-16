"""Runtime settings, read once from environment variables.

Every adapter choice lives here, so swapping a part is a config change,
never a code change in the core.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_SPEC_DIR = Path(__file__).resolve().parents[2] / "spec"


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "APPCOMPASS_DATABASE_URL",
            "postgresql://appcompass:appcompass@localhost:5432/appcompass",
        )
    )
    session_ttl_minutes: int = field(
        default_factory=lambda: int(os.environ.get("APPCOMPASS_SESSION_TTL_MINUTES", "30"))
    )
    spec_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("APPCOMPASS_SPEC_DIR", str(_DEFAULT_SPEC_DIR)))
    )
    # Adapter choices (ports are defined in app/core/ports.py; adapters arrive in Week 2).
    llm_provider: str = field(default_factory=lambda: os.environ.get("APPCOMPASS_LLM_PROVIDER", "claude"))
    embedder: str = field(default_factory=lambda: os.environ.get("APPCOMPASS_EMBEDDER", "local-multilingual"))
    vector_store: str = field(default_factory=lambda: os.environ.get("APPCOMPASS_VECTOR_STORE", "pgvector"))
    run_migrations: bool = field(
        default_factory=lambda: os.environ.get("APPCOMPASS_RUN_MIGRATIONS", "true").lower() == "true"
    )


def get_settings() -> Settings:
    return Settings()
