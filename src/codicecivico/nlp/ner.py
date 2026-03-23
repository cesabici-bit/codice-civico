"""Named entity recognition utilities for Italian text.

Provides sentence splitting via spaCy it_core_news_lg with regex fallback.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# spaCy lazy loading (graceful degradation if not installed)
# ---------------------------------------------------------------------------

_nlp: Any = None
_spacy_available: bool | None = None


def _get_spacy_nlp() -> Any:
    """Load spaCy Italian model lazily. Returns None if unavailable."""
    global _nlp, _spacy_available  # noqa: PLW0603
    if _spacy_available is not None:
        return _nlp

    try:
        import spacy

        _nlp = spacy.load("it_core_news_lg")
        _spacy_available = True
        logger.info("spaCy it_core_news_lg loaded successfully")
    except (ImportError, OSError) as exc:
        _spacy_available = False
        logger.warning("spaCy unavailable, using regex fallback: %s", exc)
    return _nlp


# ---------------------------------------------------------------------------
# Regex fallback for sentence splitting
# ---------------------------------------------------------------------------

# Splits on sentence-ending punctuation followed by whitespace and uppercase
_SENTENCE_RE = re.compile(
    r'(?<=[.!?;])\s+(?=[A-ZÀÈÉÌÒÙ"])',
)


def _split_sentences_regex(text: str) -> list[str]:
    """Split Italian text into sentences using regex heuristics."""
    parts = _SENTENCE_RE.split(text.strip())
    return [s.strip() for s in parts if s.strip()]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def split_sentences(text: str) -> list[str]:
    """Split Italian text into sentences.

    Uses spaCy it_core_news_lg when available, falls back to regex.
    Always returns at least one sentence for non-empty input.
    """
    if not text or not text.strip():
        return []

    nlp = _get_spacy_nlp()
    if nlp is not None:
        doc = nlp(text.strip())
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        if sentences:
            return sentences

    # Fallback: regex
    return _split_sentences_regex(text)


def extract_entities(text: str) -> list[dict[str, str]]:
    """Extract named entities from Italian text via spaCy.

    Returns list of {text, label} dicts. Empty list if spaCy unavailable.
    """
    nlp = _get_spacy_nlp()
    if nlp is None:
        return []

    doc = nlp(text)
    return [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
