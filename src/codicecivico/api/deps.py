"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.db import async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for request lifetime."""
    async with async_session() as session:
        yield session
