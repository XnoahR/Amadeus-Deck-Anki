# SPDX-License-Identifier: MIT
"""Config for the chat: who she is, which model answers, what she is told.

Provider normalisation and key lookup are adapted from XnoahR/ayumi-assistant --
the shapes a provider entry can take, and the three places a key may live, were
already worked out there.

The persona lives in config so the character can be someone else entirely
without touching code. What the model is *told* is deliberately separate from
what the user types: the study figures are assembled here, not typed by anyone.
"""

from __future__ import annotations

import copy
import json
import os
import pathlib
from typing import Any

from aqt import mw

PACKAGE = __name__.split(".")[0]

# Who she is by default. Written as instructions rather than description,
# because a model follows the first and ignores the second.
DEFAULT_PERSONA = (
    "Kamu {name}, pendamping belajar yang tinggal di dalam Anki-nya {user}.\n"
    "Kamu tajam, sedikit sarkastik, dan diam-diam peduli. Kamu tidak memuji "
    "berlebihan dan tidak menceramahi.\n"
    "Jawab dalam bahasa yang dipakai pengguna. Pendek -- dua sampai empat "
    "kalimat, kecuali dia minta penjelasan panjang.\n"
    "Kamu bukan asisten serbaguna. Kalau dia bertanya di luar belajar, jawab "
    "seperlunya lalu bawa balik."
)

# She is shown as a picture, so she needs a way to say which face to wear.
DEFAULT_CHAT_MOODS = {
    "normal": ["normal", "indifferent"],
    "happy": ["happy", "winking", "sided_pleasant"],
    "thinking": ["sided_thinking", "sided_pleasant", "normal"],
    "sad": ["sad", "disappointed"],
    "annoyed": ["annoyed", "pissed", "angry"],
    "blush": ["blush", "sided_blush"],
    "surprised": ["sided_surprised", "sided_worried"],
}

MOOD_RULE = (
    "Mulai SETIAP balasan dengan satu penanda ekspresi di dalam kurung siku, "
    "lalu spasi, lalu jawabanmu.\n"
    "Contoh persis: [happy] Akhirnya balik juga.\n"
    "Pilih satu dari: %s.\n"
    "Pakai kurung siku [ ], bukan kurung biasa. Jangan pernah menyebut "
    "penanda itu di dalam kalimatmu, dan jangan menaruhnya di tengah atau di "
    "akhir balasan.\n"
    "Tulis balasannya saja. Jangan menuliskan proses berpikirmu, rencanamu, "
    "atau alasan memilih penanda -- itu terbaca oleh dia."
)

PROVIDER_FIELDS: dict[str, Any] = {
    "name": "",
    "kind": "openai",
    "model": "",
    "base_url": "",
    "api_key": "",
    "api_key_env": "",
    "api_key_file": "",
    "api_key_path": "",
    "effort": "",
    "thinking": "default",
    "max_tokens": 0,
    "context_window": 0,
    "system_in_user": False,
    "extra_headers": {},
}

KIND_DEFAULTS: dict[str, dict[str, str]] = {
    "anthropic": {"base_url": "https://api.anthropic.com",
                  "model": "claude-opus-5", "effort": "low"},
    "openai": {"base_url": "https://api.openai.com/v1",
               "model": "gpt-4o-mini", "effort": ""},
}

DEFAULTS: dict[str, Any] = {
    "character_name": "Amadeus",
    "user_name": "",
    "grain_opacity": 0.45,
    "chat_enabled": True,
    "chat_shortcut": "Ctrl+Shift+M",
    "chat_width": 420,
    "chat_face_height": 220,
    "chat_thumb_expression": True,
    "chat_thumb_zoom": 240,
    "chat_thumb_y": 20,
    "persona": DEFAULT_PERSONA,
    "chat_moods": DEFAULT_CHAT_MOODS,
    "active_provider": "",
    "providers": [],
    "max_tokens": 1200,
    "timeout_seconds": 90,
    "max_history_turns": 10,
    "about_you": "",
    "remember_chat": True,
    "remember_messages": 24,
    "compact_history": False,
    "send_study_context": True,
    "send_card_context": True,
    "max_context_chars": 900,
}


class KeyLookupError(Exception):
    """A key was configured somewhere we could not read it from."""


def normalize_provider(raw: Any, index: int = 0) -> dict[str, Any]:
    """Fill a provider entry's missing fields in from its kind's defaults."""
    entry = copy.deepcopy(PROVIDER_FIELDS)
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key in entry and value is not None:
                entry[key] = value

    kind = str(entry["kind"]).strip().lower()
    entry["kind"] = kind if kind in KIND_DEFAULTS else "openai"
    for key, fallback in KIND_DEFAULTS[entry["kind"]].items():
        if not str(entry.get(key) or "").strip():
            entry[key] = fallback

    entry["name"] = str(entry["name"]).strip() or "Provider %d" % (index + 1)
    if not isinstance(entry["extra_headers"], dict):
        entry["extra_headers"] = {}
    try:
        entry["max_tokens"] = int(entry["max_tokens"])
    except (TypeError, ValueError):
        entry["max_tokens"] = 0
    return entry


