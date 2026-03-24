"""FastAPI application with lifespan and route mounting."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from codicecivico import __version__
from codicecivico.api.ratelimit import limiter
from codicecivico.api.routes import (
    contracts,
    courts,
    dossier,
    laws,
    magistrates,
    politicians,
    search,
    system,
)
from codicecivico.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown."""
    # Configure logging
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

    # Start scheduler if enabled
    _scheduler = None
    if settings.scheduler_enabled:
        from codicecivico.ingest.scheduler import setup_scheduler

        _scheduler = setup_scheduler()
        _scheduler.start()
        logger.info("Scheduler started with %d jobs", len(_scheduler.get_jobs()))

    yield

    # Shutdown
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Codice Civico API",
        description=(
            "AI-powered civic accountability engine for Italian politics, "
            "judiciary, and public spending"
        ),
        version=__version__,
        lifespan=lifespan,
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        lambda req, exc: JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
        ),
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routes under /api/v1
    prefix = settings.api_prefix
    app.include_router(system.router, prefix=prefix)
    app.include_router(politicians.router, prefix=prefix)
    app.include_router(contracts.router, prefix=prefix)
    app.include_router(courts.router, prefix=prefix)
    app.include_router(laws.router, prefix=prefix)
    app.include_router(magistrates.router, prefix=prefix)
    app.include_router(dossier.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)

    return app


app = create_app()
