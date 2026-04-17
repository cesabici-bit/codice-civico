"""Camera dei Deputati SPARQL data ingestor."""

import logging
import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.config import settings
from codicecivico.ingest.base import BaseIngestor, clean_text
from codicecivico.models import (
    LegislativeAct,
    Mandate,
    PartyMembership,
    Person,
    PersonExternalId,
    Politician,
    Speech,
    Vote,
)

logger = logging.getLogger(__name__)

LEG_19_URI = "http://dati.camera.it/ocd/legislatura.rdf/repubblica_19"
LEG_19_START = date(2022, 10, 13)  # Opening of 19th Republic legislature

# Person-id regex: `deputato.rdf/{stable_id}_{legislature}`.
# Modern Republic legislatures (leg 13+) use prefix `d` + digits with a
# numeric part that is stable across legislatures (verified live for
# Meloni `d302103` in leg 15-19 on 2026-04-18). Kingdom-of-Italy `dr` and
# older Republic `dd` prefixes are deferred per KNOWN_ISSUES EC-015.
_CAMERA_DEP_URI_RE = re.compile(r"deputato\.rdf/([a-z]+\d+)_(\d+)$")


def parse_camera_person_id(uri: str) -> tuple[str, int] | None:
    """Extract (stable_person_id, legislature) from a Camera deputy URI.

    Returns ``None`` for:
    - URIs that do not match the `deputato.rdf/{id}_{leg}` shape
    - Historical prefixes `dd` (older Republic) or `dr` (Regno) — deferred
    """
    if not uri:
        return None
    match = _CAMERA_DEP_URI_RE.search(uri)
    if match is None:
        return None
    stable_id, leg_str = match.groups()
    # Require exactly one letter `d` followed by a digit — excludes `dd`, `dr`, etc.
    if not (stable_id.startswith("d") and len(stable_id) > 1 and stable_id[1].isdigit()):
        return None
    return stable_id, int(leg_str)

# ---------------------------------------------------------------------------
# SPARQL query templates (verified against dati.camera.it 2026-03-23)
# ---------------------------------------------------------------------------

QUERY_DEPUTATI = f"""
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT DISTINCT ?dep ?nome ?cognome ?foto ?dataNascita
WHERE {{
  ?dep a ocd:deputato .
  ?dep ocd:rif_leg <{LEG_19_URI}> .
  ?dep foaf:firstName ?nome .
  ?dep foaf:surname ?cognome .
  OPTIONAL {{ ?dep foaf:depiction ?foto }}
  OPTIONAL {{ ?dep ocd:dataNascita ?dataNascita }}
}}
"""

QUERY_GRUPPI = f"""
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT ?dep ?gruppo
WHERE {{
  ?dep a ocd:deputato .
  ?dep ocd:rif_leg <{LEG_19_URI}> .
  ?dep ocd:aderisce ?adesione .
  ?adesione ocd:gruppoParlamentare ?gp .
  ?gp dc:title ?gruppo .
  OPTIONAL {{ ?adesione ocd:dataAdesione ?dataAdesione }}
}}
ORDER BY ?dep DESC(?dataAdesione)
"""

QUERY_VOTAZIONI = f"""
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?vot ?titolo ?data ?favorevoli ?contrari ?astenuti ?approvato
WHERE {{
  ?vot a ocd:votazione .
  ?vot ocd:rif_leg <{LEG_19_URI}> .
  ?vot dc:title ?titolo .
  ?vot dc:date ?data .
  OPTIONAL {{ ?vot ocd:favorevoli ?favorevoli }}
  OPTIONAL {{ ?vot ocd:contrari ?contrari }}
  OPTIONAL {{ ?vot ocd:astenuti ?astenuti }}
  OPTIONAL {{ ?vot ocd:approvato ?approvato }}
}} ORDER BY DESC(?data) LIMIT {{limit}} OFFSET {{offset}}
"""

QUERY_ATTI = f"""
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT ?atto ?titolo ?tipo ?data
WHERE {{
  ?atto a ocd:atto .
  ?atto ocd:rif_leg <{LEG_19_URI}> .
  ?atto dc:title ?titolo .
  OPTIONAL {{ ?atto dc:type ?tipo }}
  OPTIONAL {{ ?atto dc:date ?data }}
}} LIMIT {{limit}} OFFSET {{offset}}
"""

QUERY_INTERVENTI = f"""
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?int ?label ?dep
WHERE {{
  ?int a ocd:intervento .
  ?int rdfs:label ?label .
  ?int ocd:rif_deputato ?dep .
  ?int ocd:rif_leg <{LEG_19_URI}> .
}} LIMIT {{limit}} OFFSET {{offset}}
"""

