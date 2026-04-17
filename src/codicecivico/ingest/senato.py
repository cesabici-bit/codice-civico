"""Senato della Repubblica SPARQL data ingestor."""

import logging
import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.config import settings
from codicecivico.ingest.base import BaseIngestor, clean_text
from codicecivico.ingest.camera import parse_camera_person_id
from codicecivico.models import (
    LegislativeAct,
    Mandate,
    Person,
    PersonExternalId,
    Politician,
)

logger = logging.getLogger(__name__)

LEG_19_SENATO_START = date(2022, 10, 13)

# Person-id regex for Senato: `senatore/{N}` — bare numeric id, no prefix.
# Verified live 2026-04-18: senatore/22922 (Della Vedova, leg 19),
# senatore/63 (Amoruso, historical, linked to Camera via owl:sameAs).
_SENATO_PERSON_URI_RE = re.compile(r"^https?://dati\.senato\.it/senatore/(\d+)$")


def parse_senato_person_id(uri: str | None) -> str | None:
    """Extract the numeric person id from a Senato RDF URI.

    Returns the bare integer as a string (to be used as
    `PersonExternalId.external_id` in namespace ``senato``), or
    ``None`` when the URI does not match.
    """
    if not uri:
        return None
    match = _SENATO_PERSON_URI_RE.match(uri)
    if match is None:
        return None
    return match.group(1)


def extract_sameas_camera_link(
    row: dict[str, str],
) -> tuple[str, str] | None:
    """Map a ``owl:sameAs`` SPARQL row to a ``(senato_id, camera_id)`` pair.

    Expects keys ``sen`` and ``sameAs`` with URI string values.
    Returns ``None`` when either parser rejects the URI (historical
    ``dd`` prefix, malformed URI, non-Camera target, etc.), so upstream
    code can filter with a plain ``if link is None: continue``.
    """
    sen_uri = row.get("sen")
    same_uri = row.get("sameAs")
    if not sen_uri or not same_uri:
        return None
    senato_id = parse_senato_person_id(sen_uri)
    if senato_id is None:
        return None
    camera_parsed = parse_camera_person_id(same_uri)
    if camera_parsed is None:
        return None
    camera_id, _leg = camera_parsed
    return senato_id, camera_id

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

# F10 ST-10.4: owl:sameAs chain senator -> mandato/C_* -> Camera deputy URI.
# Scoped to senators with at least one leg-19 mandate (so they exist in our
# DB after ST-10.3). Each row yields (senator_id, camera_stable_id) after
# regex validation — modern `d` prefix only, historical `dd` dropped (EC-015).
QUERY_SAMEAS_CAMERA = """
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?sen ?mandato ?sameAs WHERE {
  ?sen a osr:Senatore .
  ?sen osr:mandato ?currentMandate .
  ?currentMandate osr:legislatura 19 .
  ?sen osr:mandato ?mandato .
  ?mandato owl:sameAs ?sameAs .
  FILTER(STRSTARTS(STR(?sameAs), "http://dati.camera.it/"))
} LIMIT {limit} OFFSET {offset}
"""

