"""Promise-legislation semantic matching via sentence embeddings.

Matches extracted promises against LegislativeAct titles using:
1. sentence-transformers MiniLM-L12 embeddings (if available)
2. TF-IDF fallback (always available, no ML deps)

Architecture: pure functions for matching logic, DB orchestration separate.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.models import LegislativeAct, Promise

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding backends (lazy loading)
# ---------------------------------------------------------------------------

_st_model: Any = None
_st_available: bool | None = None


def _get_sentence_transformer() -> Any:
    """Load sentence-transformers model lazily. Returns None if unavailable."""
    global _st_model, _st_available  # noqa: PLW0603
    if _st_available is not None:
        return _st_model

    try:
        from sentence_transformers import SentenceTransformer

        _st_model = SentenceTransformer("all-MiniLM-L12-v2")
        _st_available = True
        logger.info("sentence-transformers MiniLM-L12 loaded")
    except (ImportError, OSError) as exc:
        _st_available = False
        logger.warning("sentence-transformers unavailable, using TF-IDF fallback: %s", exc)
    return _st_model


# ---------------------------------------------------------------------------
# Pure matching functions
# ---------------------------------------------------------------------------


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def encode_texts_st(texts: list[str]) -> list[list[float]]:
    """Encode texts using sentence-transformers. Raises if unavailable."""
    model = _get_sentence_transformer()
    if model is None:
        msg = "sentence-transformers not available"
        raise RuntimeError(msg)
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [e.tolist() for e in embeddings]


def encode_texts_tfidf(texts: list[str]) -> list[list[float]]:
    """Encode texts using simple TF-IDF (no ML deps required).

    Uses a basic word-frequency approach as a lightweight fallback.
    """
    # Build vocabulary from all texts
    vocab: dict[str, int] = {}
    for text in texts:
        for word in text.lower().split():
            if word not in vocab:
                vocab[word] = len(vocab)

    if not vocab:
        return [[0.0] for _ in texts]

    # Build TF vectors
    vectors: list[list[float]] = []
    for text in texts:
        vec = [0.0] * len(vocab)
        words = text.lower().split()
        for word in words:
            if word in vocab:
                vec[vocab[word]] += 1.0
        # Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        vectors.append(vec)
    return vectors


def encode_texts(texts: list[str]) -> list[list[float]]:
    """Encode texts using best available backend."""
    try:
        return encode_texts_st(texts)
    except RuntimeError:
        return encode_texts_tfidf(texts)


def find_best_matches(
    promise_texts: list[str],
    act_titles: list[str],
    threshold: float = 0.3,
) -> list[dict[str, object]]:
    """Find best matching legislative act for each promise.

    Returns list of {promise_idx, act_idx, similarity} for matches above threshold.
    """
    if not promise_texts or not act_titles:
        return []

    all_texts = promise_texts + act_titles
    embeddings = encode_texts(all_texts)

    promise_embs = embeddings[: len(promise_texts)]
    act_embs = embeddings[len(promise_texts) :]

    matches: list[dict[str, object]] = []
    for p_idx, p_emb in enumerate(promise_embs):
        best_sim = 0.0
        best_act_idx = -1

        for a_idx, a_emb in enumerate(act_embs):
            sim = cosine_similarity(p_emb, a_emb)
            if sim > best_sim:
                best_sim = sim
                best_act_idx = a_idx

        if best_sim >= threshold and best_act_idx >= 0:
            matches.append({
                "promise_idx": p_idx,
                "act_idx": best_act_idx,
                "similarity": round(best_sim, 4),
            })

    return matches


# ---------------------------------------------------------------------------
# DB orchestration
# ---------------------------------------------------------------------------


async def match_promises_to_acts(
    session: AsyncSession,
    *,
    threshold: float = 0.3,
    limit: int | None = None,
) -> int:
    """Match unmatched promises against legislative act titles.

    Args:
        session: Async SQLAlchemy session.
        threshold: Minimum cosine similarity to consider a match.
        limit: Max promises to process (None = all).

    Returns:
        Number of promises matched.
    """
    # Load unmatched promises
    p_stmt = (
        select(Promise)
        .where(Promise.matched_act_id.is_(None))
        .order_by(Promise.created_at)
    )
    if limit is not None:
        p_stmt = p_stmt.limit(limit)

    p_result = await session.execute(p_stmt)
    promises = p_result.scalars().all()

    if not promises:
        logger.info("No unmatched promises found")
        return 0

    # Load all legislative acts
    a_result = await session.execute(select(LegislativeAct))
    acts = a_result.scalars().all()

    if not acts:
        logger.info("No legislative acts to match against")
        return 0

    logger.info(
        "Matching %d promises against %d legislative acts",
        len(promises),
        len(acts),
    )

    promise_texts = [p.sentence for p in promises]
    act_titles = [a.title for a in acts]

    matches = find_best_matches(promise_texts, act_titles, threshold=threshold)

    matched_count = 0
    for m in matches:
        p_idx = int(str(m["promise_idx"]))
        a_idx = int(str(m["act_idx"]))
        sim = float(str(m["similarity"]))

        promise = promises[p_idx]
        act = acts[a_idx]

        promise.matched_act_id = act.id
        promise.match_similarity = sim  # type: ignore[assignment]
        matched_count += 1

    await session.flush()
    logger.info("Matched %d/%d promises to legislative acts", matched_count, len(promises))
    return matched_count


# ---------------------------------------------------------------------------
# Legacy API compatibility
# ---------------------------------------------------------------------------


async def match_promise_to_votes(
    promise_embedding: list[float],
    threshold: float = 0.7,
) -> list[dict[str, object]]:
    """Find votes matching a promise via cosine similarity.

    Deprecated: Use match_promises_to_acts() for DB-integrated matching.
    Kept for API compatibility.
    """
    logger.warning("match_promise_to_votes is deprecated, use match_promises_to_acts")
    return []
