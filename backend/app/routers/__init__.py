# API Routers module
from .transcribe import router as transcribe_router
from .embeddings import router as embeddings_router
from .memory import router as memory_router
from .suggest import router as suggest_router
from .events import router as events_router

__all__ = [
    "transcribe_router",
    "embeddings_router",
    "memory_router",
    "suggest_router",
    "events_router"
]
