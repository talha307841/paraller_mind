"""
Parallel Mind — Main Orchestrator
==================================

Starts and coordinates all subsystems:

  Thread 1  AudioRecorder  — continuous mic → VAD → speech_queue
  Thread 2  TranscriptionWorker — speech_queue → Whisper → memory / query
  Thread 3  API server (uvicorn FastAPI) — REST for ESP32 + dashboard
  Thread 4  GPIO mute button (optional, Pi only)

Wake-word logic:
  Normal transcript: store in ChromaDB + check proactive triggers
  Wake word detected alone: enter QUERY mode (next segment = the question)
  Wake word + trailing query in same utterance: answer immediately

Run:
  python main.py
"""

from __future__ import annotations

import signal
import sys
import threading
import time
from queue import Empty, Queue

import uvicorn
from loguru import logger

import config
import state

# ── Logging setup ─────────────────────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <7}</level> | "
        "<cyan>{name}</cyan> — {message}"
    ),
    colorize=True,
)


# ── Startup validation ────────────────────────────────────────────────────────

def _check_env() -> None:
    if not config.NVIDIA_API_KEY:
        logger.error(
            "NVIDIA_API_KEY is not set. "
            "Copy env.template to .env and add your key from build.nvidia.com"
        )
        sys.exit(1)
    logger.info(f"NVIDIA model  : {config.NVIDIA_MODEL}")
    logger.info(f"Whisper model : {config.WHISPER_MODEL_SIZE} ({config.WHISPER_DEVICE}/{config.WHISPER_COMPUTE_TYPE})")
    logger.info(f"Wake words    : {config.WAKE_WORDS}")
    logger.info(f"Data dir      : {config.DATA_DIR}")


# ── API server thread ─────────────────────────────────────────────────────────

def _start_api_server() -> threading.Thread:
    from api.server import app

    def _run():
        uvicorn.run(
            app,
            host=config.API_HOST,
            port=config.API_PORT,
            log_level="warning",
            access_log=False,
        )

    t = threading.Thread(target=_run, daemon=True, name="APIServer")
    t.start()
    logger.info(f"API server    : http://{config.API_HOST}:{config.API_PORT}/docs")
    return t


# ── GPIO mute button (optional) ───────────────────────────────────────────────

