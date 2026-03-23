"""Dossier API routes — aggregated profile for any institutional figure."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from codicecivico.api.deps import get_db
from codicecivico.api.schemas import (
    AssetTimelineEntry,
    ContractSummary,
    InstitutionalDossier,
    LawSummary,
    MagistrateDossier,
    MagistrateStatResponse,
    PoliticianDossier,
    PromiseResponse,
    VoteResponse,
)
from codicecivico.models import (
    AssetDeclaration,
    Contract,
    EntityLink,
    InstitutionalFigure,
    LegislativeAct,
    Magistrate,
    Politician,
    Promise,
    Vote,
)

router = APIRouter(prefix="/dossier", tags=["dossier"])


@router.get(
    "/politician/{person_id}",
    response_model=PoliticianDossier,
)
async def politician_dossier(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PoliticianDossier:
    """Generate complete dossier for a politician.

    Aggregates: votes, promises, coherence score, attendance,
    asset timeline, linked contracts, sponsored legislation.
    """
    # Fetch politician
    result = await db.execute(
        select(Politician).where(Politician.id == person_id)
    )
    politician = result.scalar_one_or_none()
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    # Promises with status counts
    promise_result = await db.execute(
        select(Promise)
        .where(Promise.politician_id == person_id)
        .order_by(Promise.created_at.desc())
    )
    promises = promise_result.scalars().all()
    kept = sum(1 for p in promises if p.status == "kept")
    broken = sum(1 for p in promises if p.status == "broken")
    pending = sum(1 for p in promises if p.status == "pending")

    # Coherence score
    total_promises = len(promises)
    coherence = None
    if total_promises > 0:
        coherence = round((kept + pending) / total_promises * 100, 1)

    # Vote counts + attendance
    vote_count_result = await db.execute(
        select(func.count()).where(Vote.politician_id == person_id)
    )
    total_votes = vote_count_result.scalar() or 0

    absent_count_result = await db.execute(
        select(func.count())
        .where(Vote.politician_id == person_id)
        .where(Vote.vote_value == "assente")
    )
    absent_count = absent_count_result.scalar() or 0
    attendance = None
    if total_votes > 0:
        attendance = round(
            (total_votes - absent_count) / total_votes * 100, 1,
        )

    # Recent votes (last 20)
    recent_votes_result = await db.execute(
        select(Vote)
        .where(Vote.politician_id == person_id)
        .order_by(Vote.session_date.desc())
        .limit(20)
    )
    recent_votes = [
        VoteResponse.model_validate(v)
        for v in recent_votes_result.scalars().all()
    ]

    # Asset timeline
    assets_result = await db.execute(
        select(AssetDeclaration)
        .where(AssetDeclaration.politician_id == person_id)
        .order_by(AssetDeclaration.declaration_year)
    )
    asset_timeline = [
        AssetTimelineEntry(
            year=a.declaration_year,
            total_income=a.total_income,
            total_assets=a.total_assets,
        )
        for a in assets_result.scalars().all()
    ]

    # Linked contracts via entity_links
    links_result = await db.execute(
        select(EntityLink.entity_identifier)
        .where(EntityLink.politician_id == person_id)
    )
    linked_cfs = [r[0] for r in links_result.all() if r[0]]

    linked_contracts: list[ContractSummary] = []
    if linked_cfs:
        contracts_result = await db.execute(
            select(Contract)
            .where(Contract.supplier_cf.in_(linked_cfs))
            .order_by(Contract.risk_score.desc())
            .limit(50)
        )
        linked_contracts = [
            ContractSummary.model_validate(c)
            for c in contracts_result.scalars().all()
        ]

    # Sponsored legislative acts (via votes on acts they proposed)
    # Simplified: acts where politician has votes
    acts_result = await db.execute(
        select(LegislativeAct)
        .join(Vote, Vote.legislative_act_id == LegislativeAct.id)
        .where(Vote.politician_id == person_id)
        .distinct()
        .limit(20)
    )
    sponsored_acts = [
        LawSummary.model_validate(a)
        for a in acts_result.scalars().all()
    ]

    data_sources = ["dati.camera.it", "dati.senato.it"]
    if asset_timeline:
        data_sources.append("dichiarazioni patrimoniali")
    if linked_contracts:
        data_sources.append("dati.anticorruzione.it (ANAC)")

    return PoliticianDossier(
        person_id=politician.id,
        full_name=politician.full_name,
        current_party=politician.current_party,
        current_chamber=politician.current_chamber,
        region=politician.region,
        birth_date=politician.birth_date,
        photo_url=politician.photo_url,
        coherence_score=coherence,
        attendance_rate=attendance,
        total_votes=total_votes,
        total_promises=total_promises,
        promises_kept=kept,
        promises_broken=broken,
        promises_pending=pending,
        promises=[
            PromiseResponse.model_validate(p) for p in promises[:20]
        ],
        recent_votes=recent_votes,
        asset_timeline=asset_timeline,
        linked_contracts=linked_contracts,
        legislative_acts_sponsored=sponsored_acts,
        generated_at=datetime.utcnow(),
        data_sources=data_sources,
    )


@router.get(
    "/magistrate/{person_id}",
    response_model=MagistrateDossier,
)
async def magistrate_dossier(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MagistrateDossier:
    """Generate complete dossier for a magistrate.

    Aggregates: performance stats, comparison vs tribunal average,
    transfer history, disciplinary records.
    """
    result = await db.execute(
        select(Magistrate)
        .where(Magistrate.id == person_id)
        .options(
            selectinload(Magistrate.stats),
            selectinload(Magistrate.tribunal),
        )
    )
    magistrate = result.scalar_one_or_none()
    if not magistrate:
        raise HTTPException(
            status_code=404, detail="Magistrate not found",
        )

    tribunal_name = None
    tribunal_region = None
    if magistrate.tribunal:
        tribunal_name = magistrate.tribunal.name
        tribunal_region = magistrate.tribunal.region

    # Latest stats for headline numbers
    latest_stat = None
    stats_sorted = sorted(
        magistrate.stats, key=lambda s: s.period, reverse=True,
    )
    if stats_sorted:
        latest_stat = stats_sorted[0]

    avg_dur = latest_stat.avg_duration_days if latest_stat else None
    trib_avg = latest_stat.tribunal_avg_duration if latest_stat else None
    delta_pct = None
    if avg_dur and trib_avg and trib_avg > 0:
        delta_pct = round((avg_dur - trib_avg) / trib_avg * 100, 1)

    stats_timeline = [
        MagistrateStatResponse.model_validate(s)
        for s in stats_sorted
    ]

    data_sources = ["csm.it"]
    if magistrate.tribunal:
        data_sources.append("datiestatistiche.giustizia.it")

    return MagistrateDossier(
        person_id=magistrate.id,
        full_name=magistrate.full_name,
        role=magistrate.role,
        section=magistrate.section,
        tribunal_name=tribunal_name,
        tribunal_region=tribunal_region,
        birth_date=magistrate.birth_date,
        photo_url=magistrate.photo_url,
        in_office_since=magistrate.in_office_since,
        avg_duration_days=avg_dur,
        tribunal_avg_duration=trib_avg,
        performance_delta_pct=delta_pct,
        pending_cases=(
            latest_stat.pending_cases if latest_stat else None
        ),
        clearance_rate=(
            latest_stat.clearance_rate if latest_stat else None
        ),
        transfer_history=magistrate.transfer_history,
        disciplinary_records=magistrate.disciplinary_records,
        stats_timeline=stats_timeline,
        generated_at=datetime.utcnow(),
        data_sources=data_sources,
    )


@router.get(
    "/institutional/{person_id}",
    response_model=InstitutionalDossier,
)
async def institutional_dossier(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InstitutionalDossier:
    """Generate dossier for institutional figure (prefect, PA director)."""
    result = await db.execute(
        select(InstitutionalFigure)
        .where(InstitutionalFigure.id == person_id)
    )
    figure = result.scalar_one_or_none()
    if not figure:
        raise HTTPException(
            status_code=404, detail="Institutional figure not found",
        )

    # Find contracts linked to their institution
    linked_contracts: list[ContractSummary] = []
    if figure.institution:
        contracts_result = await db.execute(
            select(Contract)
            .where(Contract.buyer_name.ilike(f"%{figure.institution}%"))
            .order_by(Contract.risk_score.desc())
            .limit(50)
        )
        linked_contracts = [
            ContractSummary.model_validate(c)
            for c in contracts_result.scalars().all()
        ]

    return InstitutionalDossier(
        person_id=figure.id,
        full_name=figure.full_name,
        role_type=figure.role_type,
        institution=figure.institution,
        region=figure.region,
        in_office_since=figure.in_office_since,
        in_office_until=figure.in_office_until,
        previous_roles=figure.previous_roles,
        linked_contracts=linked_contracts,
        linked_contracts_count=len(linked_contracts),
        generated_at=datetime.utcnow(),
        data_sources=["dati.anticorruzione.it"],
    )
