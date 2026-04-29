"""
Parallel Mind — Pi Backend Configuration
All values read from .env (or environment). Only NVIDIA_API_KEY is required.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── NVIDIA NIM  (REQUIRED) ──────────────────────────────────────────────────
NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
NVIDIA_MAX_TOKENS: int = int(os.getenv("NVIDIA_MAX_TOKENS", "1024"))
NVIDIA_TEMPERATURE: float = float(os.getenv("NVIDIA_TEMPERATURE", "0.6"))

# ─── GROQ FALLBACK ───────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# ─── GOOGLE GEMINI FALLBACK (OpenAI-compat endpoint) ─────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

# ─── GITHUB MODELS FALLBACK ──────────────────────────────────────────────────
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
GITHUB_MODEL: str = os.getenv("GITHUB_MODEL", "gpt-4o-mini")
GITHUB_BASE_URL: str = "https://models.inference.ai.azure.com"

# ─── AUDIO / MIC ─────────────────────────────────────────────────────────────
SAMPLE_RATE: int = 16000          # 16 kHz — required by Silero VAD & Whisper
CHANNELS: int = 1
PYAUDIO_CHUNK: int = 512          # Silero VAD window: 512 samples @ 16kHz = 32 ms
AUDIO_DEVICE_INDEX: int = int(os.getenv("AUDIO_DEVICE_INDEX", "-1"))  # -1 = system default

# ─── SILERO VAD ──────────────────────────────────────────────────────────────
VAD_THRESHOLD: float = float(os.getenv("VAD_THRESHOLD", "0.5"))
VAD_MIN_SPEECH_MS: int = int(os.getenv("VAD_MIN_SPEECH_MS", "250"))
VAD_MIN_SILENCE_MS: int = int(os.getenv("VAD_MIN_SILENCE_MS", "800"))
VAD_SPEECH_PAD_MS: int = int(os.getenv("VAD_SPEECH_PAD_MS", "30"))

# ─── FASTER-WHISPER STT ──────────────────────────────────────────────────────
WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base")   # base = good Pi balance
WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8 = fastest on Pi
WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "en")
WHISPER_BEAM_SIZE: int = int(os.getenv("WHISPER_BEAM_SIZE", "1"))   # 1 = fastest greedy decode

# ─── DATA / CHROMADB ─────────────────────────────────────────────────────────
DATA_DIR: Path = Path(os.path.expanduser(os.getenv("DATA_DIR", "~/.parallel_mind")))
CHROMA_PATH: str = str(DATA_DIR / "chromadb")
CHROMA_COLLECTION: str = "conversations"

# ─── EMBEDDINGS ──────────────────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ─── SPACY TOPIC TAGGER ──────────────────────────────────────────────────────
SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_sm")

# ─── RAG ─────────────────────────────────────────────────────────────────────
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))

# ─── PIPER TTS ───────────────────────────────────────────────────────────────
VOICES_DIR: Path = DATA_DIR / "voices"
PIPER_VOICE: str = os.getenv("PIPER_VOICE", "en_US-lessac-medium")

# ─── WAKE WORDS ──────────────────────────────────────────────────────────────
WAKE_WORDS: list[str] = [
    w.strip().lower()
    for w in os.getenv("WAKE_WORDS", "hey memory,ok memory,parallel mind").split(",")
    if w.strip()
]
QUERY_TIMEOUT_SECONDS: float = float(os.getenv("QUERY_TIMEOUT_SECONDS", "10.0"))

# ─── PROACTIVE ASSIST ────────────────────────────────────────────────────────
PROACTIVE_KEYWORDS: list[str] = [
    k.strip().lower()
    for k in os.getenv(
        "PROACTIVE_KEYWORDS",
        "meeting,client,project,deadline,presentation,interview,standup,demo",
    ).split(",")
    if k.strip()
]
PROACTIVE_LOOKBACK_HOURS: int = int(os.getenv("PROACTIVE_LOOKBACK_HOURS", "48"))
# Debounce — don't re-trigger proactive for same keyword within N seconds
PROACTIVE_DEBOUNCE_SECONDS: int = int(os.getenv("PROACTIVE_DEBOUNCE_SECONDS", "300"))

# ─── API SERVER ──────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8765"))
API_TOKEN: str = os.getenv("API_TOKEN", "")   # Optional bearer token; empty = no auth

# ─── GPIO MUTE BUTTON (optional, Pi only) ────────────────────────────────────
MUTE_GPIO_PIN: int = int(os.getenv("MUTE_GPIO_PIN", "17"))   # BCM pin 17
GPIO_ENABLED: bool = os.getenv("GPIO_ENABLED", "false").lower() == "true"
"""
Parallel Mind — Central Configuration
All settings are loaded from .env (or OS environment variables).
Only NVIDIA_API_KEY is required; everything else has sensible Pi defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
CHROMA_DIR = DATA_DIR / "chroma"
MODELS_DIR = DATA_DIR / "models"
LOGS_DIR = DATA_DIR / "logs"

