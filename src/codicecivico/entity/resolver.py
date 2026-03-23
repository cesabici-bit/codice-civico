"""Entity resolution: deduplicate politicians across data sources.

Strategy (conservative, ordered by confidence):
1. Exact match on tax_code_hash (confidence=1.0)
2. Exact match on full_name + birth_date (confidence=0.95)
3. Normalized name match (confidence=0.85)
4. Fuzzy match via pg_trgm similarity (confidence < 0.85, flagged for review)

Cross-source merge: when a Camera deputy matches a Senato senator,
we merge into a single Politician row with both URIs populated.
"""

import logging
import re
import unicodedata
from uuid import UUID

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.models import Politician

logger = logging.getLogger(__name__)

# Minimum pg_trgm similarity threshold for fuzzy matching
FUZZY_THRESHOLD = 0.6


def normalize_name(name: str) -> str:
    """Normalize a name for comparison.

    - Strip accents (è → e)
    - Lowercase
    - Collapse whitespace
    - Remove punctuation except hyphens and apostrophes
    """
    # NFKD decomposition strips accents
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = nfkd.encode("ASCII", "ignore").decode("ASCII")
    # Lowercase, collapse spaces
    ascii_name = re.sub(r"\s+", " ", ascii_name.lower().strip())
    # Remove punctuation except hyphen/apostrophe (common in Italian names)
    ascii_name = re.sub(r"[^a-z0-9 '\-]", "", ascii_name)
    return ascii_name


async def resolve_politician(
    session: AsyncSession,
    full_name: str,
    *,
    birth_date: str | None = None,
    tax_code_hash: str | None = None,
    camera_uri: str | None = None,
    senato_uri: str | None = None,
) -> tuple[UUID | None, float]:
    """Match a politician across Camera/Senato/Openpolis.

    Returns:
        (politician_id, confidence) or (None, 0.0) if no match.
    """
    # --- Strategy 1: Exact tax_code_hash ---
    if tax_code_hash:
        stmt = select(Politician).where(Politician.tax_code_hash == tax_code_hash)
        result = await session.execute(stmt)
        match = result.scalar_one_or_none()
        if match:
            logger.debug("Resolved %s via tax_code_hash → %s", full_name, match.id)
            return match.id, 1.0

    # --- Strategy 2: Exact full_name + birth_date ---
    if birth_date:
        stmt = select(Politician).where(
            and_(
                func.lower(Politician.full_name) == full_name.lower().strip(),
                Politician.birth_date == birth_date,
            )
        )
        result = await session.execute(stmt)
        match = result.scalar_one_or_none()
        if match:
            logger.debug("Resolved %s via name+birth_date → %s", full_name, match.id)
            return match.id, 0.95

    # --- Strategy 3: Normalized name match ---
    normalized = normalize_name(full_name)
    if normalized:
        # Check all politicians; normalize on the fly
        # For efficiency, first try exact lower match
        stmt = select(Politician).where(
            func.lower(func.replace(Politician.full_name, "  ", " "))
            == full_name.lower().strip()
        )
        result = await session.execute(stmt)
        match = result.scalar_one_or_none()
        if match:
            logger.debug("Resolved %s via normalized name → %s", full_name, match.id)
            return match.id, 0.85

    # --- Strategy 4: Fuzzy via pg_trgm similarity ---
    # This requires the pg_trgm extension to be enabled
    try:
        stmt = (
            select(
                Politician.id,
                func.similarity(Politician.full_name, full_name).label("sim"),
            )
            .where(
                text("similarity(full_name, :name) > :threshold").bindparams(
                    name=full_name, threshold=FUZZY_THRESHOLD,
                )
            )
            .order_by(text("sim DESC"))
            .limit(1)
        )
        result = await session.execute(stmt)
        row = result.one_or_none()
        if row:
            pid, sim = row[0], float(row[1])
            logger.debug(
                "Resolved %s via fuzzy match → %s (similarity=%.3f)",
                full_name, pid, sim,
            )
            return pid, round(sim * 0.8, 2)  # Scale down: fuzzy = less confident
    except Exception:
        # pg_trgm not available — skip fuzzy
        logger.warning("pg_trgm not available; skipping fuzzy match for %s", full_name)

    return None, 0.0


async def merge_cross_chamber(session: AsyncSession) -> int:
    """Merge Camera and Senato politician records that refer to the same person.

    A politician may appear in both chambers (e.g., elected to Camera in one
    legislature and Senato in another). We detect duplicates by:
    1. Exact name + birth_date match
    2. Merge: keep the Camera record, copy senato_uri from Senato record,
       reassign all Senato-linked entities, delete the Senato duplicate.

    Returns:
        Number of merges performed.
    """
    # Find Camera politicians with matching Senato politicians by name+birth
    stmt = (
        select(
            Politician.id.label("camera_id"),
            Politician.full_name,
        )
        .where(
            and_(
                Politician.camera_uri.isnot(None),
                Politician.senato_uri.is_(None),
                Politician.birth_date.isnot(None),
            )
        )
    )
    result = await session.execute(stmt)
    camera_politicians = result.all()

    merge_count = 0
    for camera_id, camera_name in camera_politicians:
        # Find matching senato-only record
        camera_pol_stmt = select(Politician).where(Politician.id == camera_id)
        camera_pol_result = await session.execute(camera_pol_stmt)
        camera_pol = camera_pol_result.scalar_one()

        senato_stmt = select(Politician).where(
            and_(
                Politician.senato_uri.isnot(None),
                Politician.camera_uri.is_(None),
                func.lower(Politician.full_name) == camera_name.lower(),
                Politician.birth_date == camera_pol.birth_date,
            )
        )
        senato_result = await session.execute(senato_stmt)
        senato_pol = senato_result.scalar_one_or_none()

        if senato_pol is None:
            continue

        logger.info(
            "Merging %s: camera=%s + senato=%s",
            camera_name, camera_pol.camera_uri, senato_pol.senato_uri,
        )

        # Copy senato_uri to the camera record
        camera_pol.senato_uri = senato_pol.senato_uri

        # Reassign all relationships from senato record to camera record
        await _reassign_relationships(session, senato_pol.id, camera_id)

        # Delete the duplicate senato-only record
        await session.delete(senato_pol)
        merge_count += 1

    if merge_count:
        await session.flush()
        logger.info("Merged %d cross-chamber duplicates.", merge_count)

    return merge_count


async def _reassign_relationships(
    session: AsyncSession, old_id: UUID, new_id: UUID,
) -> None:
    """Reassign all foreign-key references from old politician to new one."""
    from codicecivico.models import (
        AssetDeclaration,
        EntityLink,
        Promise,
        Speech,
        Vote,
    )

    for model in (Vote, Speech, Promise, AssetDeclaration, EntityLink):
        stmt = (
            select(model)
            .where(model.politician_id == old_id)  # type: ignore[attr-defined]
        )
        result = await session.execute(stmt)
        for obj in result.scalars():
            obj.politician_id = new_id  # type: ignore[attr-defined]

    await session.flush()
