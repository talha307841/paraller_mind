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
"""
Parallel Mind — Main Orchestrator
===================================
Boots all components, runs the always-on audio capture ↔ VAD ↔ STT loop,
handles wake-word queries, proactive briefs, and the optional REST API.

Usage
-----
    python3 main.py               # normal run
    python3 main.py --no-tts      # silence TTS (testing)
    python3 main.py --list-devices # list audio input devices and exit
"""

import argparse
import logging
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path

import config

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)-8s] %(name)-24s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(config.LOGS_DIR / "parallel_mind.log")),
    ],
)
logger = logging.getLogger("parallel_mind")

# ── Component imports (after logging is set up) ───────────────────────────────

from audio.capture import AudioCapture
from audio.vad import SileroVAD
from stt.engine import WhisperSTT
from memory.store import MemoryStore
from memory.embeddings import EmbeddingEngine
from memory.tagger import TopicTagger
from llm.nvidia_nim import NvidiaLLM
from llm.fallback import GroqLLM
from rag.pipeline import RAGPipeline
from tts.engine import PiperTTS
from wakeword.detector import WakeWordDetector
from proactive.engine import ProactiveEngine
import api.server as api_server


# ═════════════════════════════════════════════════════════════════════════════
class ParallelMind:
    """
    Top-level controller.  Wires all components together and runs the
    main capture → transcribe → store / respond loop.
    """

    def __init__(self, enable_tts: bool = True) -> None:
        logger.info("╔══════════════════════════════════╗")
        logger.info("║    PARALLEL MIND — BOOTING UP    ║")
        logger.info("╚══════════════════════════════════╝")

        # ── Audio ─────────────────────────────────────────────────────────────
        self.audio = AudioCapture(
            sample_rate=config.SAMPLE_RATE,
            chunk_samples=config.AUDIO_CHUNK_SAMPLES,
            channels=config.CHANNELS,
            device_index=config.AUDIO_INPUT_DEVICE_INDEX,
        )
        self.vad = SileroVAD(
            sample_rate=config.SAMPLE_RATE,
            threshold=config.VAD_THRESHOLD,
            min_speech_duration_ms=config.VAD_MIN_SPEECH_MS,
            min_silence_duration_ms=config.VAD_MIN_SILENCE_MS,
            speech_pad_ms=config.VAD_SPEECH_PAD_MS,
        )

        # ── STT ───────────────────────────────────────────────────────────────
        self.stt = WhisperSTT(
            model_size=config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
            language=config.WHISPER_LANGUAGE,
            models_dir=config.MODELS_DIR / "whisper",
        )

        # ── Memory ────────────────────────────────────────────────────────────
        self.embedder = EmbeddingEngine(model_name=config.EMBEDDING_MODEL)
        self.memory = MemoryStore(
            persist_directory=str(config.CHROMA_DIR),
            collection_name=config.CHROMA_COLLECTION,
        )
        self.tagger = TopicTagger()

        # ── LLMs ──────────────────────────────────────────────────────────────
        self.llm = NvidiaLLM(
            api_key=config.NVIDIA_API_KEY,
            model=config.NVIDIA_MODEL,
            max_rpm=config.NVIDIA_MAX_RPM,
        )
        self.fallback_llm = GroqLLM(
            api_key=config.GROQ_API_KEY,
            model=config.GROQ_MODEL,
        )

        # ── RAG pipeline ──────────────────────────────────────────────────────
        self.rag = RAGPipeline(
            memory_store=self.memory,
            embedding_engine=self.embedder,
            primary_llm=self.llm,
            fallback_llm=self.fallback_llm,
            topic_tagger=self.tagger,
            top_k=config.MEMORY_TOP_K,
        )

        # ── TTS ───────────────────────────────────────────────────────────────
        tts_voice = config.TTS_VOICE if enable_tts else None
        if enable_tts and config.TTS_ENABLED:
            self.tts = PiperTTS(
                voice=config.TTS_VOICE,
                models_dir=config.MODELS_DIR / "piper",
            )
        else:
            self.tts = _ConsoleTTS()  # print-only fallback

        # ── Wake word ─────────────────────────────────────────────────────────
        self.wake = WakeWordDetector(
            wake_words=config.WAKE_WORDS,
            on_query=self._handle_query,
            capture_timeout_s=config.QUERY_CAPTURE_TIMEOUT_S,
        )

        # ── Proactive engine ──────────────────────────────────────────────────
        self.proactive: ProactiveEngine | None = None
        if config.PROACTIVE_ENABLED:
            self.proactive = ProactiveEngine(
                trigger_keywords=config.PROACTIVE_KEYWORDS,
                rag_pipeline=self.rag,
                tts_engine=self.tts,
                cooldown_minutes=config.PROACTIVE_COOLDOWN_MIN,
            )

        # ── REST API ──────────────────────────────────────────────────────────
        self._api_thread: threading.Thread | None = None

        # ── Runtime stats ─────────────────────────────────────────────────────
        self._stats: dict = {
            "start_time": datetime.now().isoformat(),
            "memories_stored": 0,
            "queries_answered": 0,
            "proactive_briefs": 0,
        }
        self._running = False

        logger.info(
            f"Parallel Mind ready — {self.memory.count()} memories in store"
        )

    # ── API ───────────────────────────────────────────────────────────────────

    def _start_api(self) -> None:
        api_server.init(
            rag=self.rag,
            memory_store=self.memory,
            tts=self.tts,
            stats=self._stats,
        )
        self._api_thread = threading.Thread(
            target=api_server.start,
            kwargs={"host": config.API_HOST, "port": config.API_PORT},
            daemon=True,
            name="api-server",
        )
        self._api_thread.start()
        logger.info(
            f"REST API running at http://{config.API_HOST}:{config.API_PORT}/docs"
        )

    # ── Query handler ─────────────────────────────────────────────────────────

    def _handle_query(self, query: str) -> None:
        """
        Called in a daemon thread when a wake-word query is captured.
        Mutes mic while speaking to prevent echo being recorded.
        """
        logger.info(f"▶ QUERY: {query!r}")
        self._stats["queries_answered"] += 1

        self.audio.mute()
        self.vad.reset()
        try:
            result = self.rag.query(query)
            answer = result["answer"]
            source = result["source"]
            logger.info(f"◀ ANSWER [{source}]: {answer[:120]}")
            self.tts.speak(answer, block=True)
        except Exception:
            logger.exception("Query handling failed")
            self.tts.speak("Sorry, I ran into an error processing that.", block=True)
        finally:
            self.vad.reset()
            self.audio.unmute()

    # ── Speech processing ─────────────────────────────────────────────────────

    def _process_speech(self, text: str) -> None:
        """
        Called in a daemon thread for every transcribed speech segment.
        1. Check wake word (returns True if consumed as a query)
        2. Store as a memory
        3. Check proactive keywords
        """
        # 1. Wake word check
        if self.wake.process(text):
            return   # consumed by wake word detector

        # 2. Store memory
        doc_id = self.rag.store_transcript(text=text, source="microphone")
        if doc_id:
            self._stats["memories_stored"] += 1
            logger.debug(f"Memory stored [{doc_id}]: {text[:60]}")

        # 3. Proactive check
        if self.proactive and self.proactive.check(text):
            self._stats["proactive_briefs"] += 1

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the system and block until shutdown."""
        self._running = True

        # Start REST API in background (if enabled)
        if config.API_ENABLED:
            self._start_api()

        # Open microphone
        self.audio.start()

        logger.info("═" * 50)
        logger.info("  PARALLEL MIND IS LISTENING")
        logger.info(f"  Wake words: {config.WAKE_WORDS}")
        logger.info(f"  Memories: {self.memory.count()}")
        logger.info("═" * 50)

        self.tts.speak("Parallel Mind online. Listening.", block=False)

        try:
            for audio_chunk in self.audio.chunks():
                if not self._running:
                    break

                # Feed chunk into VAD; get back a complete speech segment or None
                speech = self.vad.process_chunk(audio_chunk)
                if speech is None:
                    continue

                # Transcribe in a daemon thread (non-blocking)
                threading.Thread(
                    target=self._transcribe_and_process,
                    args=(speech,),
                    daemon=True,
                    name="stt-worker",
                ).start()

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received — shutting down")
        finally:
            self._shutdown()

    def _transcribe_and_process(self, speech_audio) -> None:
        """Run STT then dispatch to _process_speech (runs in a thread)."""
        text = self.stt.transcribe(speech_audio)
        if text:
            self._process_speech(text)

    def _shutdown(self) -> None:
        self._running = False
        self.audio.stop()
        uptime = datetime.now() - datetime.fromisoformat(self._stats["start_time"])
        logger.info(
            f"Parallel Mind shutdown — "
            f"uptime: {str(uptime).split('.')[0]} | "
            f"memories stored: {self._stats['memories_stored']} | "
            f"queries answered: {self._stats['queries_answered']}"
        )


# ─── Fallback TTS (print-only) ────────────────────────────────────────────────

class _ConsoleTTS:
    """Used when TTS is disabled. Prints responses to stdout."""
    available = False

    def speak(self, text: str, block: bool = True) -> bool:
        print(f"\n🔊  PARALLEL MIND: {text}\n")
        return True

    def stop(self) -> None:
        pass


# ═════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═════════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parallel Mind — wearable AI memory system"
    )
    parser.add_argument(
        "--no-tts",
        action="store_true",
        help="Disable TTS output (print responses instead)",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.list_devices:
        cap = AudioCapture()
        print("\nAvailable audio input devices:")
        for idx, name in cap.list_input_devices():
            print(f"  [{idx}] {name}")
        print(
            "\nSet AUDIO_INPUT_DEVICE=<index> in .env to use a specific device."
        )
        return

    mind = ParallelMind(enable_tts=not args.no_tts)

    # Graceful shutdown on SIGTERM / SIGINT
    def _handle_signal(sig, _frame):
        logger.info(f"Signal {sig} received — stopping")
        mind._running = False

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    mind.run()


if __name__ == "__main__":
    main()
