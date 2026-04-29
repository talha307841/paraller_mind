"""
Parallel Mind — Speech-to-Text using faster-whisper.

faster-whisper is a reimplementation of Whisper using CTranslate2 — 4×
faster than the original on CPU, uses int8 quantisation by default on Pi.
The Transcriber is a singleton: model loads once, reused for every segment.

Garbage filter: we drop segments that are only Whisper artefacts
(e.g. "[BLANK_AUDIO]", "[MUSIC]", "(background noise)").
"""

from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
from faster_whisper import WhisperModel
from loguru import logger

import config

# Regex for segments that contain only noise artefacts
_ARTEFACT_RE = re.compile(
    r"^\s*[\(\[]"       # starts with ( or [
    r"[^\)\]]{1,40}"    # up to 40 chars inside brackets
    r"[\)\]]\s*$",      # ends with ) or ]
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _load_model() -> WhisperModel:
    logger.info(
        f"Loading Whisper model '{config.WHISPER_MODEL_SIZE}' "
        f"({config.WHISPER_DEVICE} / {config.WHISPER_COMPUTE_TYPE})..."
    )
    model = WhisperModel(
        config.WHISPER_MODEL_SIZE,
        device=config.WHISPER_DEVICE,
        compute_type=config.WHISPER_COMPUTE_TYPE,
    )
    logger.info("Whisper model ready.")
    return model


class Transcriber:
    """Thread-safe transcription wrapper around faster-whisper."""

    def __init__(self) -> None:
        self._model = _load_model()

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe a float32 numpy array (16 kHz, mono, [-1, 1]).
        Returns cleaned text or empty string if nothing intelligible.
        """
        if audio is None or len(audio) == 0:
            return ""

        segments, _info = self._model.transcribe(
            audio,
            language=config.WHISPER_LANGUAGE,
            beam_size=config.WHISPER_BEAM_SIZE,
            # Built-in VAD filter as a second pass — removes silent leading/trailing
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 300,
                "speech_pad_ms": 200,
            },
        )

        parts: list[str] = []
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            # Drop pure noise artefact segments
            if _ARTEFACT_RE.match(text):
                logger.debug(f"Dropped artefact segment: {text!r}")
                continue
            parts.append(text)

        result = " ".join(parts).strip()
        if result:
            logger.debug(f"Transcribed: {result!r}")
        return result
