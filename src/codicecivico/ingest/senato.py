"""Senato della Repubblica SPARQL data ingestor."""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.config import settings
from codicecivico.ingest.base import BaseIngestor, clean_text
from codicecivico.models import LegislativeAct, Politician

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SPARQL query templates (verified against dati.senato.it 2026-03-23)
# ---------------------------------------------------------------------------

QUERY_SENATORI = """
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT DISTINCT ?sen ?nome ?cognome ?dataNascita ?foto ?tipoMandato
WHERE {
  ?sen a osr:Senatore .
  ?sen foaf:firstName ?nome .
  ?sen foaf:lastName ?cognome .
  ?sen osr:mandato ?mandato .
  ?mandato osr:legislatura 19 .
  OPTIONAL { ?sen osr:dataNascita ?dataNascita }
  OPTIONAL { ?sen foaf:depiction ?foto }
  OPTIONAL { ?mandato osr:tipoMandato ?tipoMandato }
}
"""

QUERY_GRUPPI_SENATO = """
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT ?sen ?gruppo
WHERE {
  ?sen a osr:Senatore .
  ?sen osr:mandato ?mandato .
  ?mandato osr:legislatura 19 .
  ?sen ocd:aderisce ?adesione .
  ?adesione ocd:gruppoParlamentare ?gp .
  ?gp dc:title ?gruppo .
  OPTIONAL { ?adesione ocd:dataAdesione ?dataAdesione }
}
ORDER BY ?sen DESC(?dataAdesione)
"""

QUERY_VOTAZIONI_SENATO = """
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?votazione ?oggetto ?esito ?favorevoli ?contrari ?astenuti ?dataSeduta
WHERE {
  ?votazione a osr:Votazione .
  ?votazione osr:seduta ?seduta .
  ?votazione rdfs:label ?oggetto .
  OPTIONAL { ?votazione osr:favorevoli ?favorevoli }
  OPTIONAL { ?votazione osr:contrari ?contrari }
  OPTIONAL { ?votazione osr:astenuti ?astenuti }
  OPTIONAL { ?votazione osr:esito ?esito }
  ?seduta osr:dataSeduta ?dataSeduta .
  ?seduta osr:legislatura 19
} ORDER BY DESC(?dataSeduta) LIMIT {limit} OFFSET {offset}
"""

QUERY_DDL = """
PREFIX osr: <http://dati.senato.it/osr/>
SELECT ?ddl ?titolo ?dataPresentazione ?stato ?natura
WHERE {
  ?ddl a osr:Ddl .
  ?ddl osr:titolo ?titolo .
  ?ddl osr:legislatura 19 .
  OPTIONAL { ?ddl osr:dataPresentazione ?dataPresentazione }
  OPTIONAL { ?ddl osr:statoDdl ?stato }
  OPTIONAL { ?ddl osr:natura ?natura }
} LIMIT {limit} OFFSET {offset}
"""


