"""Asset declaration PDF scraper."""

from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.ingest.base import BaseIngestor


class AssetIngestor(BaseIngestor):
    """Scrape and parse politician asset declaration PDFs."""

    source_name = "assets"

    async def ingest(self, session: AsyncSession) -> int:
        """Download and parse asset declaration PDFs."""
        raise NotImplementedError("Asset ingestion not yet implemented (F7)")

    async def get_checkpoint(self, session: AsyncSession) -> str | None:
        """Get last processed year."""
        return None
