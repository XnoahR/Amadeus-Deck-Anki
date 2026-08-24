# SPDX-License-Identifier: MIT
# Moved here from XnoahR/ayumi-assistant, which is AGPL; relicensed to MIT
# by its author for this add-on. Moved rather than rewritten because this is
# the expensive part of talking to a model -- streaming, six provider shapes,
# and error messages a person can act on -- and it already worked there.
"""LLM transport for Amadeus Deck.

Anki add-ons cannot pip-install, and the official SDKs pull in compiled
dependencies that can't be vendored portably, so endpoints are spoken to
directly over the stdlib. Requests are streamed via Server-Sent Events so the
panel can render tokens as they arrive.

A provider entry declares a `kind` — "anthropic" (native Messages API) or
"openai" (any OpenAI-compatible /chat/completions endpoint: OpenAI, OpenRouter,
NVIDIA, Z.ai, Together, Ollama, LM Studio, vLLM, …).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Iterator

ANTHROPIC_VERSION = "2023-06-01"

# urllib's default UA ("Python-urllib/3.x") is rejected outright by some
# Cloudflare-fronted endpoints (HTTP 403, CF error 1010) before the request is
# ever authenticated. Always send a real one; `extra_headers` can override it.
USER_AGENT = "Amadeus-Deck/1.2 (Anki add-on)"

# `effort` is rejected by the Haiku 4.5 tier, so it is omitted for those models.
_NO_EFFORT_MARKERS = ("haiku",)

OnText = Callable[[str], None]
OnStatus = Callable[[str], None]
ShouldStop = Callable[[], bool]


class ProviderError(Exception):
    """A user-facing failure: bad key, bad model, network trouble, refusal."""


# on_status is given a short code, not a sentence. What the reader sees is the
# caller's business: this module has no idea whose name is on the panel or what
# language it speaks.
STATUS_THINKING = "thinking"
STATUS_TRUNCATED = "truncated"


def stream_completion(
    provider: dict[str, Any],
    api_key: str,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    timeout: int,
    on_text: OnText,
    on_status: OnStatus,
    should_stop: ShouldStop,
) -> None:
    if provider["max_tokens"] > 0:
        max_tokens = provider["max_tokens"]

    if provider["kind"] == "anthropic":
        _stream_anthropic(
            provider, api_key, system, messages, max_tokens, timeout,
            on_text, on_status, should_stop,
        )
    else:
        _stream_openai(
            provider, api_key, system, messages, max_tokens, timeout,
            on_text, on_status, should_stop,
        )


def _require_key(provider: dict[str, Any], api_key: str) -> None:
    if api_key:
        return
    if provider["kind"] == "openai" and _is_local(provider["base_url"]):
        return  # local servers accept any key
    raise ProviderError(
        f'Belum ada API key untuk "{provider["name"]}".\n\n'
        "Buka Tools → Amadeus Deck: pengaturan… → Chat / AI, lalu isi kolom "
        "API key. Tombol di situ juga membuka panduan cara mendapatkannya."
    )


# --------------------------------------------------------------------------- #
# Anthropic Messages API
# --------------------------------------------------------------------------- #


def _stream_anthropic(
    provider: dict[str, Any],
    api_key: str,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    timeout: int,
    on_text: OnText,
    on_status: OnStatus,
    should_stop: ShouldStop,
) -> None:
    _require_key(provider, api_key)

    model = provider["model"]
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "stream": True,
    }
    if system:
        payload["system"] = system

    # Note: temperature/top_p/top_k are rejected by Opus 5 and are deliberately
    # never sent. Response shape is steered through the system prompt instead.
    effort = str(provider.get("effort") or "").strip()
    if effort and not any(m in model for m in _NO_EFFORT_MARKERS):
        payload["output_config"] = {"effort": effort}

    if str(provider.get("thinking") or "").strip() == "off":
        payload["thinking"] = {"type": "disabled"}

    headers = {
        "content-type": "application/json",
        "user-agent": USER_AGENT,
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
    }
    headers.update(_string_headers(provider))

    url = _join(provider["base_url"], "/v1/messages")

    stop_reason: str | None = None
    got_text = False

    for event in _iter_sse(url, headers, payload, timeout, should_stop):
        kind = event.get("type")

        if kind == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta":
                text = delta.get("text") or ""
                if text:
                    got_text = True
                    on_text(text)
            elif delta.get("type") == "thinking_delta":
                on_status("thinking")

        elif kind == "content_block_start":
            if (event.get("content_block") or {}).get("type") == "thinking":
                on_status("thinking")

        elif kind == "message_delta":
            stop_reason = (event.get("delta") or {}).get("stop_reason") or stop_reason

        elif kind == "error":
            raise ProviderError(_describe_api_error(event.get("error")))

    if stop_reason == "refusal":
        raise ProviderError(
            "Modelnya menolak menjawab permintaan ini.\n\n"
            "Biasanya cukup diubah kalimatnya. Kalau terus terjadi untuk "
            "pertanyaan belajar biasa, ganti modelnya."
        )
    if stop_reason == "max_tokens" and got_text:
        on_status("truncated")


# --------------------------------------------------------------------------- #
# OpenAI-compatible chat completions
# --------------------------------------------------------------------------- #


def _stream_openai(
    provider: dict[str, Any],
    api_key: str,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    timeout: int,
    on_text: OnText,
    on_status: OnStatus,
    should_stop: ShouldStop,
) -> None:
    _require_key(provider, api_key)

    full_messages: list[dict[str, str]] = []
    if system and provider.get("system_in_user"):
        # Some models refuse a system instruction outright -- Gemma on Google's
        # API is the one that matters here -- and this add-on keeps its entire
        # persona there. Folding it into the first user turn is the difference
        # between that model working and not.
        rest = list(messages)
        first = next((m for m in rest if m.get("role") == "user"), None)
        if first is None:
            rest.insert(0, {"role": "user", "content": system})
        else:
            first["content"] = "%s\n\n%s" % (system, first["content"])
        full_messages.extend(rest)
    else:
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

    payload: dict[str, Any] = {
        "model": provider["model"],
        "messages": full_messages,
        "max_tokens": max_tokens,
        "stream": True,
    }

    headers = {"content-type": "application/json", "user-agent": USER_AGENT}
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"
    headers.update(_string_headers(provider))

    url = _join(provider["base_url"], "/chat/completions")

    for event in _iter_sse(url, headers, payload, timeout, should_stop):
        if event.get("error"):
            raise ProviderError(_describe_api_error(event["error"]))

        for choice in event.get("choices") or []:
            text = (choice.get("delta") or {}).get("content") or ""
            if text:
                on_text(text)


# --------------------------------------------------------------------------- #
# Shared HTTP / SSE plumbing
# --------------------------------------------------------------------------- #


def _string_headers(provider: dict[str, Any]) -> dict[str, str]:
    return {
        str(k): str(v)
        for k, v in (provider.get("extra_headers") or {}).items()
        if k and v is not None
    }


def _iter_sse(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
    should_stop: ShouldStop,
) -> Iterator[dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        raise ProviderError(_describe_http_error(exc)) from exc
    except urllib.error.URLError as exc:
        raise ProviderError(
            f"Tidak bisa menghubungi {url}\n\n{exc.reason}\n\n"
            "Periksa koneksi internetmu, dan alamat API providernya."
        ) from exc
    except OSError as exc:
        raise ProviderError(f"Gangguan jaringan ke {url}\n\n{exc}") from exc

    with response:
        for raw_line in response:
            if should_stop():
                return

            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line or not line.startswith("data:"):
                # Blank separators and `event:` lines carry no payload; the
                # event type is duplicated inside the JSON on both kinds.
                continue

            data = line[len("data:") :].strip()
            if not data or data == "[DONE]":
                continue

            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                continue


def _describe_http_error(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception:
        raw = ""

    detail = ""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            detail = _describe_api_error(parsed.get("error")) or ""
    except (json.JSONDecodeError, TypeError):
        detail = raw.strip()[:500]

    hint = {
        401: "The API key was rejected — it may have expired. Check it in the "
        "add-on config, or re-authenticate wherever the key comes from.",
        402: "Out of credit on this account. Top up, or switch to a free model "
        "or another provider in the dropdown.",
        403: "The API key lacks permission for this model.",
        404: "Unknown model or endpoint — check `model` and `base_url`.",
        429: "Rate limited. Wait a moment and try again.",
        529: "The API is overloaded. Try again shortly.",
    }.get(exc.code, "")

    parts = [f"HTTP {exc.code} from the API."]
    if detail:
        parts.append(detail)
    if hint:
        parts.append(hint)
    return "\n\n".join(parts)


def _describe_api_error(error: Any) -> str:
    if isinstance(error, dict):
        message = error.get("message")
        if message:
            return str(message)
        return json.dumps(error)[:500]
    if error:
        return str(error)[:500]
    return "The API reported an unspecified error."


def _join(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def _is_local(base_url: str) -> bool:
    lowered = (base_url or "").lower()
    return "localhost" in lowered or "127.0.0.1" in lowered or "0.0.0.0" in lowered
