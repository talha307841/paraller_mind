"""
Parallel Mind — FastAPI REST server.

Endpoints consumed by:
  • ESP32 glasses  — GET /esp32/latest  (polls for new response text)
  • Dashboard / curl  — POST /query, GET /recent, GET /stats
  • Physical controls — POST /mute, POST /unmute

Auth: if API_TOKEN is set in .env, all non-/health endpoints require
      the header  Authorization: Bearer <token>.
      Leave it empty for trusted LAN use (default).
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger

import config
import state
from llm.rag import answer_query
from memory.store import get_stats, get_recent_transcripts, delete_before

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Parallel Mind",
    description="Wearable AI memory system — Pi backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# ── Auth ──────────────────────────────────────────────────────────────────────

def _verify_token(authorization: Optional[str] = Header(default=None)) -> None:
    """Bearer token guard — skipped entirely when API_TOKEN is not configured."""
    if not config.API_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header (Bearer <token>)",
        )
    token = authorization.split(" ", 1)[1]
    if token != config.API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token",
        )


_AuthDep = Depends(_verify_token)

# ── Schemas ───────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    latency_ms: float


class StatusResponse(BaseModel):
    muted: bool
    recording: bool


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health():
    """Health check — no auth required."""
    return {"status": "ok", "service": "parallel-mind", "ts": time.time()}


@app.get("/stats", dependencies=[_AuthDep], tags=["memory"])
def stats():
    """Memory statistics: document count, storage path, embedding model."""
    return get_stats()


@app.post("/query", response_model=QueryResponse, dependencies=[_AuthDep], tags=["query"])
def query(req: QueryRequest):
    """
    RAG query.  Searches memory and returns an LLM-generated answer.
    The same pipeline as a voice query — useful for testing via curl / dashboard.
    """
    t0 = time.perf_counter()
    answer, docs = answer_query(req.query)
    latency_ms = (time.perf_counter() - t0) * 1000

    sources = [
        {
            "text": d["text"][:300],
            "datetime": d["metadata"].get("datetime"),
            "topics": d["metadata"].get("topics", "").split(","),
            "relevance": d.get("relevance"),
        }
        for d in docs
    ]
    return QueryResponse(answer=answer, sources=sources, latency_ms=round(latency_ms, 1))


@app.get("/recent", dependencies=[_AuthDep], tags=["memory"])
def recent(hours: int = 24):
    """
    Retrieve the last N hours of transcript segments (newest 50 max).
    Useful for a monitoring dashboard.
    """
    if hours < 1 or hours > 720:
        raise HTTPException(400, "hours must be between 1 and 720")
    docs = get_recent_transcripts(hours=hours)
    return {
        "hours": hours,
        "count": len(docs),
        "transcripts": [
            {
                "text": d["text"][:400],
                "datetime": d["metadata"].get("datetime"),
                "topics": d["metadata"].get("topics", "").split(","),
            }
            for d in docs[-50:]
        ],
    }


@app.delete("/memory/before", dependencies=[_AuthDep], tags=["memory"])
def wipe_before(timestamp: float):
    """
    Privacy endpoint: delete all transcripts before the given Unix timestamp.
    """
    deleted = delete_before(timestamp)
    return {"deleted": deleted, "before_timestamp": timestamp}


# ── ESP32 / glasses endpoint ──────────────────────────────────────────────────

@app.get("/esp32/latest", dependencies=[_AuthDep], tags=["glasses"])
def esp32_latest():
    """
    Ultra-light polling endpoint for the XIAO ESP32S3 OLED display.
    Returns latest response text (truncated to 128 chars) + Unix timestamp.
    ESP32 firmware should poll this at ~1 Hz and update the OLED when ts changes.
    """
    return state.get_latest_response()


# ── Microphone control ────────────────────────────────────────────────────────

@app.post("/mute", dependencies=[_AuthDep], tags=["control"])
def mute() -> StatusResponse:
    """Mute the microphone (stops recording + VAD processing)."""
    if state.recorder is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Recorder not running")
    state.recorder.mute()
    return StatusResponse(muted=True, recording=True)


@app.post("/unmute", dependencies=[_AuthDep], tags=["control"])
def unmute() -> StatusResponse:
    """Unmute the microphone."""
    if state.recorder is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Recorder not running")
    state.recorder.unmute()
    return StatusResponse(muted=False, recording=True)


@app.get("/status", dependencies=[_AuthDep], tags=["control"])
def mic_status() -> StatusResponse:
    """Return whether the microphone is currently muted."""
    muted = state.recorder.is_muted if state.recorder else False
    return StatusResponse(muted=muted, recording=state.recorder is not None)
"""
Optional FastAPI REST server — lets you query Parallel Mind from a phone,
laptop, or any browser on the same WiFi network as the Pi.

