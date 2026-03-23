"""Politicians API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.api.deps import get_db
from codicecivico.api.schemas import (
    PoliticianDetail,
    PoliticianSummary,
    PromiseResponse,
    VoteResponse,
)
from codicecivico.models import Politician, Promise, Vote

router = APIRouter(prefix="/politicians", tags=["politicians"])


@router.get("", response_model=list[PoliticianSummary])
async def list_politicians(
    party: str | None = None,
    chamber: str | None = None,
    region: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[PoliticianSummary]:
    """List politicians with optional filters."""
    stmt = select(Politician)
    if party:
        stmt = stmt.where(Politician.current_party == party)
    if chamber:
        stmt = stmt.where(Politician.current_chamber == chamber)
    if region:
        stmt = stmt.where(Politician.region == region)
    if q:
        stmt = stmt.where(Politician.full_name.ilike(f"%{q}%"))
    stmt = stmt.order_by(Politician.full_name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    return [PoliticianSummary.model_validate(p) for p in result.scalars().all()]


@router.get("/{politician_id}", response_model=PoliticianDetail)
async def get_politician(
    politician_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PoliticianDetail:
    """Get politician detail with coherence score."""
    result = await db.execute(select(Politician).where(Politician.id == politician_id))
    politician = result.scalar_one_or_none()
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    # Count votes and promises
    vote_count_result = await db.execute(
        select(func.count()).where(Vote.politician_id == politician_id)
    )
    promise_count_result = await db.execute(
        select(func.count()).where(Promise.politician_id == politician_id)
    )

    detail = PoliticianDetail.model_validate(politician)
    detail.vote_count = vote_count_result.scalar() or 0
    detail.promise_count = promise_count_result.scalar() or 0
    return detail


@router.get("/{politician_id}/votes", response_model=list[VoteResponse])
async def get_politician_votes(
    politician_id: uuid.UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[VoteResponse]:
    """Get vote history for a politician."""
    stmt = (
        select(Vote)
        .where(Vote.politician_id == politician_id)
        .order_by(Vote.session_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    return [VoteResponse.model_validate(v) for v in result.scalars().all()]


@router.get("/{politician_id}/promises", response_model=list[PromiseResponse])
async def get_politician_promises(
    politician_id: uuid.UUID,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[PromiseResponse]:
    """Get promises for a politician."""
    stmt = select(Promise).where(Promise.politician_id == politician_id)
    if status:
        stmt = stmt.where(Promise.status == status)
    stmt = stmt.order_by(Promise.created_at.desc())
    result = await db.execute(stmt)
    return [PromiseResponse.model_validate(p) for p in result.scalars().all()]