def _start_gpio_listener(stop_event: threading.Event) -> threading.Thread | None:
    if not config.GPIO_ENABLED:
        return None

    def _run():
        try:
            import RPi.GPIO as GPIO  # type: ignore[import]

            GPIO.setmode(GPIO.BCM)
            GPIO.setup(config.MUTE_GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            logger.info(f"GPIO mute button active on BCM pin {config.MUTE_GPIO_PIN}")

            while not stop_event.is_set():
                # Wait for button press (active LOW — pin pulled high by default)
                if GPIO.input(config.MUTE_GPIO_PIN) == GPIO.LOW:
                    if state.recorder:
                        if state.recorder.is_muted:
                            state.recorder.unmute()
                        else:
                            state.recorder.mute()
                    time.sleep(0.4)   # debounce
                time.sleep(0.05)

        except ImportError:
            logger.warning(
                "RPi.GPIO not available — GPIO_ENABLED=true but running off-Pi? "
                "GPIO button disabled."
            )
        except Exception as e:
            logger.error(f"GPIO listener error: {e}")

    t = threading.Thread(target=_run, daemon=True, name="GPIOButton")
    t.start()
    return t


# ── Transcription worker ──────────────────────────────────────────────────────

def _transcription_worker(
    speech_queue: Queue,
    stop_event: threading.Event,
) -> None:
    """
    Consumes speech segments from the queue, transcribes them, and routes
    each utterance to storage, query handling, or proactive briefing.
    """
    # Heavy imports here so the main thread starts faster
    from stt.transcriber import Transcriber
    from memory.store import store_transcript
    from proactive.assistant import check_and_brief
    from tts.speaker import speak
    from llm.rag import answer_query

    transcriber = Transcriber()
    logger.info("Transcription worker ready. Listening for speech…")

    in_query_mode = False
    query_mode_expiry = 0.0

    while not stop_event.is_set():
        try:
            audio = speech_queue.get(timeout=0.5)
        except Empty:
            # Check for query mode timeout while idle
            if in_query_mode and time.time() > query_mode_expiry:
                logger.info("Query mode timed out (no speech heard).")
                in_query_mode = False
            continue

        text = transcriber.transcribe(audio)
        if not text:
            continue

        logger.info(f"▶ {text!r}")
        text_lower = text.lower()

        # ── Wake-word detection ───────────────────────────────────────────────
        detected_wake: str | None = None
        wake_end_pos: int = 0

        for wake in config.WAKE_WORDS:
            idx = text_lower.find(wake)
            if idx != -1:
                detected_wake = wake
                wake_end_pos = idx + len(wake)
                break

        # ── Routing logic ─────────────────────────────────────────────────────

        if in_query_mode:
            # This utterance is the user's question
            in_query_mode = False
            _handle_query(text, speak, answer_query)

        elif detected_wake is not None:
            # Wake word found — check if query is in the same utterance
            trailing = text[wake_end_pos:].strip(" .,!?;:")
            if trailing and len(trailing) > 3:
                # "Hey memory, what did I say to John?" — answer immediately
                logger.info(f"Inline query: {trailing!r}")
                speak("On it.")
                _handle_query(trailing, speak, answer_query)
            else:
                # Wake word alone — wait for next utterance
                in_query_mode = True
                query_mode_expiry = time.time() + config.QUERY_TIMEOUT_SECONDS
                speak("Listening.")
                logger.info(
                    f"Query mode active for {config.QUERY_TIMEOUT_SECONDS:.0f}s"
                )

        else:
            # Regular conversation — persist to memory
            store_transcript(text)

            # Check proactive triggers
            briefing = check_and_brief(text)
            if briefing:
                logger.info("Delivering proactive briefing.")
                speak(f"Heads up. {briefing}")
                state.set_latest_response(briefing)


def _handle_query(
    query: str,
    speak,
    answer_query,
) -> None:
    """Run RAG and speak the answer. Updates shared state for ESP32 display."""
    try:
        answer, _docs = answer_query(query)
        speak(answer)
        state.set_latest_response(answer, query=query)
    except Exception as e:
        logger.error(f"Query pipeline error: {e}")
        speak("Sorry, something went wrong. Please try again.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("╔═══════════════════════════════════╗")
    logger.info("║      PARALLEL MIND STARTING       ║")
    logger.info("╚═══════════════════════════════════╝")

    _check_env()
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    stop_event = threading.Event()
    speech_queue: Queue = Queue(maxsize=10)

    # ── Signal handling ───────────────────────────────────────────────────────
    def _shutdown(sig, frame):
        logger.info(f"Signal {sig} received. Shutting down…")
        stop_event.set()
        if state.recorder:
            state.recorder.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # ── Start API server ──────────────────────────────────────────────────────
    _start_api_server()

    # ── Start transcription worker ────────────────────────────────────────────
    worker = threading.Thread(
        target=_transcription_worker,
        args=(speech_queue, stop_event),
        daemon=True,
        name="TranscriptionWorker",
    )
    worker.start()

    # ── Start audio recorder ──────────────────────────────────────────────────
    # Import here so Silero model loads in main thread with good error reporting
    from stt.recorder import AudioRecorder

    recorder = AudioRecorder(speech_queue)
    state.recorder = recorder   # expose to API and GPIO
    recorder.start()

    # ── Start GPIO listener (optional) ────────────────────────────────────────
    _start_gpio_listener(stop_event)

    logger.info("System running. Say a wake word to query your memory.")
    logger.info(f"API docs: http://localhost:{config.API_PORT}/docs")

    # ── Keep main thread alive ────────────────────────────────────────────────
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Parallel Mind stopped.")
        stop_event.set()
        if state.recorder:
            state.recorder.stop()


if __name__ == "__main__":
    main()
