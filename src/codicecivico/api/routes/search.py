"""Global search route."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.api.deps import get_db
from codicecivico.api.schemas import SearchResult

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[SearchResult])
async def search(
    q: str = Query(..., min_length=2),
    type: str | None = Query(None, description="Filter: politician|contract|law|tribunal|all"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[SearchResult]:
    """Full-text search across all entities using pg_trgm."""
    # TODO: implement full-text search across politicians, contracts, laws, tribunals
    return []
