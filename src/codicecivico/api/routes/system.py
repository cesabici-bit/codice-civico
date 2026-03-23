"""System routes: health, ingestion status."""

from fastapi import APIRouter

from codicecivico import __version__
from codicecivico.api.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Healthcheck endpoint."""
    return HealthResponse(status="ok", version=__version__)
