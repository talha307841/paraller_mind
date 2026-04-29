"""
Parallel Mind — Shared mutable runtime state.
This module is the single source of truth for cross-module live state so
we never have circular imports or threading races on simple values.
"""

import time
from typing import Any, Optional

# ── Latest LLM response persisted for ESP32 polling ─────────────────────────
_latest: dict[str, Any] = {"text": "", "ts": 0.0, "query": ""}


def set_latest_response(text: str, query: str = "") -> None:
    """Called by the transcription worker after each LLM answer."""
    _latest["text"] = text[:256]   # Trim to OLED / low-bandwidth limit
    _latest["query"] = query[:128]
    _latest["ts"] = time.time()


def get_latest_response() -> dict[str, Any]:
    return dict(_latest)


# ── AudioRecorder reference (set by main.py after startup) ──────────────────
recorder: Optional[Any] = None   # type: backend-pi.stt.recorder.AudioRecorder


# ── Proactive debounce tracker ────────────────────────────────────────────────
# Maps keyword → last trigger timestamp so we don't spam the user.
proactive_last_triggered: dict[str, float] = {}