Endpoints
---------
GET  /health              — system status, memory count, uptime
GET  /memories/recent     — last N memories (default 24 h)
GET  /memories/search     — semantic search (query param: q)
POST /query               — RAG query + optional TTS playback
GET  /stats               — runtime statistics
POST /store               — manually store a memory (e.g. from phone)

Run alongside main.py: it is started as a daemon thread from main.py.
"""
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Parallel Mind API",
    description="Wearable AI memory system — REST interface",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Injected by init() — all Optional so startup doesn't crash without them
_rag: Any = None
_memory_store: Any = None
_tts: Any = None
_stats: Dict[str, Any] = {}
_start_time: datetime = datetime.now()


def init(rag, memory_store, tts, stats: Dict[str, Any]) -> None:
    """Call this from main.py before starting the server thread."""
    global _rag, _memory_store, _tts, _stats, _start_time
    _rag = rag
    _memory_store = memory_store
    _tts = tts
    _stats = stats
    _start_time = datetime.now()
    logger.info("Parallel Mind API initialised")


# ── Request / Response schemas ────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    speak: bool = Field(False, description="Speak the answer via TTS")
    top_k: int = Field(5, ge=1, le=20)


class QueryResponse(BaseModel):
    answer: str
    memories_used: int
    source: str
    timestamp: str


class StoreRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    topics: Optional[List[str]] = None
    source: str = "manual"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> Dict[str, Any]:
    uptime = str(datetime.now() - _start_time).split(".")[0]
    return {
        "status": "online",
        "uptime": uptime,
        "memory_count": _memory_store.count() if _memory_store else 0,
        "tts_available": bool(_tts and _tts.available) if _tts else False,
    }


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    if _rag is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not ready")

    result = _rag.query(req.question, n_results=req.top_k)

    if req.speak and _tts is not None:
        threading.Thread(
            target=_tts.speak,
            args=(result["answer"],),
            kwargs={"block": False},
            daemon=True,
        ).start()

    return QueryResponse(
        answer=result["answer"],
        memories_used=result["memory_count"],
        source=result["source"],
        timestamp=datetime.now().isoformat(),
    )


@app.get("/memories/recent")
def memories_recent(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    if _memory_store is None:
        raise HTTPException(status_code=503, detail="Memory store not ready")
    return _memory_store.get_recent(hours=hours, limit=limit)


@app.get("/memories/search")
def memories_search(
    q: str = Query(..., min_length=2, max_length=500),
    top_k: int = Query(5, ge=1, le=20),
) -> Dict[str, Any]:
    if _rag is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not ready")
    result = _rag.query(q, n_results=top_k)
    # Return just memories without generating an LLM answer
    return {
        "query": q,
        "memories": result["memories"],
        "count": result["memory_count"],
    }


@app.post("/store", status_code=201)
def store_memory(req: StoreRequest) -> Dict[str, str]:
    if _rag is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not ready")
    doc_id = _rag.store_transcript(
        text=req.text,
        topics=req.topics,
        source=req.source,
    )
    if not doc_id:
        raise HTTPException(status_code=500, detail="Failed to store memory")
    return {"id": doc_id, "status": "stored"}


@app.get("/stats")
def stats() -> Dict[str, Any]:
    return {
        **_stats,
        "start_time": str(_start_time),
        "uptime_s": (datetime.now() - _start_time).total_seconds(),
        "memory_count": _memory_store.count() if _memory_store else 0,
    }


# ── Server runner ─────────────────────────────────────────────────────────────

def start(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the API server (blocking). Designed to run in a daemon thread."""
    logger.info(f"Parallel Mind API listening on http://{host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
