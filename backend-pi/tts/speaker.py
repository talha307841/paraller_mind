"""
Parallel Mind — Text-to-Speech using Piper TTS.

Primary: piper-tts Python library → renders WAV in-process → plays via
         sounddevice (bone conduction headset / any default audio output).

Fallback 1: espeak  (installed via apt, no model file required)
Fallback 2: silent  (log only — so the pipeline never crashes)

Voice model files (.onnx + .onnx.json) are downloaded by setup.sh to
~/.parallel_mind/voices/.  Set PIPER_VOICE in .env to change voice.
"""

from __future__ import annotations

import io
import subprocess
import threading
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from loguru import logger

import config


class Speaker:
    """Thread-safe TTS output. speak() blocks until audio has played."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._voice = None
        self._sr: int = 22050   # default; overwritten after model loads
        self._load_piper()

    # ── Model loading ────────────────────────────────────────────────────────

    def _load_piper(self) -> None:
        model_path = config.VOICES_DIR / f"{config.PIPER_VOICE}.onnx"
        config_path = config.VOICES_DIR / f"{config.PIPER_VOICE}.onnx.json"

        if not model_path.exists():
            logger.warning(
                f"Piper voice model not found: {model_path}\n"
                "Run setup.sh to download the model. Falling back to espeak."
            )
            return

        try:
            from piper.voice import PiperVoice  # type: ignore[import]

            self._voice = PiperVoice.load(
                str(model_path),
                config_path=str(config_path) if config_path.exists() else None,
                use_cuda=False,
            )
            # Piper stores sample rate on the voice config
            self._sr = self._voice.config.sample_rate
            logger.info(
                f"Piper TTS ready: {config.PIPER_VOICE} ({self._sr} Hz)"
            )
        except ImportError:
            logger.warning(
                "piper-tts not installed (pip install piper-tts). "
                "Using espeak fallback."
            )
        except Exception as e:
            logger.error(f"Failed to load Piper voice: {e}. Using espeak fallback.")

    # ── Public interface ─────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Synthesise and play text. Blocks until playback finishes."""
        text = text.strip()
        if not text:
            return

        logger.info(f"TTS ▶ {text[:80]}{'…' if len(text) > 80 else ''}")

        with self._lock:
            if self._voice is not None:
                self._play_piper(text)
            else:
                self._play_espeak(text)

    # ── Piper synthesis ──────────────────────────────────────────────────────

    def _play_piper(self, text: str) -> None:
        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav:
                self._voice.synthesize(text, wav)

            buf.seek(0)
            with wave.open(buf, "rb") as wav:
                nframes = wav.getnframes()
                sr = wav.getframerate()
                raw = wav.readframes(nframes)

            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            sd.play(audio, samplerate=sr, blocking=True)
            sd.wait()
        except Exception as e:
            logger.error(f"Piper playback error: {e} — retrying with espeak")
            self._play_espeak(text)

    # ── espeak fallback ──────────────────────────────────────────────────────

    @staticmethod
    def _play_espeak(text: str) -> None:
        try:
            subprocess.run(
                ["espeak", "-v", "en", "-s", "145", "-a", "200", text],
                check=False,
                timeout=30,
                capture_output=True,
            )
        except FileNotFoundError:
            logger.error(
                "espeak not found. Install with: sudo apt-get install espeak"
            )
        except subprocess.TimeoutExpired:
            logger.error("espeak timed out.")
        except Exception as e:
            logger.error(f"espeak error: {e}")


# ── Module-level singleton + convenience function ────────────────────────────

_speaker: Speaker | None = None


def _get_speaker() -> Speaker:
    global _speaker
    if _speaker is None:
        _speaker = Speaker()
    return _speaker


def speak(text: str) -> None:
    """Module-level convenience wrapper — use this everywhere."""
    _get_speaker().speak(text)
