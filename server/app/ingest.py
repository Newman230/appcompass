"""Help articles in, searchable chunks out. Used by the /docs endpoint and the CLI."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

import yaml

from .core.chunking import chunk_article, embedding_input
from .core.ports import Article, Embedder, VectorStore

_FRONT_MATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


class ArticleError(ValueError):
    pass


def parse_markdown_article(text: str, source: str = "article") -> Article:
    """Markdown with YAML front matter: id, title, locale, screens."""
    match = _FRONT_MATTER.match(text)
    if not match:
        raise ArticleError(f"{source}: missing front matter (--- id/title/locale/screens ---)")
    meta = yaml.safe_load(match.group(1)) or {}
    missing = [k for k in ("id", "title") if not meta.get(k)]
    if missing:
        raise ArticleError(f"{source}: front matter missing {missing}")
    return Article(
        article_id=str(meta["id"]),
        title=str(meta["title"]),
        body=match.group(2),
        locale=str(meta.get("locale", "en")),
        screen_ids=tuple(meta.get("screens") or ()),
    )


def load_directory(path: Path) -> list[Article]:
    return [parse_markdown_article(p.read_text(encoding="utf-8"), p.name) for p in sorted(path.glob("*.md"))]


def check_screens(articles: Iterable[Article], manifest: dict | None) -> list[str]:
    if not manifest:
        return []
    known = {s["id"] for s in manifest.get("screens", [])}
    return [
        f"{a.article_id}: unknown screens {sorted(set(a.screen_ids) - known)}"
        for a in articles
        if set(a.screen_ids) - known
    ]


def ingest(app_id: str, articles: Iterable[Article], embedder: Embedder, store: VectorStore) -> tuple[int, int]:
    """Chunk, embed and store each article, replacing its previous chunks. Returns (articles, chunks)."""
    n_articles = n_chunks = 0
    for article in articles:
        chunks = chunk_article(app_id, article)
        if not chunks:
            store.delete_article(app_id, article.article_id)
            continue
        vectors = embedder.embed_documents([embedding_input(c) for c in chunks])
        store.replace_article(app_id, article.article_id, embedder.name, chunks, vectors)
        n_articles += 1
        n_chunks += len(chunks)
    return n_articles, n_chunks
