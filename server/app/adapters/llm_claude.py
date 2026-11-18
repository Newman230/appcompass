"""Claude via the Anthropic API.

Reads ANTHROPIC_API_KEY from the environment. Model is set with
APPCOMPASS_CLAUDE_MODEL. Later adapters can reach Claude through a client's
own cloud account (Bedrock, Vertex) without touching the core.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from ..core.ports import ChatMessage, ModelEvent, ToolSpec

DEFAULT_MODEL = "claude-haiku-5-5"


class ClaudeProvider:
    def __init__(self, model: str = DEFAULT_MODEL, api_key: str | None = None, timeout_s: float = 30.0) -> None:
        import anthropic  # imported here so the core never depends on it

        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=2)

    def stream(
        self,
        system: str,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
        max_tokens: int,
    ) -> Iterator[ModelEvent]:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": m.role, "content": m.text} for m in messages],
        }
        if tools:
            kwargs["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools
            ]
        with self._client.messages.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "content_block_delta" and getattr(event.delta, "type", "") == "text_delta":
                    yield ModelEvent("text", text=event.delta.text)
            final = stream.get_final_message()
        for block in final.content:
            if block.type == "tool_use":
                yield ModelEvent("tool_call", tool_name=block.name, tool_input=dict(block.input))
        yield ModelEvent("end")
