"""CSM (Consiglio Superiore della Magistratura) data ingestor."""

from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.ingest.base import BaseIngestor


class CsmIngestor(BaseIngestor):
    """Ingest magistrate data from CSM.

    Sources:
    - csm.it: magistrate appointments, transfers, disciplinary records
    - Ministero Giustizia: court staffing data

    Data available:
    - Delibere di nomina e trasferimento
    - Procedimenti disciplinari (esiti pubblici)
    - Organico magistrati per sede
    """

    source_name = "csm"

    async def ingest(self, session: AsyncSession) -> int:
        """Scrape and store magistrate data from CSM."""
        raise NotImplementedError("CSM ingestion not yet implemented (F5)")

    async def get_checkpoint(self, session: AsyncSession) -> str | None:
        """Get last processed delibera date."""
        return None
