"""Laws API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.api.deps import get_db
from codicecivico.api.ratelimit import limiter
from codicecivico.api.schemas import LawDetail, LawSummary, TranslationResponse
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


@router.post("/{law_id}/translate", response_model=TranslationResponse)
@limiter.limit("10/minute")
async def translate_law_endpoint(
    request: Request,  # noqa: ARG001 — required by slowapi
    law_id: uuid.UUID,
    force: bool = Query(False, description="Re-translate even if already translated"),
    db: AsyncSession = Depends(get_db),
) -> TranslationResponse:
    """Translate a legislative act to plain Italian via local LLM.

    Returns cached translation if available (use force=true to re-translate).
    Returns 503 if Ollama is not available.
    """
    from codicecivico.nlp.translator import translate_law

    result = await db.execute(select(LegislativeAct).where(LegislativeAct.id == law_id))
    law = result.scalar_one_or_none()
    if not law:
        raise HTTPException(status_code=404, detail="Legislative act not found")

    # Return cached translation if available
    if law.plain_translation and not force:
        return TranslationResponse(
            law_id=law.id,
            title=law.title,
            translation=law.plain_translation,
            translated_at=law.translated_at,
            cached=True,
        )

    if not law.full_text:
        raise HTTPException(
            status_code=422,
            detail="Legislative act has no full text to translate",
        )

    translation = await translate_law(law.full_text)
    if translation is None:
        raise HTTPException(
            status_code=503,
            detail="Translation service unavailable (Ollama not running)",
        )

    # Persist translation
    law.plain_translation = translation
    law.translated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(law)

    return TranslationResponse(
        law_id=law.id,
        title=law.title,
        translation=translation,
        translated_at=law.translated_at,
        cached=False,
    )
