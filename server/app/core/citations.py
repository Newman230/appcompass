"""Strip [[article-id]] citation markers out of a token stream.

The model is told to cite sources inline as [[article-id]]. Users should never
see the markers, but a marker can arrive split across several tokens
("[", "[resch", "edule]", "]"), so the filter holds back text that might be
the start of a marker until it can decide.
"""

from __future__ import annotations

import re

_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_MAX_MARKER = 70


def _hold_from(buffer: str, index: int) -> int:
    """Start of the text to hold back: the bracket plus any spaces right before it."""
    while index > 0 and buffer[index - 1] == " ":
        index -= 1
    return index


class CitationFilter:
    def __init__(self) -> None:
        self._buffer = ""
        self.cited: list[str] = []

    def _record(self, article_id: str) -> None:
        if article_id not in self.cited:
            self.cited.append(article_id)

    def feed(self, text: str) -> str:
        self._buffer += text
        out: list[str] = []
        while True:
            start = self._buffer.find("[[")
            if start == -1:
                # Hold a trailing "[" (and the space before it) in case the next token completes "[[".
                if self._buffer.endswith("["):
                    hold = _hold_from(self._buffer, len(self._buffer) - 1)
                    out.append(self._buffer[:hold])
                    self._buffer = self._buffer[hold:]
                else:
                    out.append(self._buffer)
                    self._buffer = ""
                break
            end = self._buffer.find("]]", start + 2)
            if end == -1:
                if len(self._buffer) - start > _MAX_MARKER:
                    # Not a marker after all; release it as plain text.
                    out.append(self._buffer[: start + 2])
                    self._buffer = self._buffer[start + 2 :]
                    continue
                hold = _hold_from(self._buffer, start)
                out.append(self._buffer[:hold])
                self._buffer = self._buffer[hold:]
                break
            inner = self._buffer[start + 2 : end].strip()
            ids = [part.strip() for part in inner.split(",")]
            if ids and all(_ID.match(i) for i in ids):
                for i in ids:
                    self._record(i)
                before = self._buffer[:start]
                # Drop the space a model usually puts before a marker.
                out.append(before[:-1] if before.endswith(" ") else before)
            else:
                out.append(self._buffer[: end + 2])
            self._buffer = self._buffer[end + 2 :]
        return "".join(out)

    def flush(self) -> str:
        rest, self._buffer = self._buffer, ""
        return rest
