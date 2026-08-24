# SPDX-License-Identifier: MIT
# Moved here from XnoahR/ayumi-assistant, which is AGPL; relicensed to MIT
# by its author for this add-on. Moved rather than rewritten because this is
# the expensive part of talking to a model -- streaming, six provider shapes,
# and error messages a person can act on -- and it already worked there.
"""Pulling the word and card context out of the current reviewer state."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from aqt import mw

try:  # Anki exposes this, but the helper has moved around across versions.
    from anki.utils import strip_html as _anki_strip_html
except ImportError:  # pragma: no cover - fallback for older/newer layouts
    _anki_strip_html = None

# Field names that usually hold the target expression, most specific first.
_WORD_FIELDS = (
    "word",
    "expression",
    "vocab",
    "vocabkanji",
    "vocab-kanji",
    "term",
    "key",
    "kanji",
    "target word",
    "front",
)

_SOUND_RE = re.compile(r"\[sound:[^]]*\]")
_ANKI_PLAY_RE = re.compile(r"\[anki:play:[^]]*\]")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t　]+")


@dataclass
class CardContext:
    word: str = ""
    selection: str = ""
    deck: str = ""
    note_type: str = ""
    fields: list[tuple[str, str]] = field(default_factory=list)

    def summary(self, max_chars: int) -> str:
        """A compact plain-text digest of the card, for the model."""
        lines: list[str] = []
        if self.deck:
            lines.append(f"Deck: {self.deck}")
        for name, value in self.fields:
            lines.append(f"{name}: {value}")

        text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "…"
        return text


def strip_html(value: str) -> str:
    if not value:
        return ""

    value = _SOUND_RE.sub(" ", value)
    value = _ANKI_PLAY_RE.sub(" ", value)

    if _anki_strip_html is not None:
        try:
            value = _anki_strip_html(value)
        except Exception:
            value = _TAG_RE.sub(" ", value)
    else:
        value = _TAG_RE.sub(" ", value)

    value = value.replace("&nbsp;", " ")
    value = _WS_RE.sub(" ", value)
    return value.strip()


def selected_text() -> str:
    """Whatever the user has highlighted in the reviewer webview."""
    for view in (getattr(mw, "web", None), getattr(getattr(mw, "reviewer", None), "web", None)):
        if view is None:
            continue
        try:
            text = view.page().selectedText()
        except Exception:
            continue
        if text and text.strip():
            return text.strip()
    return ""


def current_context(max_chars: int = 1200) -> CardContext | None:
    """Context for the card on screen, or None when not reviewing."""
    reviewer = getattr(mw, "reviewer", None)
    card = getattr(reviewer, "card", None) if reviewer else None

    selection = selected_text()

    if card is None:
        # Outside the reviewer a selection is still worth answering about.
        if selection:
            return CardContext(word=selection, selection=selection)
        return None

    try:
        note = card.note()
        items = [(name, strip_html(value)) for name, value in note.items()]
    except Exception:
        return CardContext(word=selection, selection=selection)

    fields = [(name, value) for name, value in items if value]

    context = CardContext(
        word=selection or _guess_word(fields),
        selection=selection,
        deck=_deck_name(card),
        note_type=_note_type_name(note),
        fields=fields,
    )
    return context


def _guess_word(fields: list[tuple[str, str]]) -> str:
    lowered = {name.strip().lower(): value for name, value in fields}

    for candidate in _WORD_FIELDS:
        value = lowered.get(candidate)
        if value:
            return _first_line(value)

    # Fall back to a partial match (e.g. "VocabKanji", "Word Reading").
    for candidate in _WORD_FIELDS:
        for name, value in fields:
            if candidate in name.strip().lower() and value:
                return _first_line(value)

    return _first_line(fields[0][1]) if fields else ""


def _first_line(value: str) -> str:
    line = value.strip().splitlines()[0] if value.strip() else ""
    return line[:120].strip()


def _deck_name(card) -> str:
    try:
        return mw.col.decks.name(card.odid or card.did)
    except Exception:
        return ""


def _note_type_name(note) -> str:
    try:
        return note.note_type()["name"]
    except Exception:
        return ""
