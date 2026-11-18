"""Core logic with no database: chunking, citation markers, prompt policy."""

from __future__ import annotations

from app.core.answer import normalize_history
from app.core.chunking import chunk_article, embedding_input
from app.core.ports import ChatMessage
from app.core.citations import CitationFilter
from app.core.ports import Article, Chunk, ScoredChunk
from app.core.prompt import build_system_prompt
from app.ingest import load_directory

from .conftest import REPO_ROOT

HELP = REPO_ROOT / "examples" / "clinic_demo" / "help"


# ---------- chunking ----------


def test_every_clinic_article_chunks_within_limit():
    for article in load_directory(HELP):
        chunks = chunk_article("clinic-demo", article, max_words=90)
        assert chunks, article.article_id
        for c in chunks:
            assert len(c.text.split()) <= 90, (article.article_id, c.chunk_index)
            assert not c.text.startswith("# "), "title heading should not be a chunk"
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_numbered_steps_stay_in_one_chunk():
    article = next(a for a in load_directory(HELP) if a.article_id == "reschedule")
    chunks = chunk_article("clinic-demo", article)
    steps = [c for c in chunks if "1. Open" in c.text]
    assert len(steps) == 1 and "5. Tap **Confirm new time**" in steps[0].text


def test_long_paragraph_is_split_on_sentences():
    body = " ".join(f"Sentence number {i} explains one more detail about the feature." for i in range(40))
    chunks = chunk_article("x", Article("long", "Long", body, "en"), max_words=50)
    assert len(chunks) > 1
    assert all(len(c.text.split()) <= 50 for c in chunks)


def test_embedding_input_includes_title():
    c = Chunk("a", "b", 0, "Cancel an appointment", "Tap Cancel.", "en")
    assert embedding_input(c).startswith("Cancel an appointment\n")


# ---------- citation markers ----------


def _run(pieces):
    f = CitationFilter()
    visible = "".join(f.feed(p) for p in pieces) + f.flush()
    return visible, f.cited


def test_marker_split_across_tokens_is_removed():
    visible, cited = _run(["Open **My appointments** [", "[resch", "edule]", "] and tap it."])
    assert visible == "Open **My appointments** and tap it."
    assert cited == ["reschedule"]


def test_multiple_ids_and_repeats():
    visible, cited = _run(["Step one [[book-appointment, choose-clinic-and-doctor]]. Step two [[book-appointment]]."])
    assert "[[" not in visible
    assert cited == ["book-appointment", "choose-clinic-and-doctor"]


def test_ordinary_brackets_survive():
    visible, cited = _run(["Use [this] link and a matrix [[1, 2], [3, 4]] here [", "x"])
    assert visible == "Use [this] link and a matrix [[1, 2], [3, 4]] here [x"
    assert cited == []


def test_unclosed_marker_is_released_at_end():
    visible, cited = _run(["Answer [[never-closed"])
    assert visible == "Answer [[never-closed"
    assert cited == []


# ---------- prompt ----------


def _manifest():
    import json

    return json.loads((REPO_ROOT / "examples" / "clinic_demo" / "manifest.json").read_text(encoding="utf-8"))


def test_prompt_carries_rules_screen_language_and_articles():
    chunk = Chunk("clinic-demo", "reschedule", 0, "Reschedule an appointment", "Tap Reschedule.", "en", ("appointments",))
    prompt = build_system_prompt(_manifest(), "ar", "appointments", [ScoredChunk(chunk, 0.8)])
    assert "Northwind Clinic (demo)" in prompt
    assert "Reply in Arabic" in prompt
    assert "currently on the My appointments screen" in prompt
    assert "Do not give medical advice" in prompt
    assert '<article id="reschedule" title="Reschedule an appointment">' in prompt
    assert "[[reschedule]]" in prompt  # citation instruction example


def test_prompt_without_articles_says_so():
    prompt = build_system_prompt(_manifest(), "en", None, [])
    assert "(no relevant articles found)" in prompt
    assert "currently on" not in prompt


# ---------- conversation history ----------


def test_history_alternates_and_starts_with_user():
    history = [
        ChatMessage("assistant", "orphan answer"),
        ChatMessage("user", "first question"),
        ChatMessage("user", "retry after a failed answer"),
        ChatMessage("assistant", "an answer"),
    ]
    turns = normalize_history(history, "follow-up")
    assert [t.role for t in turns] == ["user", "assistant", "user"]
    assert turns[0].text == "first question\n\nretry after a failed answer"
    assert turns[-1].text == "follow-up"
