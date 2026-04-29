"""
Parallel Mind — Proactive meeting/context assistant.

When a proactive keyword (meeting, client, project, …) is detected in a
live transcript, this module:
  1. Fetches the most relevant memory chunks from the past N hours
  2. Asks the LLM: "what should the user know right now?"
  3. Returns a 1–3 sentence spoken briefing

A per-keyword debounce (default 5 min) prevents continuous interruption
when the same topic comes up repeatedly.
"""

from __future__ import annotations

import time

from loguru import logger

import config
import state
from llm.client import chat
from memory.store import query_memory

_SYSTEM_PROMPT = (
    "You are Parallel Mind, a proactive AI assistant worn by the user. "
    "The user just mentioned a keyword that may be relevant to an upcoming situation. "
    "Based on their recent conversation history, give a brief, actionable spoken briefing. "
    "Maximum 2–3 sentences. No bullet points. No markdown. "
    "Sound like a knowledgeable friend whispering useful context."
)


def check_and_brief(transcript: str) -> str | None:
    """
    Check transcript for proactive keywords.  If found and not debounced,
    fetch context and return a spoken briefing string.  Returns None if
    no action should be taken.
    """
    text_lower = transcript.lower()
    triggered_kw: str | None = None

    for kw in config.PROACTIVE_KEYWORDS:
        if kw not in text_lower:
            continue

        # Debounce — don't re-trigger for same keyword within debounce window
        last = state.proactive_last_triggered.get(kw, 0.0)
        if time.time() - last < config.PROACTIVE_DEBOUNCE_SECONDS:
            logger.debug(
                f"Proactive '{kw}': debounced "
                f"({int(time.time() - last)}s ago < {config.PROACTIVE_DEBOUNCE_SECONDS}s)"
            )
            continue

        triggered_kw = kw
        break

    if triggered_kw is None:
        return None

    logger.info(f"Proactive trigger: '{triggered_kw}'")
    state.proactive_last_triggered[triggered_kw] = time.time()

    # Retrieve context from memory within the lookback window
    since = time.time() - config.PROACTIVE_LOOKBACK_HOURS * 3600
    docs = query_memory(
        query_text=f"context related to {triggered_kw}",
        top_k=5,
        since_timestamp=since,
    )

    if not docs:
        logger.info(f"Proactive trigger '{triggered_kw}': no relevant memories found.")
        return None

    context = "\n\n".join(
        f"[{d['metadata'].get('datetime', '?')}] {d['text']}"
        for d in docs
    )

    answer = chat(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"The user just mentioned '{triggered_kw}'.\n\n"
                    f"Recent relevant memories:\n{context}\n\n"
                    f"Give a brief proactive briefing."
                ),
            },
        ],
        max_tokens=150,   # Keep spoken output short
        temperature=0.4,
    )

    logger.info(f"Proactive briefing: {answer[:80]}…")
    return answer
