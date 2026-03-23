"""Magistrates API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from codicecivico.api.deps import get_db
from codicecivico.api.schemas import MagistrateDetail, MagistrateSummary
from codicecivico.models import Magistrate

router = APIRouter(prefix="/magistrates", tags=["magistrates"])


@router.get("", response_model=list[MagistrateSummary])
async def list_magistrates(
    role: str | None = None,
    tribunal_id: uuid.UUID | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[MagistrateSummary]:
    """List magistrates with optional filters."""
    stmt = select(Magistrate)
    if role:
        stmt = stmt.where(Magistrate.role == role)
    if tribunal_id:
        stmt = stmt.where(Magistrate.tribunal_id == tribunal_id)
    if q:
        stmt = stmt.where(Magistrate.full_name.ilike(f"%{q}%"))
    stmt = (
        stmt.order_by(Magistrate.full_name)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    return [
        MagistrateSummary.model_validate(m)
        for m in result.scalars().all()
    ]


@router.get("/{magistrate_id}", response_model=MagistrateDetail)
async def get_magistrate(
    magistrate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MagistrateDetail:
    """Get magistrate detail with performance stats."""
    stmt = (
        select(Magistrate)
        .where(Magistrate.id == magistrate_id)
        .options(selectinload(Magistrate.stats))
    )
    result = await db.execute(stmt)
    magistrate = result.scalar_one_or_none()
    if not magistrate:
        raise HTTPException(
            status_code=404, detail="Magistrate not found",
        )
    return MagistrateDetail.model_validate(magistrate)