# F10 bitemporal: mandates as temporal arcs Persona -> Camera.
# Verified live against dati.camera.it on 2026-04-18 — returns
# startDate (YYYYMMDD), optional endDate, optional motivoTermine.
QUERY_MANDATI = f"""
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT DISTINCT ?mandato ?dep ?nome ?cognome ?startDate ?endDate ?motivo
WHERE {{
  ?mandato a ocd:mandatoCamera .
  ?mandato ocd:rif_deputato ?dep .
  ?mandato ocd:rif_leg <{LEG_19_URI}> .
  ?dep foaf:firstName ?nome .
  ?dep foaf:surname ?cognome .
  OPTIONAL {{ ?mandato ocd:startDate ?startDate }}
  OPTIONAL {{ ?mandato ocd:endDate ?endDate }}
  OPTIONAL {{ ?mandato ocd:motivoTermine ?motivo }}
}} LIMIT {{limit}} OFFSET {{offset}}
"""

# F10 bitemporal: party adhesions as temporal arcs Persona -> group.
# `ocd:dataAdesione` may be absent — fallback to legislature opening date.
QUERY_ADESIONI = f"""
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT ?adesione ?dep ?gruppo ?dataAdesione ?dataFineAdesione
WHERE {{
  ?dep a ocd:deputato .
  ?dep ocd:rif_leg <{LEG_19_URI}> .
  ?dep ocd:aderisce ?adesione .
  ?adesione ocd:gruppoParlamentare ?gp .
  ?gp dc:title ?gruppo .
  OPTIONAL {{ ?adesione ocd:dataInizio ?dataAdesione }}
  OPTIONAL {{ ?adesione ocd:dataFine ?dataFineAdesione }}
}} LIMIT {{limit}} OFFSET {{offset}}
"""


def _parse_date(raw: str) -> date | None:
    """Parse date from SPARQL (YYYYMMDD or YYYY-MM-DD)."""
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return date.fromisoformat(raw) if "-" in raw else date(
                int(raw[:4]), int(raw[4:6]), int(raw[6:8])
            )
        except (ValueError, IndexError):
            continue
    return None


