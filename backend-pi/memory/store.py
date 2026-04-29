"""
Parallel Mind — ChromaDB vector store.

Provides:
  store_transcript()      — embed + save a transcript chunk
  query_memory()          — semantic search, returns ranked docs
  get_recent_transcripts()— retrieve by time window
  get_stats()             — basic stats (count, path)
  delete_before()         — privacy: wipe entries older than a timestamp

ChromaDB ≥ 0.5 API is used throughout (PersistentClient).
All operations are synchronous and safe to call from threads.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from functools import lru_cache

import chromadb
from loguru import logger

import config
from memory.embedder import embed_one
from memory.tagger import extract_topics


# ── ChromaDB singleton ────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_collection():
    os.makedirs(config.CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=config.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(
        f"ChromaDB ready: collection='{config.CHROMA_COLLECTION}', "
        f"path='{config.CHROMA_PATH}', "
        f"documents={collection.count()}"
    )
    return collection


# ── Public API ────────────────────────────────────────────────────────────────

def store_transcript(text: str, speaker: str = "unknown") -> str:
    """
    Embed and persist a transcript segment.
    Returns the document UUID, or empty string if text is blank.
    """
    text = text.strip()
    if not text:
        return ""

    collection = _get_collection()
    doc_id = str(uuid.uuid4())
    ts = time.time()
    topics = extract_topics(text)
    embedding = embed_one(text)

    collection.add(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[
            {
                "timestamp": ts,
                "datetime": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "speaker": speaker,
                "topics": ",".join(topics),
                "char_count": len(text),
            }
        ],
    )
    logger.debug(
        f"Stored transcript id={doc_id[:8]}  len={len(text)}  topics={topics}"
    )
    return doc_id


def query_memory(
    query_text: str,
    top_k: int | None = None,
    since_timestamp: float | None = None,
) -> list[dict]:
    """
    Semantic search over the conversation store.

    Returns a list of dicts:
      { "text": str, "metadata": dict, "relevance": float [0–1] }
    Sorted by relevance descending.
    """
    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return []

    k = min(top_k or config.RAG_TOP_K, total)
    query_embedding = embed_one(query_text)

    where: dict | None = None
    if since_timestamp is not None:
        where = {"timestamp": {"$gte": since_timestamp}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs: list[dict] = []
    raw_docs = results.get("documents") or [[]]
    raw_metas = results.get("metadatas") or [[]]
    raw_dists = results.get("distances") or [[]]

    for doc, meta, dist in zip(raw_docs[0], raw_metas[0], raw_dists[0]):
        docs.append(
            {
                "text": doc,
                "metadata": meta,
                # cosine distance in [0,2] → relevance in [0,1]
                "relevance": round(max(0.0, 1.0 - dist), 4),
            }
        )

    # Already sorted by distance (nearest first) by ChromaDB
    return docs


def get_recent_transcripts(hours: int = 24) -> list[dict]:
    """
    Retrieve transcripts from the last `hours` hours, oldest first.
    """
    collection = _get_collection()
    if collection.count() == 0:
        return []

    since = time.time() - hours * 3600
    results = collection.get(
        where={"timestamp": {"$gte": since}},
        include=["documents", "metadatas"],
    )

    docs = []
    for doc, meta in zip(
        results.get("documents") or [],
        results.get("metadatas") or [],
    ):
        docs.append({"text": doc, "metadata": meta})

    return sorted(docs, key=lambda x: x["metadata"].get("timestamp", 0))


def delete_before(timestamp: float) -> int:
    """
    Delete all documents with timestamp < `timestamp`.
    Returns the number of deleted documents.
    """
    collection = _get_collection()
    results = collection.get(
        where={"timestamp": {"$lt": timestamp}},
        include=[],   # only IDs needed
    )
    ids = results.get("ids") or []
    if ids:
        collection.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} documents older than timestamp {timestamp:.0f}")
    return len(ids)


def get_stats() -> dict:
    collection = _get_collection()
    return {
        "total_segments": collection.count(),
        "collection": config.CHROMA_COLLECTION,
        "path": config.CHROMA_PATH,
        "embedding_model": config.EMBEDDING_MODEL,
    }
"""
Persistent vector memory store backed by ChromaDB.
All data lives locally on the Pi under data/chroma/ — no cloud, no cost.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    CRUD wrapper around a single ChromaDB collection.

    Schema per document
    -------------------
    id          : "mem_<unix_timestamp_ms>"
    embedding   : List[float]   — sentence-transformers vector
    document    : str           — raw transcript text
    metadata    : {
        timestamp : ISO-8601 string,
        topics    : comma-separated tag string,
        source    : "microphone" | "manual" | …
    }
    """

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "parallel_mind_memory",
    ) -> None:
        self._collection_name = collection_name
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"ChromaDB ready: '{collection_name}' "
            f"({self._collection.count()} memories stored)"
        )

    # ── Write ─────────────────────────────────────────────────────────────────

    def store(
        self,
        text: str,
        embedding: List[float],
        topics: Optional[List[str]] = None,
        source: str = "microphone",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Persist a transcript chunk. Returns the generated document ID."""
        ts = datetime.now()
        doc_id = f"mem_{int(ts.timestamp() * 1000)}"

        metadata: Dict[str, Any] = {
            "timestamp": ts.isoformat(),
            "topics": ",".join(topics or ["general"]),
            "source": source,
        }
        if extra_metadata:
            metadata.update(extra_metadata)

        self._collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
        logger.debug(f"Memory stored: {doc_id} | topics={metadata['topics']}")
        return doc_id

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        embedding: List[float],
        n_results: int = 5,
        topic_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic similarity search.
        Returns list of {text, metadata, relevance} dicts sorted best-first.
        """
        total = self._collection.count()
        if total == 0:
            return []

        n = min(n_results, total)
        kwargs: Dict[str, Any] = dict(
            query_embeddings=[embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        # ChromaDB `where` clause: exact string match on metadata fields
        if topic_filter:
            kwargs["where"] = {"topics": {"$contains": topic_filter}}

        try:
            results = self._collection.query(**kwargs)
        except Exception:
            # where-filter may error if no docs match; fall back without filter
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=n,
                include=["documents", "metadatas", "distances"],
            )

        memories: List[Dict[str, Any]] = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            memories.append(
                {
                    "text": doc,
                    "metadata": meta,
                    "relevance": round(1.0 - float(dist), 4),
                }
            )
        return memories

    # ── Retrieval helpers ─────────────────────────────────────────────────────

    def get_recent(
        self,
        hours: int = 24,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return up to *limit* most recent memories from the last *hours* hours."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        try:
            results = self._collection.get(
                where={"timestamp": {"$gte": cutoff}},
                limit=limit,
                include=["documents", "metadatas"],
            )
            return [
                {"text": doc, "metadata": meta}
                for doc, meta in zip(results["documents"], results["metadatas"])
            ]
        except Exception as e:
            logger.debug(f"get_recent filter error: {e} — returning empty")
            return []

    def count(self) -> int:
        return self._collection.count()
