"""Contracts API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from codicecivico.api.deps import get_db
from codicecivico.api.schemas import ContractDetail, ContractSummary
from codicecivico.models import Contract

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("", response_model=list[ContractSummary])
async def list_contracts(
    region: str | None = None,
    cpv: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    risk_min: float | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ContractSummary]:
    """List contracts with optional filters."""
    stmt = select(Contract)
    if region:
        stmt = stmt.where(Contract.buyer_region == region)
    if cpv:
        stmt = stmt.where(Contract.cpv_code.startswith(cpv))
    if amount_min is not None:
        stmt = stmt.where(Contract.amount_awarded >= amount_min)
    if amount_max is not None:
        stmt = stmt.where(Contract.amount_awarded <= amount_max)
    if risk_min is not None:
        stmt = stmt.where(Contract.risk_score >= risk_min)
    stmt = stmt.order_by(Contract.risk_score.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    return [ContractSummary.model_validate(c) for c in result.scalars().all()]


@router.get("/anomalies", response_model=list[ContractSummary])
async def top_anomalies(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[ContractSummary]:
    """Get top contracts by risk score."""
    stmt = (
        select(Contract)
        .where(Contract.risk_score > 0)
        .order_by(Contract.risk_score.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [ContractSummary.model_validate(c) for c in result.scalars().all()]


@router.get("/{contract_id}", response_model=ContractDetail)
async def get_contract(
    contract_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ContractDetail:
    """Get contract detail with anomaly flags."""
    stmt = (
        select(Contract)
        .where(Contract.id == contract_id)
        .options(selectinload(Contract.anomaly_flags))
    )
    result = await db.execute(stmt)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return ContractDetail.model_validate(contract)
