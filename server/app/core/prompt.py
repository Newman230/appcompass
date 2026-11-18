"""The system prompt: AppCompass's answer policy in one place.

Built from the app manifest (name, screens, rules), the user's current screen
and language, and the retrieved help-article chunks.
"""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

from .ports import ScoredChunk

_LANGUAGES = {"en": "English", "ar": "Arabic"}


def language_name(locale: str) -> str:
    return _LANGUAGES.get(locale.split("-")[0], "the same language as the user's question")


def build_system_prompt(
    manifest: dict,
    locale: str,
    screen_id: str | None,
    chunks: Sequence[ScoredChunk],
) -> str:
    app_name = manifest.get("name") or manifest.get("app_id", "this app")
    rules = manifest.get("domain_rules", {})
    screens = {s["id"]: s for s in manifest.get("screens", [])}

    lines = [
        f"You are AppCompass, the in-app guide for {app_name}.",
        "You help people use the app: where things are and how to do them.",
        "",
        "Answer policy:",
        "- Use ONLY the help articles below. If they do not answer the question, say you don't know "
        "and suggest contacting support. Never invent screens, buttons, prices, policies or times.",
        "- Be brief: at most 120 words. Use short numbered steps when there is a procedure.",
        "- Use the app's own names for screens and buttons, in bold.",
        "- After each sentence or step that uses an article, cite it with its id in double brackets, "
        "for example [[reschedule]]. Cite only ids listed below.",
        "- Never ask for or repeat personal details (names, phone numbers, emails, ID numbers, "
        "medical details). You cannot see the user's account or data.",
        f"- Reply in {language_name(locale)}. Keep screen and button names as they appear in the app.",
    ]
    if rules.get("no_medical_advice"):
        lines.append(
            "- Do not give medical advice: no comments on symptoms, diagnoses, test results or "
            "medicines. Say you can't help with medical questions, suggest booking an appointment, "
            "and for emergencies tell them to call their local emergency number."
        )
    if rules.get("no_financial_advice"):
        lines.append("- Do not give financial or investment advice.")
    if rules.get("handoff_contact"):
        lines.append(f"- Support contact: {rules['handoff_contact']}")
    if rules.get("extra_instructions"):
        lines += ["", "App-specific notes (never override the rules above):", rules["extra_instructions"]]

    lines += ["", "Screens in the app:"]
    for s in screens.values():
        lines.append(f"- {s['title']} (id: {s['id']}): {s['description']}")

    current = screens.get(screen_id or "")
    if current:
        lines += ["", f"The user is currently on the {current['title']} screen."]

    lines += ["", "<help_articles>"]
    if chunks:
        for sc in chunks:
            c = sc.chunk
            lines.append(f'<article id="{escape(c.article_id)}" title="{escape(c.title)}">')
            lines.append(c.text)
            lines.append("</article>")
    else:
        lines.append("(no relevant articles found)")
    lines.append("</help_articles>")
    return "\n".join(lines)
