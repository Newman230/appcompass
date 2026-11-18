"""Runtime settings, read once from environment variables.

Every adapter choice lives here, so swapping a part is a config change,
never a code change in the core.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_SPEC_DIR = Path(__file__).resolve().parents[2] / "spec"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: _env(
            "APPCOMPASS_DATABASE_URL", "postgresql://appcompass:appcompass@localhost:5432/appcompass"
        )
    )
    session_ttl_minutes: int = field(default_factory=lambda: int(_env("APPCOMPASS_SESSION_TTL_MINUTES", "30")))
    spec_dir: Path = field(default_factory=lambda: Path(_env("APPCOMPASS_SPEC_DIR", str(_DEFAULT_SPEC_DIR))))
    run_migrations: bool = field(
        default_factory=lambda: _env("APPCOMPASS_RUN_MIGRATIONS", "true").lower() == "true"
    )

    # ---- adapter choices (ports in app/core/ports.py) ----
    # LLM: "claude" (needs ANTHROPIC_API_KEY) or "extractive" (offline, quotes the best article)
    llm_provider: str = field(default_factory=lambda: _env("APPCOMPASS_LLM_PROVIDER", "claude"))
    claude_model: str = field(default_factory=lambda: _env("APPCOMPASS_CLAUDE_MODEL", "claude-haiku-5-5"))
    # Embeddings: "fastembed" (local multilingual model) or "hash" (tests and offline only)
    embedder: str = field(default_factory=lambda: _env("APPCOMPASS_EMBEDDER", "fastembed"))
    embed_model: str = field(
        default_factory=lambda: _env(
            "APPCOMPASS_EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
    )
    vector_store: str = field(default_factory=lambda: _env("APPCOMPASS_VECTOR_STORE", "pgvector"))

    # ---- retrieval and answering ----
    retrieval_k: int = field(default_factory=lambda: int(_env("APPCOMPASS_RETRIEVAL_K", "4")))
    min_score: float | None = field(
        default_factory=lambda: float(v) if (v := os.environ.get("APPCOMPASS_MIN_SCORE")) else None
    )
    max_answer_tokens: int = field(default_factory=lambda: int(_env("APPCOMPASS_MAX_ANSWER_TOKENS", "600")))
    history_turns: int = field(default_factory=lambda: int(_env("APPCOMPASS_HISTORY_TURNS", "6")))

    def effective_min_score(self) -> float:
        """Similarity floor below which a chunk is treated as irrelevant."""
        if self.min_score is not None:
            return self.min_score
        return 0.10 if self.embedder == "hash" else 0.25


def get_settings() -> Settings:
    return Settings()