def _parse_date_senato(raw: str) -> date | None:
    """Parse date from Senato SPARQL (various formats)."""
    if not raw:
        return None
    raw = raw.strip()
    # Senato uses ISO format typically
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y"):
        try:
            if fmt == "%Y-%m-%d" and "-" in raw:
                return date.fromisoformat(raw[:10])
            if fmt == "%Y%m%d" and len(raw) >= 8 and raw[:8].isdigit():
                return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
            if fmt == "%d/%m/%Y" and "/" in raw:
                parts = raw.split("/")
                return date(int(parts[2][:4]), int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            continue
    return None


class SenatoIngestor(BaseIngestor):
    """Ingest politicians, votes, and acts from dati.senato.it SPARQL."""

    source_name = "senato"

    async def ingest(self, session: AsyncSession, *, limit: int | None = None) -> int:
        """Fetch and store Senato data.

        Args:
            session: Async DB session.
            limit: If set, limits max pages for each entity type (for testing).

        Returns:
            Total number of records processed.
        """
        log_entry = await self.log_ingestion_start(session)
        total = 0
        errors: dict[str, str] = {}

        try:
            n = await self._ingest_senatori(session)
            total += n
            logger.info("Senato: %d senatori ingested.", n)

            n = await self._ingest_gruppi(session)
            logger.info("Senato: %d group memberships updated.", n)

            n = await self._ingest_votazioni(session, max_pages=limit)
            total += n
            logger.info("Senato: %d votazioni parsed.", n)

            n = await self._ingest_ddl(session, max_pages=limit)
            total += n
            logger.info("Senato: %d DDL ingested.", n)

            await self.log_ingestion_end(
                session, log_entry, records=total, checkpoint=str(date.today()),
            )
            await session.commit()

        except Exception as exc:
            errors["exception"] = str(exc)
            await self.log_ingestion_end(
                session, log_entry, records=total, status="failed", errors=errors,
            )
            await session.commit()
            raise

        return total

    async def get_checkpoint(self, session: AsyncSession) -> str | None:
        """Get last ingested date."""
        return await self.get_last_checkpoint(session)

    # ------------------------------------------------------------------
    # Private ingestion methods
    # ------------------------------------------------------------------

    async def _ingest_senatori(self, session: AsyncSession) -> int:
        """Ingest senators from SPARQL."""
        endpoint = settings.senato_sparql_endpoint
        rows = self._sparql_query(endpoint, QUERY_SENATORI)

        count = 0
        for row in rows:
            sen_uri = row.get("sen", "")
            if not sen_uri:
                continue

            # Upsert by senato_uri
            stmt = select(Politician).where(Politician.senato_uri == sen_uri)
            result = await session.execute(stmt)
            politician = result.scalar_one_or_none()

            nome = row.get("nome", "")
            cognome = row.get("cognome", "")
            full_name = f"{cognome} {nome}".strip()
            birth = _parse_date_senato(row.get("dataNascita", ""))

            if politician is None:
                politician = Politician(
                    full_name=full_name,
                    senato_uri=sen_uri,
                    current_chamber="senato",
                    birth_date=birth,
                    photo_url=row.get("foto"),
                )
                session.add(politician)
                count += 1
            else:
                politician.full_name = full_name
                politician.birth_date = birth or politician.birth_date
                politician.photo_url = row.get("foto") or politician.photo_url

        await session.flush()
        return count

    async def _ingest_gruppi(self, session: AsyncSession) -> int:
        """Update current party for each senator based on latest group."""
        endpoint = settings.senato_sparql_endpoint
        rows = self._sparql_query(endpoint, QUERY_GRUPPI_SENATO)

        seen: set[str] = set()
        count = 0
        for row in rows:
            sen_uri = row.get("sen", "")
            if sen_uri in seen or not sen_uri:
                continue
            seen.add(sen_uri)

            gruppo = row.get("gruppo", "")
            if not gruppo:
                continue

            stmt = select(Politician).where(Politician.senato_uri == sen_uri)
            result = await session.execute(stmt)
            politician = result.scalar_one_or_none()
            if politician and politician.current_party != gruppo:
                politician.current_party = gruppo
                count += 1

        await session.flush()
        return count

    async def _ingest_votazioni(
        self, session: AsyncSession, *, max_pages: int | None = None,
    ) -> int:
        """Ingest aggregate votazioni from Senato."""
        endpoint = settings.senato_sparql_endpoint
        rows = self._sparql_paginated(
            endpoint, QUERY_VOTAZIONI_SENATO, max_pages=max_pages,
        )

        # Aggregate votazioni — same as Camera, we parse and count.
        # Individual vote linking requires a separate phase.
        count = len(rows)
        logger.info("Senato: parsed %d votazioni (aggregate metadata).", count)
        return count

    async def _ingest_ddl(
        self, session: AsyncSession, *, max_pages: int | None = None,
    ) -> int:
        """Ingest DDL (disegni di legge) as LegislativeAct."""
        endpoint = settings.senato_sparql_endpoint
        rows = self._sparql_paginated(
            endpoint, QUERY_DDL, max_pages=max_pages,
        )

        count = 0
        for row in rows:
            ddl_uri = row.get("ddl", "")
            if not ddl_uri:
                continue

            stmt = select(LegislativeAct).where(LegislativeAct.source_uri == ddl_uri)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                continue

            titolo = clean_text(row.get("titolo"))
            act = LegislativeAct(
                title=titolo[:2000] if titolo else "Senza titolo",
                act_type=row.get("natura", "DDL"),
                chamber="senato",
                status=row.get("stato"),
                presentation_date=_parse_date_senato(row.get("dataPresentazione", "")),
                source_uri=ddl_uri,
            )
            session.add(act)
            count += 1

        await session.flush()
        return count
