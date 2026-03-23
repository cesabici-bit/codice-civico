"""NLP pipeline orchestration — DB integration for promise extraction.

Processes Speech rows where nlp_processed=False, extracts promises,
stores Promise ORM objects, and marks speeches as processed.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.models import Promise, Speech
from codicecivico.nlp.promise import extract_promises

logger = logging.getLogger(__name__)


async def run_promise_pipeline(
    session: AsyncSession,
    *,
    batch_size: int = 100,
    limit: int | None = None,
) -> int:
    """Process unprocessed speeches and extract promises.

    Args:
        session: Async SQLAlchemy session.
        batch_size: Number of speeches to process per batch.
        limit: Max speeches to process (None = all).

    Returns:
        Total number of promises created.
    """
    stmt = (
        select(Speech)
        .where(Speech.nlp_processed.is_(False))
        .order_by(Speech.created_at)
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    speeches = result.scalars().all()

    if not speeches:
        logger.info("No unprocessed speeches found")
        return 0

    logger.info("Processing %d unprocessed speeches", len(speeches))
    total_promises = 0

    for i, speech in enumerate(speeches):
        if not speech.full_text or not speech.full_text.strip():
            speech.nlp_processed = True
            continue

        try:
            raw_promises = await extract_promises(speech.full_text)
        except Exception:
            logger.exception("Failed to process speech %s", speech.id)
            continue

        for p in raw_promises:
            promise = Promise(
                politician_id=speech.politician_id,
                speech_id=speech.id,
                sentence=str(p["sentence"]),
                topic=str(p["topic"]) if p.get("topic") else None,
                specificity_score=Decimal(str(p["specificity_score"])),
                confidence=Decimal(str(p["confidence"])),
                status="pending",
            )
            session.add(promise)
            total_promises += 1

        speech.nlp_processed = True

        # Flush periodically
        if (i + 1) % batch_size == 0:
            await session.flush()
            logger.info("Processed %d/%d speeches", i + 1, len(speeches))

    await session.flush()
    logger.info(
        "Promise pipeline complete: %d promises from %d speeches",
        total_promises,
        len(speeches),
    )
    return total_promises
