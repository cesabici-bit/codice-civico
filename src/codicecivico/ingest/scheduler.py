"""APScheduler configuration for periodic data ingestion."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from codicecivico.db import async_session

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600},
)


async def _ingest_camera() -> None:
    """Daily Camera dei Deputati ingestion."""
    from codicecivico.ingest.camera import CameraIngestor

    async with async_session() as session:
        ingestor = CameraIngestor()
        count = await ingestor.ingest(session)
        await session.commit()
        logger.info("Camera ingest completed: %d records", count)


async def _ingest_senato() -> None:
    """Daily Senato della Repubblica ingestion."""
    from codicecivico.ingest.senato import SenatoIngestor

    async with async_session() as session:
        ingestor = SenatoIngestor()
        count = await ingestor.ingest(session)
        await session.commit()
        logger.info("Senato ingest completed: %d records", count)


async def _entity_resolve() -> None:
    """Daily entity resolution (cross-chamber merge)."""
    from codicecivico.entity.resolver import merge_cross_chamber

    async with async_session() as session:
        count = await merge_cross_chamber(session)
        await session.commit()
        logger.info("Entity resolution: %d merges", count)


async def _run_nlp_pipeline() -> None:
    """Daily NLP promise extraction on unprocessed speeches."""
    from codicecivico.nlp.pipeline import run_promise_pipeline

    async with async_session() as session:
        count = await run_promise_pipeline(session)
        await session.commit()
        logger.info("NLP pipeline: %d promises extracted", count)


async def _ingest_anac() -> None:
    """Monthly ANAC procurement ingestion."""
    from codicecivico.ingest.anac import AnacIngestor

    async with async_session() as session:
        ingestor = AnacIngestor()
        count = await ingestor.ingest(session)
        await session.commit()
        logger.info("ANAC ingest completed: %d records", count)


async def _ingest_giustizia() -> None:
    """Monthly Min. Giustizia statistics ingestion."""
    from codicecivico.ingest.giustizia import GiustiziaIngestor

    async with async_session() as session:
        ingestor = GiustiziaIngestor()
        count = await ingestor.ingest(session)
        await session.commit()
        logger.info("Giustizia ingest completed: %d records", count)


def setup_scheduler() -> AsyncIOScheduler:
    """Configure and return the ingestion scheduler.

    Schedule (all times UTC):
    - Camera:         daily   02:00
    - Senato:         daily   02:30
    - Entity resolve: daily   03:00
    - NLP pipeline:   daily   03:30
    - ANAC:           monthly 1st at 04:00
    - Giustizia:      monthly 1st at 04:30
    """
    scheduler.add_job(
        _ingest_camera,
        CronTrigger(hour=2, minute=0),
        id="ingest_camera",
        replace_existing=True,
    )
    scheduler.add_job(
        _ingest_senato,
        CronTrigger(hour=2, minute=30),
        id="ingest_senato",
        replace_existing=True,
    )
    scheduler.add_job(
        _entity_resolve,
        CronTrigger(hour=3, minute=0),
        id="entity_resolve",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_nlp_pipeline,
        CronTrigger(hour=3, minute=30),
        id="nlp_pipeline",
        replace_existing=True,
    )
    scheduler.add_job(
        _ingest_anac,
        CronTrigger(day=1, hour=4, minute=0),
        id="ingest_anac",
        replace_existing=True,
    )
    scheduler.add_job(
        _ingest_giustizia,
        CronTrigger(day=1, hour=4, minute=30),
        id="ingest_giustizia",
        replace_existing=True,
    )

    return scheduler
