"""The answer pipeline: retrieve, prompt, stream, cite.

Pure core: it talks to the outside world only through ports, so the same
pipeline runs with Claude or a self-hosted model, pgvector or Qdrant.

Week 2: token, citation, done and error events.
Week 4 adds PII masking, actions (tool calls) and handoff.
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from .citations import CitationFilter
from .ports import ChatMessage, Embedder, LLMProvider, ScoredChunk, VectorStore
from .prompt import build_system_prompt


@dataclass(frozen=True)
class Event:
    """One server-sent event, as defined in spec/events.md."""

    name: str
    data: dict


@dataclass(frozen=True)
class RetrievalSettings:
    k: int = 4
    min_score: float = 0.25
    screen_boost: float = 0.05
    max_tokens: int = 600


@dataclass
class AnswerTrace:
    """What happened, for persistence and (from Week 4) the audit log."""

    answer: str = ""
    retrieved: list[ScoredChunk] = field(default_factory=list)
    cited: list[str] = field(default_factory=list)
    latency_ms: int = 0
    error: str | None = None


def normalize_history(history: Sequence[ChatMessage], question: str) -> list[ChatMessage]:
    """Model APIs expect user/assistant turns that alternate and start with the user.

    A failed answer can leave two user turns in a row, and a history window can
    start on an assistant turn; merge the first and drop the second.
    """
    turns: list[ChatMessage] = []
    for m in [*history, ChatMessage("user", question)]:
        if not turns and m.role != "user":
            continue
        if turns and turns[-1].role == m.role:
            turns[-1] = ChatMessage(m.role, f"{turns[-1].text}\n\n{m.text}")
        else:
            turns.append(m)
    return turns


class AnswerService:
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        llm: LLMProvider,
        settings: RetrievalSettings | None = None,
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.llm = llm
        self.settings = settings or RetrievalSettings()

    def retrieve(self, app_id: str, question: str, screen_id: str | None) -> list[ScoredChunk]:
        s = self.settings
        hits = self.store.search(app_id, self.embedder.name, self.embedder.embed_query(question), s.k * 3)

        def boosted(h: ScoredChunk) -> float:
            return h.score + (s.screen_boost if screen_id and screen_id in h.chunk.screen_ids else 0.0)

        ranked = sorted(hits, key=boosted, reverse=True)
        return [ScoredChunk(h.chunk, boosted(h)) for h in ranked if h.score >= s.min_score][: s.k]

    def answer(
        self,
        app_id: str,
        manifest: dict,
        question: str,
        screen_id: str | None,
        locale: str,
        history: Sequence[ChatMessage],
        message_id: str,
        trace: AnswerTrace | None = None,
    ) -> Iterator[Event]:
        trace = trace if trace is not None else AnswerTrace()
        started = time.monotonic()
        try:
            chunks = self.retrieve(app_id, question, screen_id)
        except Exception as exc:  # noqa: BLE001 - surface as a contract error event
            trace.error = f"retrieval: {exc}"
            yield Event("error", {"code": "internal", "message": "Search is unavailable right now."})
            return
        trace.retrieved = chunks

        system = build_system_prompt(manifest, locale, screen_id, chunks)
        messages = normalize_history(history, question)
        citations = CitationFilter()
        parts: list[str] = []
        try:
            for event in self.llm.stream(system, messages, tools=[], max_tokens=self.settings.max_tokens):
                if event.kind != "text":
                    continue
                visible = citations.feed(event.text)
                if visible:
                    parts.append(visible)
                    yield Event("token", {"text": visible})
            tail = citations.flush()
            if tail:
                parts.append(tail)
                yield Event("token", {"text": tail})
        except Exception as exc:  # noqa: BLE001
            trace.error = f"llm: {exc}"
            trace.answer = "".join(parts)
            yield Event("error", {"code": "upstream_unavailable",
                                  "message": "The assistant is unavailable right now. Please try again."})
            return

        titles = {sc.chunk.article_id: sc.chunk.title for sc in chunks}
        trace.cited = [a for a in citations.cited if a in titles]
        for article_id in trace.cited:
            yield Event("citation", {"article_id": article_id, "title": titles[article_id]})

        trace.answer = "".join(parts).strip()
        trace.latency_ms = int((time.monotonic() - started) * 1000)
        yield Event("done", {"message_id": message_id, "latency_ms": trace.latency_ms})
