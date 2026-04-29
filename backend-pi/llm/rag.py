"""
Parallel Mind — RAG (Retrieval-Augmented Generation) pipeline.

Flow:
  1. Embed the user's query with sentence-transformers
  2. Retrieve top-K most relevant transcript chunks from ChromaDB
  3. Build a context-aware prompt
  4. Call the LLM (NVIDIA NIM → fallbacks)
  5. Return (answer_text, source_docs)

The system prompt is tuned for spoken-word output — concise, no markdown,
no bullet lists.
"""

from __future__ import annotations

from loguru import logger

import config
from llm.client import chat
from memory.store import query_memory

_SYSTEM_PROMPT = (
    "You are Parallel Mind, a personal AI memory assistant running on "
    "a Raspberry Pi worn by the user. "
    "You have access to transcripts of real conversations the user has had. "
    "Answer in plain spoken language — no bullet points, no markdown, no headers. "
    "Be direct and concise: 1–3 sentences unless the user explicitly asks for more. "
    "If the provided memories don't contain enough information to answer, "
    "say so honestly rather than guessing."
)

_NO_MEMORY_PROMPT = (
    "The user asked: {query}\n\n"
    "No relevant memories were found for this query. "
    "Let the user know politely and suggest they let the system keep listening."
)


def answer_query(query: str) -> tuple[str, list[dict]]:
    """
    Full RAG pipeline: retrieve → prompt → LLM → answer.

    Returns:
      (answer_text: str, source_docs: list[dict])
    """
    logger.info(f"RAG query: {query!r}")

    docs = query_memory(query, top_k=config.RAG_TOP_K)

    if not docs:
        logger.info("No relevant memories found for query.")
        answer = chat(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _NO_MEMORY_PROMPT.format(query=query),
                },
            ]
        )
        return answer, []

    # Build context block (most relevant first — already sorted by ChromaDB)
    context_parts: list[str] = []
    for i, doc in enumerate(docs, start=1):
        meta = doc["metadata"]
        dt = meta.get("datetime", "unknown time")
        topics = meta.get("topics", "")
        relevance = doc.get("relevance", 0)
        context_parts.append(
            f"[Memory {i} | {dt} | topics: {topics} | relevance: {relevance:.2f}]\n"
            f"{doc['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Here are the most relevant memories from your conversations:\n\n"
                f"{context}\n\n"
                f"---\n\n"
                f"User question: {query}"
            ),
        },
    ]

    answer = chat(messages)
    logger.info(f"RAG answer ({len(answer)} chars): {answer[:80]}…")
    return answer, docs