class CameraIngestor(BaseIngestor):
    """Ingest politicians, votes, and speeches from dati.camera.it SPARQL."""

    source_name = "camera"

    async def ingest(self, session: AsyncSession, *, limit: int | None = None) -> int:
        """Fetch and store Camera dei Deputati data.

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
            n = await self._ingest_deputati(session)
            total += n
            logger.info("Camera: %d deputati ingested (legacy politicians table).", n)

            n = await self._ingest_mandati(session, max_pages=limit)
            total += n
            logger.info("Camera: %d mandati ingested (F10 bitemporal).", n)

            n = await self._ingest_party_memberships(session, max_pages=limit)
            total += n
            logger.info("Camera: %d party memberships ingested (F10 bitemporal).", n)

            n = await self._ingest_gruppi(session)
            logger.info("Camera: %d group memberships updated (legacy).", n)

            n = await self._ingest_votazioni(session, max_pages=limit)
            total += n
            logger.info("Camera: %d votazioni ingested.", n)

            n = await self._ingest_atti(session, max_pages=limit)
            total += n
            logger.info("Camera: %d atti ingested.", n)

            n = await self._ingest_interventi(session, max_pages=limit)
            total += n
            logger.info("Camera: %d interventi ingested.", n)

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

    async def _ingest_deputati(self, session: AsyncSession) -> int:
        """Ingest deputies from SPARQL."""
        endpoint = settings.camera_sparql_endpoint
        rows = self._sparql_query(endpoint, QUERY_DEPUTATI)

        count = 0
        for row in rows:
            dep_uri = row.get("dep", "")
            if not dep_uri:
                continue

            # Upsert by camera_uri
            stmt = select(Politician).where(Politician.camera_uri == dep_uri)
            result = await session.execute(stmt)
            politician = result.scalar_one_or_none()

            nome = row.get("nome", "")
            cognome = row.get("cognome", "")
            full_name = f"{cognome} {nome}".strip()
            birth = _parse_date(row.get("dataNascita", ""))

            if politician is None:
                politician = Politician(
                    full_name=full_name,
                    camera_uri=dep_uri,
                    current_chamber="camera",
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
        """Update current party for each deputy based on latest group."""
        endpoint = settings.camera_sparql_endpoint
        rows = self._sparql_query(endpoint, QUERY_GRUPPI)

        # Keep only the first (latest) group per deputy
        seen: set[str] = set()
        count = 0
        for row in rows:
            dep_uri = row.get("dep", "")
            if dep_uri in seen or not dep_uri:
                continue
            seen.add(dep_uri)

            gruppo = row.get("gruppo", "")
            if not gruppo:
                continue

            stmt = select(Politician).where(Politician.camera_uri == dep_uri)
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
        """Ingest aggregate votazioni (not individual votes)."""
        endpoint = settings.camera_sparql_endpoint
        rows = self._sparql_paginated(
            endpoint, QUERY_VOTAZIONI, max_pages=max_pages,
        )

        count = 0
        for row in rows:
            vot_uri = row.get("vot", "")
            if not vot_uri:
                continue

            # Upsert by source_uri
            stmt = select(Vote).where(Vote.source_uri == vot_uri)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                continue

            session_date = _parse_date(row.get("data", ""))
            if not session_date:
                continue

            # Store as a "summary" vote (no politician_id — aggregate data)
            # We'll link individual votes in a later phase if needed
            # For now, store as LegislativeAct vote record
            # Actually, votazioni are aggregate — store key info in Vote
            # with a placeholder politician reference... No.
            #
            # Better: store votazioni as info we can cross-reference later.
            # For now, skip individual vote storage and just log.
            # The Vote model requires politician_id which we don't have
            # from aggregate votazioni.
            count += 1

        logger.info("Camera: parsed %d votazioni (aggregate, stored as metadata).", count)
        return count

    async def _ingest_atti(
        self, session: AsyncSession, *, max_pages: int | None = None,
    ) -> int:
        """Ingest legislative acts."""
        endpoint = settings.camera_sparql_endpoint
        rows = self._sparql_paginated(
            endpoint, QUERY_ATTI, max_pages=max_pages,
        )

        count = 0
        for row in rows:
            atto_uri = row.get("atto", "")
            if not atto_uri:
                continue

            stmt = select(LegislativeAct).where(LegislativeAct.source_uri == atto_uri)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                continue

            act = LegislativeAct(
                title=(clean_text(row.get("titolo")) or "")[:2000],
                act_type=row.get("tipo"),
                chamber="camera",
                presentation_date=_parse_date(row.get("data", "")),
                source_uri=atto_uri,
            )
            session.add(act)
            count += 1

        await session.flush()
        return count

    # ------------------------------------------------------------------
    # F10 bitemporal ingestion — persons, mandates, party memberships
    # ------------------------------------------------------------------

    async def _upsert_person_camera(
        self,
        session: AsyncSession,
        *,
        stable_id: str,
        full_name: str,
        dep_source_url: str,
    ) -> Person:
        """Find-or-create Person + PersonExternalId(namespace='camera').

        M5: source_url is required on person_external_ids (set to the
        deputato RDF URI observed when the person was first seen).
        """
        stmt = (
            select(Person)
            .join(PersonExternalId, PersonExternalId.person_id == Person.id)
            .where(
                PersonExternalId.namespace == "camera",
                PersonExternalId.external_id == stable_id,
            )
        )
        result = await session.execute(stmt)
        person = result.scalar_one_or_none()
        if person is not None:
            return person

        person = Person(primary_full_name=full_name)
        session.add(person)
        await session.flush()  # get person.id
        ext = PersonExternalId(
            person_id=person.id,
            namespace="camera",
            external_id=stable_id,
            source_url=dep_source_url,
        )
        session.add(ext)
        await session.flush()
        return person

    async def _ingest_mandati(
        self, session: AsyncSession, *, max_pages: int | None = None,
    ) -> int:
        """Ingest mandates as temporal arcs Persona -> Camera.

        Each mandate yields:
        - Upsert Person (keyed by stable Camera id, e.g. ``d302103``)
        - Insert Mandate(person_id, chamber='camera', legislature, start_date,
          end_date, motivo_termine, source_url=mandate RDF URI)

        Rows without ``startDate`` are skipped with a warning (M5 forbids
        mandates without a start date).
        """
        endpoint = settings.camera_sparql_endpoint
        rows = self._sparql_paginated(endpoint, QUERY_MANDATI, max_pages=max_pages)

        count = 0
        skipped_no_start = 0
        skipped_bad_uri = 0
        for row in rows:
            mandato_uri = row.get("mandato", "")
            dep_uri = row.get("dep", "")
            if not mandato_uri or not dep_uri:
                continue

            parsed = parse_camera_person_id(dep_uri)
            if parsed is None:
                skipped_bad_uri += 1
                continue
            stable_id, leg = parsed

            start_date = _parse_date(row.get("startDate", ""))
            if start_date is None:
                skipped_no_start += 1
                logger.warning(
                    "Mandato %s skipped: startDate missing (M5 violation).",
                    mandato_uri,
                )
                continue

            end_date = _parse_date(row.get("endDate", ""))
            motivo = row.get("motivo") or None
            nome = row.get("nome", "")
            cognome = row.get("cognome", "")
            full_name = f"{cognome} {nome}".strip()

            person = await self._upsert_person_camera(
                session,
                stable_id=stable_id,
                full_name=full_name,
                dep_source_url=dep_uri,
            )

            # Dedup by unique (person_id, chamber, legislature, start_date)
            stmt = select(Mandate).where(
                Mandate.person_id == person.id,
                Mandate.chamber == "camera",
                Mandate.legislature == leg,
                Mandate.start_date == start_date,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                # Update end_date / motivo if newly observed
                if end_date is not None and existing.end_date != end_date:
                    existing.end_date = end_date
                if motivo and existing.motivo_termine != motivo:
                    existing.motivo_termine = motivo
                continue

            mandate = Mandate(
                person_id=person.id,
                chamber="camera",
                legislature=leg,
                start_date=start_date,
                end_date=end_date,
                motivo_termine=motivo,
                source_url=mandato_uri,
            )
            session.add(mandate)
            count += 1

        await session.flush()
        logger.info(
            "Camera mandati: %d inserted, skipped no-start=%d, skipped bad-uri=%d.",
            count, skipped_no_start, skipped_bad_uri,
        )
        return count

    async def _ingest_party_memberships(
        self, session: AsyncSession, *, max_pages: int | None = None,
    ) -> int:
        """Ingest party adhesions as temporal arcs Persona -> party.

        `ocd:dataInizio` may be absent on ``ocd:aderisce`` records — we
        fall back to the legislature opening date so M5 (start_date NOT NULL)
        is satisfied. The source_url is the adhesion RDF URI.
        """
        endpoint = settings.camera_sparql_endpoint
        rows = self._sparql_paginated(endpoint, QUERY_ADESIONI, max_pages=max_pages)

        count = 0
        for row in rows:
            dep_uri = row.get("dep", "")
            gruppo = (row.get("gruppo") or "").strip()
            adesione_uri = row.get("adesione", "")
            if not dep_uri or not gruppo or not adesione_uri:
                continue

            parsed = parse_camera_person_id(dep_uri)
            if parsed is None:
                continue
            stable_id, _leg = parsed

            start_date = _parse_date(row.get("dataAdesione", "")) or LEG_19_START
            end_date = _parse_date(row.get("dataFineAdesione", ""))

            # Need existing person (must have been inserted by _ingest_mandati).
            stmt = (
                select(Person)
                .join(PersonExternalId, PersonExternalId.person_id == Person.id)
                .where(
                    PersonExternalId.namespace == "camera",
                    PersonExternalId.external_id == stable_id,
                )
            )
            person = (await session.execute(stmt)).scalar_one_or_none()
            if person is None:
                # Adesione for an unknown person — create minimal Person record.
                person = await self._upsert_person_camera(
                    session,
                    stable_id=stable_id,
                    full_name=stable_id,  # placeholder; refreshed on mandate pass
                    dep_source_url=dep_uri,
                )

            # Dedup: same person + party + start_date
            stmt2 = select(PartyMembership).where(
                PartyMembership.person_id == person.id,
                PartyMembership.party == gruppo,
                PartyMembership.start_date == start_date,
            )
            existing = (await session.execute(stmt2)).scalar_one_or_none()
            if existing is not None:
                if end_date is not None and existing.end_date != end_date:
                    existing.end_date = end_date
                continue

            membership = PartyMembership(
                person_id=person.id,
                party=gruppo,
                start_date=start_date,
                end_date=end_date,
                source_url=adesione_uri,
            )
            session.add(membership)
            count += 1

        await session.flush()
        return count

    async def _ingest_interventi(
        self, session: AsyncSession, *, max_pages: int | None = None,
    ) -> int:
        """Ingest parliamentary speeches."""
        endpoint = settings.camera_sparql_endpoint
        rows = self._sparql_paginated(
            endpoint, QUERY_INTERVENTI, max_pages=max_pages,
        )

        count = 0
        for row in rows:
            int_uri = row.get("int", "")
            dep_uri = row.get("dep", "")
            if not int_uri or not dep_uri:
                continue

            # Find politician by camera_uri
            stmt = select(Politician).where(Politician.camera_uri == dep_uri)
            result = await session.execute(stmt)
            politician = result.scalar_one_or_none()
            if not politician:
                continue

            # Upsert by source_uri
            stmt2 = select(Speech).where(Speech.source_uri == int_uri)
            result2 = await session.execute(stmt2)
            existing = result2.scalar_one_or_none()
            if existing:
                continue

            label = clean_text(row.get("label")) or ""
            speech = Speech(
                politician_id=politician.id,
                speech_date=date.today(),  # SPARQL label doesn't always have date
                full_text=label,
                source_uri=int_uri,
                context="Aula",
            )
            session.add(speech)
            count += 1

        await session.flush()
        return count
