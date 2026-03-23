"""Courts API routes."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from codicecivico.api.deps import get_db
from codicecivico.api.schemas import (
    NationalYearStats,
    TribunalDetail,
    TribunalRanking,
    TribunalSummary,
)
from codicecivico.models import CourtStat, Tribunal

router = APIRouter(prefix="/courts", tags=["courts"])


@router.get("", response_model=list[TribunalSummary])
async def list_courts(
    region: str | None = None,
    type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[TribunalSummary]:
    """List all tribunals."""
    stmt = select(Tribunal)
    if region:
        stmt = stmt.where(Tribunal.region == region)
    if type:
        stmt = stmt.where(Tribunal.type == type)
    stmt = stmt.order_by(Tribunal.name)
    result = await db.execute(stmt)
    return [TribunalSummary.model_validate(t) for t in result.scalars().all()]


@router.get("/stats/national", response_model=list[NationalYearStats])
async def national_stats(
    category: str | None = Query(
        None, description="Filter by case_category (civile, penale, lavoro)",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[NationalYearStats]:
    """Aggregated national statistics by year."""
    year_expr = func.extract("year", CourtStat.period).label("year")
    stmt = (
        select(
            year_expr,
            func.sum(CourtStat.new_cases).label("total_incoming"),
            func.sum(CourtStat.resolved_cases).label("total_resolved"),
            func.sum(CourtStat.pending_cases).label("total_pending"),
        )
        .group_by(year_expr)
        .order_by(year_expr)
    )
    if category:
        stmt = stmt.where(CourtStat.case_category == category)

    result = await db.execute(stmt)
    rows = result.all()

    stats: list[NationalYearStats] = []
    for row in rows:
        yr = int(row.year) if row.year else 0
        incoming = int(row.total_incoming or 0)
        resolved = int(row.total_resolved or 0)
        pending = int(row.total_pending or 0)
        cr = round(resolved / incoming, 4) if incoming > 0 else None
        dt = round((pending / resolved) * 365, 2) if resolved > 0 else None
        stats.append(NationalYearStats(
            year=yr,
            total_incoming=incoming,
            total_resolved=resolved,
            total_pending=pending,
            clearance_rate=cr,
            avg_disposition_time=dt,
        ))
    return stats


@router.get("/rankings", response_model=list[TribunalRanking])
async def court_rankings(
    metric: str = Query(
        "disposition_time",
        description="Metric to rank by: disposition_time, clearance_rate, pending_cases",
    ),
    year: int | None = Query(None, description="Year to rank (default: latest available)"),
    category: str | None = Query(None, description="Case category filter"),
    order: str = Query("asc", description="Sort order: asc or desc"),
    limit: int = Query(20, ge=1, le=200, description="Number of results"),
    db: AsyncSession = Depends(get_db),
) -> list[TribunalRanking]:
    """Rank tribunals by a performance metric."""
    # Map metric name to column
    metric_columns = {
        "disposition_time": CourtStat.avg_duration_days,
        "clearance_rate": CourtStat.clearance_rate,
        "pending_cases": CourtStat.pending_cases,
        "new_cases": CourtStat.new_cases,
        "resolved_cases": CourtStat.resolved_cases,
    }
    col = metric_columns.get(metric)
    if col is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric '{metric}'. Valid: {list(metric_columns.keys())}",
        )

    # Determine year
    if year is None:
        max_year_stmt = select(func.max(func.extract("year", CourtStat.period)))
        max_year_result = await db.execute(max_year_stmt)
        year_val = max_year_result.scalar_one_or_none()
        if year_val is None:
            return []
        year = int(year_val)

    # Build period filter (end of year)
    period_date = date(year, 12, 31)

    stmt = (
        select(Tribunal, col.label("metric_value"))
        .join(CourtStat, CourtStat.tribunal_id == Tribunal.id)
        .where(CourtStat.period == period_date)
        .where(col.isnot(None))
    )
    if category:
        stmt = stmt.where(CourtStat.case_category == category)

    if order == "desc":
        stmt = stmt.order_by(col.desc())
    else:
        stmt = stmt.order_by(col.asc())

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    return [
        TribunalRanking(
            name=row.Tribunal.name,
            region=row.Tribunal.region,
            province=row.Tribunal.province,
            lat=float(row.Tribunal.lat) if row.Tribunal.lat else None,
            lon=float(row.Tribunal.lon) if row.Tribunal.lon else None,
            metric_value=float(row.metric_value) if row.metric_value is not None else None,
            metric_name=metric,
            year=year,
        )
        for row in rows
    ]


@router.get("/{tribunal_id}", response_model=TribunalDetail)
async def get_tribunal(
    tribunal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TribunalDetail:
    """Get tribunal detail with stats time series."""
    stmt = (
        select(Tribunal)
        .where(Tribunal.id == tribunal_id)
        .options(selectinload(Tribunal.stats))
    )
    result = await db.execute(stmt)
    tribunal = result.scalar_one_or_none()
    if not tribunal:
        raise HTTPException(status_code=404, detail="Tribunal not found")
    return TribunalDetail.model_validate(tribunal)
