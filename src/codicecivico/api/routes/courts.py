"""Courts API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from codicecivico.api.deps import get_db
from codicecivico.api.schemas import TribunalDetail, TribunalSummary
from codicecivico.models import Tribunal

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
