"""Split help articles into small, self-contained chunks for retrieval.

Chunks stay short (default 90 words) because compact multilingual embedding
models only read ~128 tokens. Paragraphs and numbered lists are kept whole
where possible, so a step-by-step answer is never cut in half.
"""

from __future__ import annotations

import re

from .ports import Article, Chunk

_HEADING = re.compile(r"^#{1,6}\s+")


def _words(text: str) -> int:
    return len(text.split())


def _split_long_block(block: str, max_words: int) -> list[str]:
    """Break an oversized block on line breaks, then on sentences."""
    parts: list[str] = []
    for line in block.splitlines():
        if _words(line) <= max_words:
            parts.append(line)
            continue
        sentences = re.split(r"(?<=[.!?؟])\s+", line)
        current = ""
        for sentence in sentences:
            if current and _words(current) + _words(sentence) > max_words:
                parts.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()
        if current:
            parts.append(current)
    # Re-pack the small pieces up to the limit.
    packed: list[str] = []
    current = ""
    for part in parts:
        if current and _words(current) + _words(part) > max_words:
            packed.append(current)
            current = part
        else:
            current = f"{current}\n{part}".strip()
    if current:
        packed.append(current)
    return packed


def chunk_article(app_id: str, article: Article, max_words: int = 90) -> list[Chunk]:
    blocks = []
    for raw in re.split(r"\n\s*\n", article.body.strip()):
        block = raw.strip()
        if not block:
            continue
        if _HEADING.match(block) and "\n" not in block:
            continue  # the title is stored separately and prefixed at embed time
        if _words(block) > max_words:
            blocks.extend(_split_long_block(block, max_words))
        else:
            blocks.append(block)

    texts: list[str] = []
    current = ""
    for block in blocks:
        if current and _words(current) + _words(block) > max_words:
            texts.append(current)
            current = block
        else:
            current = f"{current}\n\n{block}".strip()
    if current:
        texts.append(current)

    return [
        Chunk(
            app_id=app_id,
            article_id=article.article_id,
            chunk_index=i,
            title=article.title,
            text=text,
            locale=article.locale,
            screen_ids=article.screen_ids,
        )
        for i, text in enumerate(texts)
    ]


def embedding_input(chunk: Chunk) -> str:
    """What the embedder sees: title plus text, so short chunks keep their topic."""
    return f"{chunk.title}\n{chunk.text}"
