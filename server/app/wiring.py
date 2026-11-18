"""Builds adapters from config and hands them to the core. The only place that knows vendors."""

from __future__ import annotations

from functools import lru_cache

from .config import Settings, get_settings
from .core.answer import AnswerService, RetrievalSettings
from .core.ports import Embedder, LLMProvider, VectorStore
from .db import get_pool


class ConfigError(RuntimeError):
    pass


def build_embedder(settings: Settings) -> Embedder:
    if settings.embedder == "hash":
        from .adapters.embed_hash import HashEmbedder

        return HashEmbedder()
    if settings.embedder == "fastembed":
        from .adapters.embed_fastembed import FastEmbedder

        return FastEmbedder(settings.embed_model)
    raise ConfigError(f"Unknown APPCOMPASS_EMBEDDER '{settings.embedder}' (use fastembed or hash)")


def build_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "extractive":
        from .adapters.llm_extractive import ExtractiveLLM

        return ExtractiveLLM()
    if settings.llm_provider == "claude":
        import os

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ConfigError("ANTHROPIC_API_KEY is not set (or use APPCOMPASS_LLM_PROVIDER=extractive)")
        from .adapters.llm_claude import ClaudeProvider

        return ClaudeProvider(settings.claude_model)
    raise ConfigError(f"Unknown APPCOMPASS_LLM_PROVIDER '{settings.llm_provider}' (use claude or extractive)")


def build_store(settings: Settings) -> VectorStore:
    if settings.vector_store == "pgvector":
        from .adapters.store_pgvector import PgVectorStore

        return PgVectorStore(get_pool())
    raise ConfigError(f"Unknown APPCOMPASS_VECTOR_STORE '{settings.vector_store}' (use pgvector)")


@lru_cache(maxsize=1)
def embedder() -> Embedder:
    return build_embedder(get_settings())


@lru_cache(maxsize=1)
def answer_service() -> AnswerService:
    s = get_settings()
    return AnswerService(
        embedder=embedder(),
        store=build_store(s),
        llm=build_llm(s),
        settings=RetrievalSettings(k=s.retrieval_k, min_score=s.effective_min_score(),
                                   max_tokens=s.max_answer_tokens),
    )


def reset() -> None:
    """Forget built adapters (tests, or after a config change)."""
    embedder.cache_clear()
    answer_service.cache_clear()
