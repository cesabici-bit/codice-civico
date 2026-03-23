"""Laws API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.api.deps import get_db
from codicecivico.api.schemas import LawDetail, LawSummary
from codicecivico.models import LegislativeAct

router = APIRouter(prefix="/laws", tags=["laws"])


@router.get("", response_model=list[LawSummary])
async def list_laws(
    chamber: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[LawSummary]:
    """List legislative acts."""
    stmt = select(LegislativeAct)
    if chamber:
        stmt = stmt.where(LegislativeAct.chamber == chamber)
    if status:
        stmt = stmt.where(LegislativeAct.status == status)
    stmt = (
        stmt.order_by(LegislativeAct.presentation_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    return [LawSummary.model_validate(a) for a in result.scalars().all()]


@router.get("/{law_id}", response_model=LawDetail)
async def get_law(
    law_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> LawDetail:
    """Get legislative act detail with plain-language translation."""
    result = await db.execute(select(LegislativeAct).where(LegislativeAct.id == law_id))
    law = result.scalar_one_or_none()
    if not law:
        raise HTTPException(status_code=404, detail="Legislative act not found")
    return LawDetail.model_validate(law)
