"""Scripted adapters for tests."""

from __future__ import annotations

from app.core.ports import ModelEvent


class ScriptedLLM:
    """Streams fixed text pieces and records what it was asked."""

    def __init__(self, *pieces: str) -> None:
        self.pieces = pieces
        self.calls: list[dict] = []

    def stream(self, system, messages, tools, max_tokens):
        self.calls.append({"system": system, "messages": list(messages)})
        for piece in self.pieces:
            yield ModelEvent("text", text=piece)
        yield ModelEvent("end")


class FailingLLM:
    def __init__(self, after: int = 1) -> None:
        self.after = after

    def stream(self, system, messages, tools, max_tokens):
        yield ModelEvent("text", text="Partial ")
        raise RuntimeError("upstream timeout")
