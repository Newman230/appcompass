"""Hashing embedder: deterministic, dependency-free, no model download.

Good enough for tests, CI and offline development. Not for production: it
matches words, not meaning, and cannot match Arabic questions to English
articles. Use the fastembed adapter for real retrieval.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

_TOKEN = re.compile(r"\w+", re.UNICODE)
_STOP = frozenset(
    "a an the to of and or in on for is are be can i my me how do does you your it this that with at "
    "from by as what when where which who will".split()
)


class HashEmbedder:
    def __init__(self, dimensions: int = 512) -> None:
        self._dims = dimensions

    @property
    def name(self) -> str:
        return f"hash-{self._dims}"

    @property
    def dimensions(self) -> int:
        return self._dims

    def _vector(self, text: str) -> list[float]:
        tokens = [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        vec = [0.0] * self._dims
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self._dims
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)
