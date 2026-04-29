"""
Parallel Mind — Sentence embeddings singleton.
Uses sentence-transformers (all-MiniLM-L6-v2 by default).
Model downloads once on first call (~80 MB) and reuses the cached weights.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

import config


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    from loguru import logger
    logger.info(f"Loading embedding model '{config.EMBEDDING_MODEL}'...")
    model = SentenceTransformer(config.EMBEDDING_MODEL)
    logger.info("Embedding model ready.")
    return model


def embed_one(text: str) -> list[float]:
    """Embed a single string. Returns a list[float] (ChromaDB-compatible)."""
    vec: np.ndarray = _get_model().encode(
        [text], convert_to_numpy=True, normalize_embeddings=True
    )[0]
    return vec.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings efficiently."""
    if not texts:
        return []
    vecs: np.ndarray = _get_model().encode(
        texts, convert_to_numpy=True, normalize_embeddings=True
    )
    return vecs.tolist()
