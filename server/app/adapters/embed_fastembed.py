"""Local multilingual embeddings with fastembed (ONNX, CPU, no external API).

Help articles and questions never leave the server to be embedded, which is
what regulated clients want. The default model covers ~50 languages, so an
Arabic question can match an English article.

The model (~220 MB) downloads from Hugging Face on first use and is cached in
APPCOMPASS_MODEL_CACHE (default ~/.cache/appcompass/models).
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class FastEmbedder:
    def __init__(self, model: str = DEFAULT_MODEL, cache_dir: str | None = None) -> None:
        from fastembed import TextEmbedding  # imported here so the core never depends on it

        cache = cache_dir or os.environ.get(
            "APPCOMPASS_MODEL_CACHE", str(Path.home() / ".cache" / "appcompass" / "models")
        )
        self._model_name = model
        self._model = TextEmbedding(model_name=model, cache_dir=cache)
        self._dims = len(next(iter(self._model.embed(["dimension probe"]))))

    @property
    def name(self) -> str:
        return f"fastembed:{self._model_name}"

    @property
    def dimensions(self) -> int:
        return self._dims

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.embed([text]))).tolist()
