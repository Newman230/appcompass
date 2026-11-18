"""Vector store on Postgres + pgvector. Every query is scoped by app_id and embedder."""

from __future__ import annotations

from collections.abc import Sequence

from psycopg_pool import ConnectionPool

from ..core.ports import Chunk, ScoredChunk


def _literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(f"{v:.7f}" for v in vector) + "]"


class PgVectorStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def replace_article(
        self,
        app_id: str,
        article_id: str,
        embedder: str,
        chunks: Sequence[Chunk],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        with self._pool.connection() as conn, conn.transaction():
            conn.execute("DELETE FROM doc_chunks WHERE app_id = %s AND article_id = %s", (app_id, article_id))
            for chunk, vector in zip(chunks, vectors):
                conn.execute(
                    "INSERT INTO doc_chunks (app_id, article_id, chunk_index, title, text, locale,"
                    " screen_ids, embedder, embedding) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)",
                    (
                        app_id,
                        article_id,
                        chunk.chunk_index,
                        chunk.title,
                        chunk.text,
                        chunk.locale,
                        list(chunk.screen_ids),
                        embedder,
                        _literal(vector),
                    ),
                )

    def search(self, app_id: str, embedder: str, vector: Sequence[float], limit: int) -> list[ScoredChunk]:
        literal = _literal(vector)
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT article_id, chunk_index, title, text, locale, screen_ids,"
                " 1 - (embedding <=> %s::vector) AS score"
                " FROM doc_chunks WHERE app_id = %s AND embedder = %s"
                " ORDER BY embedding <=> %s::vector LIMIT %s",
                (literal, app_id, embedder, literal, limit),
            ).fetchall()
        return [
            ScoredChunk(
                Chunk(
                    app_id=app_id,
                    article_id=r["article_id"],
                    chunk_index=r["chunk_index"],
                    title=r["title"],
                    text=r["text"],
                    locale=r["locale"],
                    screen_ids=tuple(r["screen_ids"]),
                ),
                float(r["score"]),
            )
            for r in rows
        ]

    def delete_article(self, app_id: str, article_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM doc_chunks WHERE app_id = %s AND article_id = %s", (app_id, article_id))
