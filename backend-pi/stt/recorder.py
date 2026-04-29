"""
Parallel Mind — Continuous audio recorder with Silero VAD.

Architecture:
  PyAudio stream  →  512-sample chunks  →  VADIterator  →  speech segments
  Speech segments are put on `speech_queue` for the transcription worker.

Silero VAD (torch.hub) requires chunks of exactly 512 samples at 16 kHz.
VADIterator fires 'start'/'end' events; we accumulate int16 frames between
events and flush a float32 array onto the queue at each 'end' event.
"""

import threading
from queue import Queue

import numpy as np
import pyaudio
import torch
from loguru import logger

import config


class AudioRecorder:
    """
    Always-on microphone capture with Silero VAD.
    Call start() to begin, stop() to shut down cleanly.
    Mute/unmute via the mute() / unmute() methods (or physical GPIO button).
    """

    # Maximum speech segment before we force-flush (prevents runaway buffers)
    _MAX_SEGMENT_SEC = 30

    def __init__(self, speech_queue: Queue) -> None:
        self._queue = speech_queue
        self._running = threading.Event()
        self._muted = threading.Event()
        self._thread: threading.Thread | None = None

        self._vad_model, self._VADIterator = self._load_silero_vad()
        self._vad_iter = self._new_vad_iter()

    # ── VAD loading ──────────────────────────────────────────────────────────

    @staticmethod
    def _load_silero_vad() -> tuple:
        """
        Load Silero VAD from torch.hub.
        First call downloads ~5 MB from GitHub and caches in ~/.cache/torch/hub/.
        Subsequent calls are instant (cached locally).
        """
        logger.info("Loading Silero VAD model (first run may download ~5 MB)...")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            verbose=False,
            trust_repo=True,
        )
        model.eval()
        _get_ts, _save, _read, VADIterator, _collect = utils
        logger.info("Silero VAD ready.")
        return model, VADIterator

    def _new_vad_iter(self):
        """Create a fresh VADIterator (call after every end-of-segment reset)."""
        return self._VADIterator(
            self._vad_model,
            threshold=config.VAD_THRESHOLD,
            sampling_rate=config.SAMPLE_RATE,
            min_silence_duration_ms=config.VAD_MIN_SILENCE_MS,
            speech_pad_ms=config.VAD_SPEECH_PAD_MS,
        )

    # ── Recording loop ────────────────────────────────────────────────────────

    def _record_loop(self) -> None:
        pa = pyaudio.PyAudio()
        device_index = (
            config.AUDIO_DEVICE_INDEX if config.AUDIO_DEVICE_INDEX >= 0 else None
        )

        stream = pa.open(
            rate=config.SAMPLE_RATE,
            channels=config.CHANNELS,
            format=pyaudio.paInt16,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=config.PYAUDIO_CHUNK,
        )
        logger.info(
            f"Microphone stream open (device={device_index or 'default'}, "
            f"{config.SAMPLE_RATE} Hz, chunk={config.PYAUDIO_CHUNK})."
        )

        # int16 frames accumulated while 'is_speaking' is True
        speech_buf: list[np.ndarray] = []
        is_speaking = False
        buf_samples = 0
        max_buf_samples = config.SAMPLE_RATE * self._MAX_SEGMENT_SEC

        try:
            while self._running.is_set():
                raw = stream.read(config.PYAUDIO_CHUNK, exception_on_overflow=False)

                if self._muted.is_set():
                    # If we were mid-speech when muted, discard the buffer cleanly
                    if is_speaking:
                        speech_buf.clear()
                        is_speaking = False
                        buf_samples = 0
                        self._vad_iter = self._new_vad_iter()
                    continue

                chunk_int16 = np.frombuffer(raw, dtype=np.int16)
                # Silero expects float32 [-1, 1] with exactly PYAUDIO_CHUNK samples
                chunk_f32 = chunk_int16.astype(np.float32) / 32768.0

                event = self._vad_iter(
                    torch.from_numpy(chunk_f32), return_seconds=False
                )

                # ── Handle VAD events ─────────────────────────────────────────
                if event is not None:
                    if "start" in event:
                        is_speaking = True
                        speech_buf.clear()
                        buf_samples = 0
                        logger.debug("VAD: speech start")

                    elif "end" in event:
                        min_samples = (
                            config.VAD_MIN_SPEECH_MS * config.SAMPLE_RATE // 1000
                        )
                        if is_speaking and buf_samples >= min_samples:
                            self._flush(speech_buf)

                        speech_buf.clear()
                        is_speaking = False
                        buf_samples = 0
                        # Reset VAD state for next utterance
                        self._vad_iter = self._new_vad_iter()
                        logger.debug("VAD: speech end")

                # Accumulate audio while speaking
                if is_speaking:
                    speech_buf.append(chunk_int16)
                    buf_samples += len(chunk_int16)

                    # Safety: force-flush after MAX_SEGMENT_SEC
                    if buf_samples >= max_buf_samples:
                        logger.warning(
                            "Max segment length reached — force-flushing."
                        )
                        self._flush(speech_buf)
                        speech_buf.clear()
                        is_speaking = False
                        buf_samples = 0
                        self._vad_iter = self._new_vad_iter()

        except Exception as exc:
            logger.error(f"AudioRecorder error: {exc}")
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
            logger.info("Microphone stream closed.")

    def _flush(self, frames: list[np.ndarray]) -> None:
        """Concatenate frames, convert to float32 [-1,1] and push to queue."""
        if not frames:
            return
        audio = np.concatenate(frames).astype(np.float32) / 32768.0
        duration = len(audio) / config.SAMPLE_RATE
        if not self._queue.full():
            self._queue.put_nowait(audio)
            logger.debug(f"Queued speech segment: {duration:.2f}s")
        else:
            logger.warning(
                f"Speech queue full — dropping {duration:.2f}s segment. "
                "Consider increasing queue size or reducing transcription load."
            )

    # ── Public interface ──────────────────────────────────────────────────────

    def start(self) -> None:
        self._running.set()
        self._thread = threading.Thread(
            target=self._record_loop,
            daemon=True,
            name="AudioRecorder",
        )
        self._thread.start()
        logger.info("AudioRecorder started.")

    def stop(self) -> None:
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=3.0)
        logger.info("AudioRecorder stopped.")

    def mute(self) -> None:
        self._muted.set()
        logger.info("Microphone MUTED.")

    def unmute(self) -> None:
        self._muted.clear()
        logger.info("Microphone UNMUTED.")

    @property
    def is_muted(self) -> bool:
        return self._muted.is_set()
