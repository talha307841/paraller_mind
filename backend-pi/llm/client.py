"""
Parallel Mind — Multi-backend LLM client.

Priority order:
  1. NVIDIA NIM   (primary — free, 100+ models, OpenAI-compatible)
  2. Groq         (fallback — 14,400 req/day free, very fast)
  3. Google Gemini Flash  (fallback — free tier, OpenAI-compatible endpoint)
  4. GitHub Models        (fallback — 45+ models, GitHub PAT required)

All providers use the OpenAI Python SDK with different base_url / api_key
except Groq which has its own SDK but the same message format.

Each backend is tried in order; on any exception (including 429) the next
one is attempted. If all fail an error string is returned rather than raising
so the voice pipeline keeps running.
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from openai import OpenAI, RateLimitError, APIStatusError

import config

# ── Lazy-initialised client singletons ───────────────────────────────────────

_nvidia: OpenAI | None = None
_groq_client: Any | None = None
_gemini: OpenAI | None = None
_github: OpenAI | None = None


def _nvidia_client() -> OpenAI:
    global _nvidia
    if _nvidia is None:
        _nvidia = OpenAI(
            api_key=config.NVIDIA_API_KEY,
            base_url=config.NVIDIA_BASE_URL,
        )
    return _nvidia


def _groq() -> Any | None:
    global _groq_client
    if _groq_client is None and config.GROQ_API_KEY:
        from groq import Groq
        _groq_client = Groq(api_key=config.GROQ_API_KEY)
    return _groq_client


def _gemini_client() -> OpenAI | None:
    global _gemini
    if _gemini is None and config.GEMINI_API_KEY:
        _gemini = OpenAI(
            api_key=config.GEMINI_API_KEY,
            base_url=config.GEMINI_BASE_URL,
        )
    return _gemini


def _github_client() -> OpenAI | None:
    global _github
    if _github is None and config.GITHUB_TOKEN:
        _github = OpenAI(
            api_key=config.GITHUB_TOKEN,
            base_url=config.GITHUB_BASE_URL,
        )
    return _github


# ── Per-backend call helpers ──────────────────────────────────────────────────

def _call_nvidia(messages: list[dict], max_tokens: int, temperature: float) -> str | None:
    if not config.NVIDIA_API_KEY:
        return None
    try:
        resp = _nvidia_client().chat.completions.create(
            model=config.NVIDIA_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except RateLimitError:
        logger.warning("NVIDIA NIM: rate limited (429) — trying next backend")
        return None
    except APIStatusError as e:
        logger.warning(f"NVIDIA NIM API error {e.status_code}: {e.message} — trying next backend")
        return None
    except Exception as e:
        logger.warning(f"NVIDIA NIM error: {e} — trying next backend")
        return None


def _call_groq(messages: list[dict], max_tokens: int, temperature: float) -> str | None:
    client = _groq()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Groq error: {e} — trying next backend")
        return None


def _call_gemini(messages: list[dict], max_tokens: int, temperature: float) -> str | None:
    client = _gemini_client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=config.GEMINI_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"Gemini error: {e} — trying next backend")
        return None


def _call_github(messages: list[dict], max_tokens: int, temperature: float) -> str | None:
    client = _github_client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=config.GITHUB_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"GitHub Models error: {e} — no more backends")
        return None


# ── Public interface ──────────────────────────────────────────────────────────

_BACKENDS = [_call_nvidia, _call_groq, _call_gemini, _call_github]
_BACKEND_NAMES = ["NVIDIA NIM", "Groq", "Gemini Flash", "GitHub Models"]


def chat(
    messages: list[dict],
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """
    Send a chat request.  Tries NVIDIA NIM first, then falls back through
    Groq → Gemini → GitHub Models.
    Returns response text, or an error string if all backends fail.
    """
    mt = max_tokens or config.NVIDIA_MAX_TOKENS
    temp = temperature if temperature is not None else config.NVIDIA_TEMPERATURE

    for fn, name in zip(_BACKENDS, _BACKEND_NAMES):
        result = fn(messages, mt, temp)
        if result is not None:
            logger.debug(f"LLM answered via {name}")
            return result
        logger.info(f"{name} unavailable, trying next…")

    logger.error("All LLM backends failed.")
    return (
        "Sorry, I couldn't reach any AI backend right now. "
        "Check your NVIDIA_API_KEY and network connection."
    )
