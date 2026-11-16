"""Ports: the only way the AppCompass core reaches the outside world.

Rule 1 of the design: core code imports these interfaces, never a vendor
SDK. Adapters (Claude, pgvector, a local embedding model, ...) live in
app/adapters/ and are chosen in config. Every adapter for a port must pass
that port's contract tests.

Week 1 defines the ports; the first adapters arrive in Week 2.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

# ---------- shared value types ----------


@dataclass(frozen=True)
class Chunk:
    """A searchable piece of a help article."""

    app_id: str
    article_id: str
    title: str
    text: str
    locale: str
    screen_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class ToolSpec:
    """A manifest action, compiled into a tool the model can call."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "assistant"]
    text: str


@dataclass(frozen=True)
class ModelEvent:
    """What an LLM adapter streams back: text pieces, then tool calls, then the end."""

    kind: Literal["text", "tool_call", "end"]
    text: str = ""
    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Article:
    article_id: str
    title: str
    body: str
    locale: str
    screen_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuditRecord:
    app_id: str
    session_id: str
    message_id: str
    question_masked: str
    source_article_ids: tuple[str, ...]
    answer: str
    action_id: str | None
    handoff_reason: str | None
    latency_ms: int


# ---------- ports ----------


@runtime_checkable
class LLMProvider(Protocol):
    """Claude API today; Claude via Bedrock/Vertex or a self-hosted model later."""

    def stream(
        self,
        system: str,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
        max_tokens: int,
    ) -> Iterator[ModelEvent]: ...


@runtime_checkable
class Embedder(Protocol):
    """Local multilingual model today; any hosted embedding API later."""

    @property
    def dimensions(self) -> int: ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


@runtime_checkable
class VectorStore(Protocol):
    """pgvector today; Qdrant or OpenSearch later. Always scoped by app_id."""

    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None: ...

    def search(
        self,
        app_id: str,
        vector: Sequence[float],
        locale: str,
        screen_id: str | None,
        limit: int,
    ) -> list[ScoredChunk]: ...

    def delete_article(self, app_id: str, article_id: str) -> None: ...


@runtime_checkable
class PIIDetector(Protocol):
    """Regex rules today; Presidio or a client's DLP service later."""

    def mask(self, text: str) -> tuple[str, list[str]]:
        """Return masked text and the kinds of data found (e.g. ['email', 'phone'])."""
        ...


@runtime_checkable
class AuditSink(Protocol):
    """Postgres table today; a client's SIEM, object storage or Kafka later."""

    def write(self, record: AuditRecord) -> None: ...


@runtime_checkable
class KnowledgeLoader(Protocol):
    """Markdown files today; Confluence, SharePoint or a CMS later."""

    def load(self, app_id: str) -> Iterator[Article]: ...


@runtime_checkable
class HandoffChannel(Protocol):
    """Emit a `handoff` event today; open a Zendesk/Freshdesk ticket or send email later."""

    def open(self, app_id: str, session_id: str, reason: str, summary: str) -> str | None:
        """Return a ticket reference if the channel creates one."""
        ...
