"""
Parallel Mind — spaCy topic/entity tagger.

Extracts a short list of topic labels from a transcript chunk.
Used for metadata stored alongside each ChromaDB document so you can
visually browse what a segment is about.

Gracefully degrades to a keyword-match-only approach if the spaCy model
isn't installed (run `python -m spacy download en_core_web_sm`).
"""

from __future__ import annotations

from functools import lru_cache

import config

# Named entity labels we care about
_NE_LABELS = frozenset(
    {"PERSON", "ORG", "GPE", "EVENT", "PRODUCT", "WORK_OF_ART", "FAC", "LOC"}
)


@lru_cache(maxsize=1)
def _get_nlp():
    from loguru import logger

    try:
        import spacy
        nlp = spacy.load(config.SPACY_MODEL, disable=["parser", "ner"])
        # Re-enable ner — we disabled it above to load faster, now load full
        nlp = spacy.load(config.SPACY_MODEL)
        logger.info(f"spaCy model '{config.SPACY_MODEL}' loaded.")
        return nlp
    except OSError:
        logger.warning(
            f"spaCy model '{config.SPACY_MODEL}' not found. "
            "Run: python -m spacy download en_core_web_sm"
        )
        return None


def extract_topics(text: str) -> list[str]:
    """
    Return up to 8 topic strings from a transcript segment.
    Combines named entities, noun chunks, and proactive keyword matches.
    """
    topics: set[str] = set()

    # ── Proactive keyword match (always runs, no model needed) ───────────────
    text_lower = text.lower()
    for kw in config.PROACTIVE_KEYWORDS:
        if kw in text_lower:
            topics.add(kw)

    # ── spaCy NER + noun chunks ───────────────────────────────────────────────
    nlp = _get_nlp()
    if nlp is not None:
        doc = nlp(text[:1000])   # cap for Pi performance

        for ent in doc.ents:
            if ent.label_ in _NE_LABELS:
                topics.add(ent.text.strip().lower())

        for chunk in doc.noun_chunks:
            noun = chunk.text.strip().lower()
            # Keep only short, meaningful noun phrases
            if 1 < len(noun.split()) <= 3 and len(noun) > 3:
                topics.add(noun)

    # Sort for deterministic output; cap at 8
    return sorted(topics)[:8]
"""
Topic tagger using spaCy NER + keyword matching.
Returns a list of topic tags for a transcript chunk so memories can be
filtered later (e.g. "show me everything tagged 'meeting'").
"""
import logging
import subprocess
from typing import List

logger = logging.getLogger(__name__)

# Keyword → topic mapping (supplement NER with domain heuristics)
_KEYWORD_TOPICS: dict[str, list[str]] = {
    "meeting":      ["meeting", "meet", "conference", "standup", "sync", "call", "agenda"],
    "project":      ["project", "task", "ticket", "milestone", "deliverable", "sprint"],
    "finance":      ["money", "budget", "invoice", "payment", "salary", "cost", "revenue", "price"],
    "health":       ["doctor", "hospital", "medicine", "pain", "symptoms", "diet", "exercise"],
    "food":         ["eat", "food", "restaurant", "lunch", "dinner", "breakfast", "coffee", "cook"],
    "travel":       ["flight", "hotel", "trip", "travel", "airport", "drive", "commute"],
    "technology":   ["code", "software", "bug", "deploy", "server", "api", "database", "commit"],
    "social":       ["friend", "family", "party", "wedding", "birthday", "date"],
}


class TopicTagger:
    """
    Assigns topic tags to a piece of text using:
      1. spaCy named-entity recognition (PERSON, ORG, GPE, MONEY, DATE …)
      2. Keyword heuristics for domain-specific topics
    """

    def __init__(self, model: str = "en_core_web_sm") -> None:
        self._model_name = model
        self._nlp = None
        self._load()

    def _load(self) -> None:
        try:
            import spacy
            self._nlp = spacy.load(self._model_name)
            logger.info(f"spaCy '{self._model_name}' loaded")
        except OSError:
            logger.warning(f"spaCy model '{self._model_name}' not found — downloading …")
            try:
                subprocess.run(
                    ["python3", "-m", "spacy", "download", self._model_name],
                    check=True,
                    capture_output=True,
                )
                import spacy
                self._nlp = spacy.load(self._model_name)
                logger.info(f"spaCy '{self._model_name}' downloaded and loaded")
            except Exception as e:
                logger.error(f"spaCy load failed: {e}. Topic tagging will be keyword-only.")
                self._nlp = None
        except Exception as e:
            logger.error(f"spaCy load error: {e}. Topic tagging will be keyword-only.")
            self._nlp = None

    # ── Public interface ──────────────────────────────────────────────────────

    def tag(self, text: str) -> List[str]:
        """Return a deduplicated list of topic tags for *text*."""
        tags: set[str] = set()
        text_lower = text.lower()

        # 1. Keyword heuristics
        for topic, keywords in _KEYWORD_TOPICS.items():
            if any(kw in text_lower for kw in keywords):
                tags.add(topic)

        # 2. spaCy NER
        if self._nlp is not None:
            try:
                doc = self._nlp(text[:1000])  # limit to avoid slow processing
                for ent in doc.ents:
                    if ent.label_ == "PERSON":
                        tags.add("person")
                    elif ent.label_ in ("ORG", "PRODUCT", "WORK_OF_ART"):
                        tags.add("organization")
                    elif ent.label_ == "GPE":
                        tags.add("location")
                    elif ent.label_ in ("DATE", "TIME"):
                        tags.add("temporal")
                    elif ent.label_ == "MONEY":
                        tags.add("finance")
                    elif ent.label_ == "EVENT":
                        tags.add("event")
            except Exception as e:
                logger.debug(f"spaCy NER error: {e}")

        return list(tags) if tags else ["general"]

    def extract_noun_phrases(self, text: str) -> List[str]:
        """Extract key noun phrases for richer search queries."""
        if self._nlp is None:
            return []
        try:
            doc = self._nlp(text[:500])
            return [chunk.text.lower() for chunk in doc.noun_chunks if len(chunk.text) > 2][:8]
        except Exception:
            return []
