"""Ministero della Giustizia statistics scraper."""

from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.ingest.base import BaseIngestor


class GiustiziaIngestor(BaseIngestor):
    """Scrape court statistics from datiestatistiche.giustizia.it."""

    source_name = "giustizia"

    async def ingest(self, session: AsyncSession) -> int:
        """Scrape and store justice system statistics."""
        raise NotImplementedError("Giustizia ingestion not yet implemented (F5)")

    async def get_checkpoint(self, session: AsyncSession) -> str | None:
        """Get last scraped period."""
        return None
