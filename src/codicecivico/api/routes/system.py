"""System routes: health, ingestion status, aggregate stats."""

import shutil

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico import __version__
from codicecivico.anomaly.rules import (
    LAST_MINUTE_DAYS,
    PRICE_SPIKE_MIN_SAMPLES,
    PRICE_SPIKE_Z_THRESHOLD,
    SHORT_DURATION_DAYS,
    SPLIT_GIANT_CLUSTER_SIZE,
    SPLIT_LOOKBACK_DAYS,
    SPLIT_MIN_SIMILAR,
    SPLIT_SUPPLIER_DIVERSITY_MAX,
    SPLIT_THRESHOLD_EUR,
)
from codicecivico.api.deps import get_db
from codicecivico.api.schemas import (
    AnomalyCalibrationResponse,
    AnomalyRuleCalibration,
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


@router.get("/stats/anomaly-calibration", response_model=AnomalyCalibrationResponse)
async def anomaly_calibration(
    session: AsyncSession = Depends(get_db),
) -> AnomalyCalibrationResponse:
    """Transparency endpoint: per-rule flag rates, severity distribution,
    and active thresholds.

    Exposes calibration state so reviewers can audit the detector without
    reading source code. Data updates after each `codicecivico train` run.
    """
    total_contracts = await session.scalar(select(func.count(Contract.id))) or 0

    flagged = await session.scalar(
        select(func.count(func.distinct(AnomalyFlag.contract_id))),
    ) or 0

    high_risk = await session.scalar(
        select(func.count(Contract.id)).where(Contract.risk_score >= 70),
    ) or 0
    medium_risk = await session.scalar(
        select(func.count(Contract.id)).where(
            Contract.risk_score >= 40, Contract.risk_score < 70,
        ),
    ) or 0

    # Per-rule breakdown with severity split
    per_rule_rows = (
        await session.execute(
            select(
                AnomalyFlag.flag_type,
                AnomalyFlag.severity,
                func.count(AnomalyFlag.id),
            ).group_by(AnomalyFlag.flag_type, AnomalyFlag.severity),
        )
    ).all()

    agg: dict[str, dict[str, int]] = {}
    for flag_type, severity, n in per_rule_rows:
        bucket = agg.setdefault(
            flag_type, {"total": 0, "high": 0, "medium": 0, "low": 0},
        )
        bucket["total"] += n
        if severity in ("high", "medium", "low"):
            bucket[severity] += n

    rules_payload = [
        AnomalyRuleCalibration(
            flag_type=ftype,
            total_flags=vals["total"],
            pct_of_contracts=(
                round(100.0 * vals["total"] / total_contracts, 3)
                if total_contracts else 0.0
            ),
            severity_high=vals["high"],
            severity_medium=vals["medium"],
            severity_low=vals["low"],
        )
        for ftype, vals in sorted(
            agg.items(), key=lambda kv: -kv[1]["total"],
        )
    ]

    thresholds: dict[str, object] = {
        "split_threshold_eur": SPLIT_THRESHOLD_EUR,
        "split_lookback_days": SPLIT_LOOKBACK_DAYS,
        "split_min_similar": SPLIT_MIN_SIMILAR,
        "split_supplier_diversity_max": SPLIT_SUPPLIER_DIVERSITY_MAX,
        "split_giant_cluster_size": SPLIT_GIANT_CLUSTER_SIZE,
        "price_spike_z_threshold": PRICE_SPIKE_Z_THRESHOLD,
        "price_spike_min_samples": PRICE_SPIKE_MIN_SAMPLES,
        "last_minute_days": LAST_MINUTE_DAYS,
        "short_duration_days": SHORT_DURATION_DAYS,
    }

    return AnomalyCalibrationResponse(
        total_contracts=total_contracts,
        flagged_contracts=flagged,
        flagged_pct=(
            round(100.0 * flagged / total_contracts, 2)
            if total_contracts else 0.0
        ),
        contracts_high_risk=high_risk,
        contracts_medium_risk=medium_risk,
        rules=rules_payload,
        thresholds=thresholds,
    )
