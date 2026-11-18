"""Offline stand-in for an LLM: answers by quoting the best help article.

No API key, no network. Useful for local development, demos without a key,
and CI. It does not reason, translate or refuse; use a real model for that.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence

from ..core.ports import ChatMessage, ModelEvent, ToolSpec

_ARTICLE = re.compile(r'<article id="([^"]+)" title="[^"]*">\n(.*?)\n</article>', re.S)


class ExtractiveLLM:
    def stream(
        self,
        system: str,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolSpec],
        max_tokens: int,
    ) -> Iterator[ModelEvent]:
        match = _ARTICLE.search(system)
        if match is None:
            text = "I don't know the answer to that. Please contact support from the Help screen."
        else:
            article_id, body = match.group(1), match.group(2).strip()
            text = f"{body} [[{article_id}]]"
        for word in re.findall(r"\S+\s*", text):
            yield ModelEvent("text", text=word)
        yield ModelEvent("end")