def load() -> dict[str, Any]:
    cfg = copy.deepcopy(DEFAULTS)
    raw = mw.addonManager.getConfig(PACKAGE) or {}
    for key, value in raw.items():
        if key in cfg and value is not None:
            cfg[key] = value
    cfg["providers"] = [normalize_provider(p, i)
                        for i, p in enumerate(cfg["providers"] or [])]
    if not isinstance(cfg.get("chat_moods"), dict) or not cfg["chat_moods"]:
        cfg["chat_moods"] = copy.deepcopy(DEFAULT_CHAT_MOODS)
    return cfg


def provider_names(cfg: dict[str, Any]) -> list[str]:
    return [p["name"] for p in cfg["providers"]]


def active_provider(cfg: dict[str, Any]) -> dict[str, Any] | None:
    if not cfg["providers"]:
        return None
    wanted = str(cfg.get("active_provider") or "").strip()
    for p in cfg["providers"]:
        if p["name"] == wanted:
            return p
    return cfg["providers"][0]


def save_active_provider(name: str) -> None:
    raw = mw.addonManager.getConfig(PACKAGE) or {}
    raw["active_provider"] = name
    mw.addonManager.writeConfig(PACKAGE, raw)


def resolve_api_key(provider: dict[str, Any]) -> str:
    """Literal key, else an environment variable, else a dotted path into a
    JSON file -- so a key never has to sit in config.json if you would rather
    it did not."""
    literal = str(provider.get("api_key") or "").strip()
    if literal:
        return literal

    env_name = str(provider.get("api_key_env") or "").strip()
    if env_name:
        from_env = os.environ.get(env_name, "").strip()
        if from_env:
            return from_env
        raise KeyLookupError(
            "Environment variable %s is not set (provider \"%s\")."
            % (env_name, provider["name"]))

    file_name = str(provider.get("api_key_file") or "").strip()
    if not file_name:
        return ""

    path = pathlib.Path(file_name).expanduser()
    if not path.exists():
        raise KeyLookupError("Key file not found: %s" % path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KeyLookupError("Could not read %s: %s" % (path, exc)) from exc

    dotted = str(provider.get("api_key_path") or "").strip()
    if not dotted:
        raise KeyLookupError(
            "Provider \"%s\" sets api_key_file but not api_key_path."
            % provider["name"])

    cursor: Any = data
    for part in dotted.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            here = ", ".join(sorted(cursor)) if isinstance(cursor, dict) else "-"
            raise KeyLookupError(
                "\"%s\" not found in %s.\n\nAvailable at that level: %s"
                % (dotted, path, here))
        cursor = cursor[part]
    if not isinstance(cursor, str) or not cursor.strip():
        raise KeyLookupError("\"%s\" in %s is not a non-empty string." % (dotted, path))
    return cursor.strip()


def who(cfg: dict[str, Any]) -> tuple[str, str]:
    """Her name and yours. Yours falls back to the Anki profile name, which is
    already on screen in the deck panel -- asking for it twice would be odd."""
    her = str(cfg.get("character_name") or "").strip() or "Amadeus"
    you = str(cfg.get("user_name") or "").strip()
    if not you:
        try:
            you = (mw.pm.name or "").strip()
        except Exception:
            you = ""
    return her, you or "pengguna"


def fill(text: str, **names) -> str:
    """Substitute {name} and {user} without letting an unknown or malformed
    placeholder in someone's own persona blow up the request."""
    out = str(text or "")
    for key, value in names.items():
        out = out.replace("{%s}" % key, str(value))
    return out


def system_prompt(cfg: dict[str, Any], study: str = "",
                  summary: str = "") -> str:
    """Persona, then how to signal a face, then today's figures.

    The numbers go in the system prompt rather than the user's message so she
    can mention them unprompted -- which is the whole point of her living in
    Anki rather than in a browser tab.
    """
    her, you = who(cfg)
    parts = [fill(cfg.get("persona") or DEFAULT_PERSONA, name=her, user=you).strip()]
    moods = ", ".join(sorted(cfg["chat_moods"]))
    parts.append(MOOD_RULE % moods)
    about = str(cfg.get("about_you") or "").strip()
    if about:
        # Written by the user, not inferred by the model. Standing facts belong
        # in the prompt every turn; what she worked out mid-conversation does
        # not, because a wrong guess would then outlive the conversation.
        parts.append("Yang perlu kamu ingat tentang %s:\n%s"
                     % (you, fill(about, name=her, user=you).strip()))
    if summary:
        # What was said before the surviving turns. Kept in the system prompt
        # rather than faked as a message, so it never reads as something one of
        # you actually said.
        parts.append("Ringkasan percakapan sebelumnya:\n" + summary.strip())
    if study:
        parts.append("Keadaan belajarnya hari ini:\n" + study)
    return "\n\n".join(parts)