for _d in [DATA_DIR, TRANSCRIPTS_DIR, CHROMA_DIR, MODELS_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ─── NVIDIA NIM (Primary LLM) ─────────────────────────────────────────────────
NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
# Free models: meta/llama-3.1-70b-instruct, nvidia/llama-3.1-nemotron-70b-instruct
# mistralai/mistral-large-2-instruct, meta/llama-3.3-70b-instruct
NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
NVIDIA_MAX_RPM: int = int(os.getenv("NVIDIA_MAX_RPM", "35"))  # Stay under 40/min hard limit

# ─── Fallback LLMs ────────────────────────────────────────────────────────────
# Groq: https://console.groq.com — 14,400 req/day free
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# ─── Speech-to-Text ───────────────────────────────────────────────────────────
# Pi 5 (8GB): "small" is fine; Pi 4: stick to "base"
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "en")
WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
# int8 is fastest on CPU (Pi); int16 if you get accuracy issues
WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# ─── Audio ────────────────────────────────────────────────────────────────────
SAMPLE_RATE: int = 16000          # 16kHz — required by Whisper and Silero VAD
CHANNELS: int = 1                  # Mono
# MUST be 512 for Silero VAD at 16kHz (32ms window)
AUDIO_CHUNK_SAMPLES: int = 512
# Leave empty for auto-detect (will find ReSpeaker HAT automatically)
AUDIO_INPUT_DEVICE_INDEX: int | None = (
    int(os.getenv("AUDIO_INPUT_DEVICE", ""))
    if os.getenv("AUDIO_INPUT_DEVICE", "").strip()
    else None
)

# ─── Voice Activity Detection ─────────────────────────────────────────────────
VAD_THRESHOLD: float = float(os.getenv("VAD_THRESHOLD", "0.5"))
VAD_MIN_SPEECH_MS: int = int(os.getenv("VAD_MIN_SPEECH_MS", "500"))
VAD_MIN_SILENCE_MS: int = int(os.getenv("VAD_MIN_SILENCE_MS", "600"))
VAD_SPEECH_PAD_MS: int = int(os.getenv("VAD_SPEECH_PAD_MS", "300"))

# ─── Memory / Vector DB ───────────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHROMA_COLLECTION: str = "parallel_mind_memory"
MEMORY_TOP_K: int = int(os.getenv("MEMORY_TOP_K", "5"))

# ─── Wake Words ───────────────────────────────────────────────────────────────
WAKE_WORDS: list[str] = [
    w.strip().lower()
    for w in os.getenv("WAKE_WORDS", "hey mind,parallel mind,hey memory,what did").split(",")
    if w.strip()
]
QUERY_CAPTURE_TIMEOUT_S: float = float(os.getenv("QUERY_CAPTURE_TIMEOUT_S", "12.0"))

# ─── Proactive Mode ───────────────────────────────────────────────────────────
PROACTIVE_ENABLED: bool = os.getenv("PROACTIVE_ENABLED", "true").lower() == "true"
PROACTIVE_KEYWORDS: list[str] = [
    k.strip().lower()
    for k in os.getenv(
        "PROACTIVE_KEYWORDS",
        "meeting,project,client,deadline,presentation,call,interview,demo"
    ).split(",")
    if k.strip()
]
PROACTIVE_COOLDOWN_MIN: int = int(os.getenv("PROACTIVE_COOLDOWN_MIN", "5"))

# ─── Text-to-Speech ───────────────────────────────────────────────────────────
TTS_ENABLED: bool = os.getenv("TTS_ENABLED", "true").lower() == "true"
# Voices: en_US-lessac-medium, en_US-arctic-medium, en_GB-alan-medium
TTS_VOICE: str = os.getenv("TTS_VOICE", "en_US-lessac-medium")

# ─── Optional REST API ────────────────────────────────────────────────────────
API_ENABLED: bool = os.getenv("API_ENABLED", "true").lower() == "true"
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# ─── System ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

# Validate critical config
if not NVIDIA_API_KEY:
    import warnings
    warnings.warn(
        "NVIDIA_API_KEY is not set. LLM responses will use Groq fallback only. "
        "Get a free key at https://build.nvidia.com/",
        stacklevel=1,
    )