# F10 bitemporal: Senato mandates as temporal arcs Persona -> Senato.
# Verified live 2026-04-18. Note: a senator's ``osr:mandato`` set may
# include C_* mandates (retrospective Camera mandates) — we accept those
# as Senato-originated rows here (source provenance is Senato SPARQL),
# and a separate subtask (ST-10.4) will use owl:sameAs chains to merge
# them with Camera-side identities.
QUERY_MANDATI_SENATO = """
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT DISTINCT ?sen ?nome ?cognome ?mandato ?inizio ?fine ?tipoFine
WHERE {
  ?sen a osr:Senatore .
  ?sen foaf:firstName ?nome .
  ?sen foaf:lastName ?cognome .
  ?sen osr:mandato ?mandato .
  ?mandato osr:legislatura 19 .
  OPTIONAL { ?mandato osr:inizio ?inizio }
  OPTIONAL { ?mandato osr:fine ?fine }
  OPTIONAL { ?mandato osr:tipoFineMandato ?tipoFine }
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
            logger.info("Senato: %d senatori ingested (legacy politicians table).", n)

            n = await self._ingest_mandati_senato(session, max_pages=limit)
            total += n
            logger.info("Senato: %d mandati ingested (F10 bitemporal).", n)

            n = await self._link_camera_senato_sameas(session, max_pages=limit)
            logger.info("Senato: %d Camera links added via owl:sameAs.", n)

            n = await self._ingest_gruppi(session)
            logger.info("Senato: %d group memberships updated (legacy).", n)

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

    # ------------------------------------------------------------------
    # F10 bitemporal ingestion — persons + mandates (Senato side)
    # ------------------------------------------------------------------

    async def _upsert_person_senato(
        self,
        session: AsyncSession,
        *,
        stable_id: str,
        full_name: str,
        sen_source_url: str,
    ) -> Person:
        """Find-or-create Person + PersonExternalId(namespace='senato')."""
        stmt = (
            select(Person)
            .join(PersonExternalId, PersonExternalId.person_id == Person.id)
            .where(
                PersonExternalId.namespace == "senato",
                PersonExternalId.external_id == stable_id,
            )
        )
        result = await session.execute(stmt)
        person = result.scalar_one_or_none()
        if person is not None:
            return person

        person = Person(primary_full_name=full_name)
        session.add(person)
        await session.flush()
        ext = PersonExternalId(
            person_id=person.id,
            namespace="senato",
            external_id=stable_id,
            source_url=sen_source_url,
        )
        session.add(ext)
        await session.flush()
        return person

    async def _ingest_mandati_senato(
        self, session: AsyncSession, *, max_pages: int | None = None,
    ) -> int:
        """Ingest Senato mandates as temporal arcs Persona -> Senato.

        Chamber is tagged by mandate URI prefix: mandates starting with
        ``/mandato/S_`` go to chamber='senato'; ``/mandato/C_`` are Camera
        retrospective mandates surfaced by the Senato endpoint and map to
        chamber='camera' (later reconciled via owl:sameAs in ST-10.4).
        Rows without ``inizio`` are skipped (M5: valid_from NOT NULL).
        """
        endpoint = settings.senato_sparql_endpoint
        rows = self._sparql_paginated(
            endpoint, QUERY_MANDATI_SENATO, max_pages=max_pages,
        )

        count = 0
        skipped_no_start = 0
        skipped_bad_uri = 0
        for row in rows:
            sen_uri = row.get("sen", "")
            mandato_uri = row.get("mandato", "")
            if not sen_uri or not mandato_uri:
                continue

            stable_id = parse_senato_person_id(sen_uri)
            if stable_id is None:
                skipped_bad_uri += 1
                continue

            start_date = _parse_date_senato(row.get("inizio", ""))
            if start_date is None:
                skipped_no_start += 1
                logger.warning(
                    "Senato mandato %s skipped: inizio missing (M5).",
                    mandato_uri,
                )
                continue

            end_date = _parse_date_senato(row.get("fine", ""))
            tipo_fine = row.get("tipoFine") or None

            # Derive chamber + legislature from mandate URI:
            # http://dati.senato.it/mandato/{S|C}_{leg}_{id}_{k}
            chamber = "senato"
            leg = 19
            try:
                tail = mandato_uri.rsplit("/", 1)[1]  # S_19_29040_1
                parts = tail.split("_")
                if parts and parts[0].upper() == "C":
                    chamber = "camera"
                if len(parts) > 1 and parts[1].isdigit():
                    leg = int(parts[1])
            except (IndexError, ValueError):
                # Fallback: treat as Senato leg 19
                pass

            nome = row.get("nome", "")
            cognome = row.get("cognome", "")
            full_name = f"{cognome} {nome}".strip()

            person = await self._upsert_person_senato(
                session,
                stable_id=stable_id,
                full_name=full_name,
                sen_source_url=sen_uri,
            )

            # Dedup by unique (person_id, chamber, legislature, start_date)
            stmt = select(Mandate).where(
                Mandate.person_id == person.id,
                Mandate.chamber == chamber,
                Mandate.legislature == leg,
                Mandate.start_date == start_date,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                if end_date is not None and existing.end_date != end_date:
                    existing.end_date = end_date
                if tipo_fine and existing.motivo_termine != tipo_fine:
                    existing.motivo_termine = tipo_fine
                continue

            mandate = Mandate(
                person_id=person.id,
                chamber=chamber,
                legislature=leg,
                start_date=start_date,
                end_date=end_date,
                motivo_termine=tipo_fine,
                source_url=mandato_uri,
            )
            session.add(mandate)
            count += 1

        await session.flush()
        logger.info(
            "Senato mandati: %d inserted, skipped no-start=%d, bad-uri=%d.",
            count, skipped_no_start, skipped_bad_uri,
        )
        return count

    async def _link_camera_senato_sameas(
        self, session: AsyncSession, *, max_pages: int | None = None,
    ) -> int:
        """Attach ``camera:{stable_id}`` external_id to existing Senato Persons.

        Uses the ``owl:sameAs`` chain exposed by the Senato endpoint.
        Behavior:
        - For each (senato_id, camera_id) pair extracted from the query,
          locate the existing Person by ``senato:{senato_id}``.
        - If that Person already has ``camera:{camera_id}``, skip.
        - If a DIFFERENT Person (from prior Camera ingestion) already claims
          ``camera:{camera_id}``, do NOT merge — log a conflict. Merging
          two entities is out of scope for ST-10.4 (zero-defect policy).
        - Otherwise attach the new external_id to the Senato Person with
          ``source_url`` = sameAs Camera URI (M5 satisfied).
        """
        endpoint = settings.senato_sparql_endpoint
        rows = self._sparql_paginated(
            endpoint, QUERY_SAMEAS_CAMERA, max_pages=max_pages,
        )

        linked = 0
        skipped_historical = 0
        conflicts = 0
        missing_senato_person = 0

        for row in rows:
            link = extract_sameas_camera_link(row)
            if link is None:
                skipped_historical += 1
                continue
            senato_id, camera_id = link
            same_uri = row.get("sameAs", "")

            # Find the Senato-side Person (must exist from ST-10.3 ingest).
            stmt = (
                select(Person)
                .join(PersonExternalId, PersonExternalId.person_id == Person.id)
                .where(
                    PersonExternalId.namespace == "senato",
                    PersonExternalId.external_id == senato_id,
                )
            )
            senato_person = (await session.execute(stmt)).scalar_one_or_none()
            if senato_person is None:
                missing_senato_person += 1
                continue

            # Check if camera:{camera_id} is already attached to this or
            # another person.
            stmt2 = select(PersonExternalId).where(
                PersonExternalId.namespace == "camera",
                PersonExternalId.external_id == camera_id,
            )
            existing_link = (await session.execute(stmt2)).scalar_one_or_none()
            if existing_link is not None:
                if existing_link.person_id == senato_person.id:
                    continue  # already linked
                conflicts += 1
                logger.warning(
                    "owl:sameAs conflict: camera:%s owned by %s but Senato "
                    "claims it for %s (skipping merge, manual review needed)",
                    camera_id, existing_link.person_id, senato_person.id,
                )
                continue

            # Safe to attach.
            ext = PersonExternalId(
                person_id=senato_person.id,
                namespace="camera",
                external_id=camera_id,
                source_url=same_uri,
            )
            session.add(ext)
            linked += 1

        await session.flush()
        logger.info(
            "owl:sameAs links: %d added, %d historical skipped, "
            "%d conflicts, %d senators not found in DB.",
            linked, skipped_historical, conflicts, missing_senato_person,
        )
        return linked

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
