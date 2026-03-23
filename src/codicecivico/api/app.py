"""FastAPI application with lifespan and route mounting."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from codicecivico import __version__
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown."""
    # Startup: could initialize DB pool, scheduler, NLP models here
    yield
    # Shutdown: cleanup resources


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
