"""Openpolis REST API data ingestor."""

from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.ingest.base import BaseIngestor


class OpenpolisIngestor(BaseIngestor):
    """Enrich politician profiles from api3.openpolis.it."""

    source_name = "openpolis"

    async def ingest(self, session: AsyncSession) -> int:
        """Fetch and enrich politician data from Openpolis."""
        raise NotImplementedError("Openpolis ingestion not yet implemented (F2)")

    async def get_checkpoint(self, session: AsyncSession) -> str | None:
        """Get last sync timestamp."""
        return None
