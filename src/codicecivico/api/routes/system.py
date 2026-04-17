"""System routes: health, ingestion status, aggregate stats."""

import shutil

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico import __version__
from codicecivico.api.deps import get_db
from codicecivico.api.schemas import (
    HealthDetailedResponse,
    HealthResponse,
    StatsOverview,
)
from codicecivico.config import settings
from codicecivico.models import (
    AnomalyFlag,
    Contract,
    CourtStat,
    LegislativeAct,
    Politician,
    Promise,
    Tribunal,
)

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Lightweight healthcheck (for Docker healthcheck probes)."""
    return HealthResponse(status="ok", version=__version__)


@router.get("/health/detailed", response_model=HealthDetailedResponse)
async def health_detailed(
    session: AsyncSession = Depends(get_db),
) -> HealthDetailedResponse:
    """Detailed health with DB, Ollama, disk, and scheduler status."""
    checks: dict[str, object] = {}

    # Database connectivity
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    # Ollama availability
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags")
            checks["ollama"] = "ok" if resp.status_code == 200 else "unavailable"
    except Exception:
        checks["ollama"] = "unavailable"

    # Disk space
    try:
        usage = shutil.disk_usage("/")
        checks["disk_free_gb"] = round(usage.free / (1024**3), 1)
        checks["disk_used_pct"] = round(usage.used / usage.total * 100, 1)
    except Exception:
        checks["disk_free_gb"] = None
        checks["disk_used_pct"] = None

    # Scheduler
    try:
        from codicecivico.ingest.scheduler import scheduler

        checks["scheduler"] = "running" if scheduler.running else "stopped"
        checks["scheduler_jobs"] = len(scheduler.get_jobs())
    except Exception:
        checks["scheduler"] = "not_initialized"
        checks["scheduler_jobs"] = 0

    overall = "ok" if checks.get("database") == "ok" else "degraded"

    return HealthDetailedResponse(
        status=overall,
        version=__version__,
        checks=checks,
    )


@router.get("/stats/overview", response_model=StatsOverview)
async def stats_overview(
    session: AsyncSession = Depends(get_db),
) -> StatsOverview:
    """Aggregate counts across all tables, used by the dashboard homepage."""
    # Single query per table — on 170k contracts this is <50ms with indexes.
    politicians = await session.scalar(select(func.count(Politician.id)))
    contracts = await session.scalar(select(func.count(Contract.id)))
    flags = await session.scalar(select(func.count(AnomalyFlag.id)))
    high_risk = await session.scalar(
        select(func.count(Contract.id)).where(Contract.risk_score >= 70),
    )
    tribunals = await session.scalar(select(func.count(Tribunal.id)))
    laws = await session.scalar(select(func.count(LegislativeAct.id)))
    promises = await session.scalar(select(func.count(Promise.id)))
    court_stats = await session.scalar(select(func.count(CourtStat.id)))

    return StatsOverview(
        politicians=politicians or 0,
        contracts=contracts or 0,
        anomaly_flags=flags or 0,
        high_risk_contracts=high_risk or 0,
        tribunals=tribunals or 0,
        laws=laws or 0,
        promises=promises or 0,
        court_stats=court_stats or 0,
    )
