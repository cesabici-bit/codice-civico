r"""Tests for F10 Senato bitemporal graph ingestion (mandates only).

Target: `ingest/senato.py::parse_senato_person_id` + `_ingest_mandati_senato`.

Oracles used (L2):
- Live SPARQL dati.senato.it on 2026-04-18 (SPARQLWrapper) — verified URI
  pattern `senatore/{N}` is persona-stable (bare integer, no prefix/suffix).
  Confirmed `senatore/63` (Amoruso) present across historical legislatures
  via owl:sameAs chain to Camera deputato URIs.
- Mandate URI pattern `mandato/{S|C}_{leg}_{id}_{k}` where `S`=Senato
  native mandate and `C`=Camera mandate referenced from the Senato
  profile (same person was also a deputy in another legislature).
- Dates in ISO `YYYY-MM-DD` format (`osr:inizio` / `osr:fine`).
"""

import json
from pathlib import Path

from codicecivico.ingest.senato import (
    _parse_date_senato,
    parse_senato_person_id,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# L1: parse_senato_person_id — regex on senatore RDF URI
# ---------------------------------------------------------------------------


class TestParseSenatoPersonId:
    """Unit tests for the Senato person-id extractor."""

    def test_current_senator_uri(self) -> None:
        """L2: senatore/22922 = Della Vedova leg 19.
        # SOURCE: dati.senato.it SPARQL live 2026-04-18
        """
        uri = "http://dati.senato.it/senatore/22922"
        assert parse_senato_person_id(uri) == "22922"

    def test_historical_senator_uri(self) -> None:
        """L2: senatore/63 = Amoruso, stable across historical legs.
        # SOURCE: dati.senato.it owl:sameAs chain (Camera leg 12-14)
        """
        uri = "http://dati.senato.it/senatore/63"
        assert parse_senato_person_id(uri) == "63"

    def test_rejects_camera_uri(self) -> None:
        """Camera deputy URIs must not match Senato parser."""
        uri = "http://dati.camera.it/ocd/deputato.rdf/d302103_19"
        assert parse_senato_person_id(uri) is None

    def test_rejects_mandate_uri(self) -> None:
        """Mandate URIs (mandato/S_...) must not match person parser."""
        uri = "http://dati.senato.it/mandato/S_19_29040_1"
        assert parse_senato_person_id(uri) is None

    def test_rejects_garbage(self) -> None:
        assert parse_senato_person_id("") is None
        assert parse_senato_person_id(None) is None  # type: ignore[arg-type]
        assert parse_senato_person_id("http://dati.senato.it/") is None
        assert parse_senato_person_id("senatore/abc") is None


# ---------------------------------------------------------------------------
# L2: mandate fixture parsing
# SOURCE: dati.senato.it/sparql live 2026-04-18 — osr:mandato for leg 19
# ---------------------------------------------------------------------------


class TestSenatoMandateFixture:
    def test_fixture_loads(self) -> None:
        data = json.loads((FIXTURES / "senato_mandati.json").read_text())
        assert "results" in data
        assert len(data["results"]["bindings"]) == 3

    def test_first_row_is_della_vedova_camera_mandate(self) -> None:
        """Row 0 shows a senator with a ``C_*`` mandate — previously a deputy.

        # SOURCE: Della Vedova was a deputy before becoming senator leg 19.
        The mandato URI prefix `C_` signals this is a Camera-provenance
        mandate attached to the senator's profile via owl:sameAs chain.
        """
        data = json.loads((FIXTURES / "senato_mandati.json").read_text())
        b = data["results"]["bindings"][0]
        assert b["cognome"]["value"] == "Della Vedova"
        assert "/mandato/C_" in b["mandato"]["value"]
        assert b["inizio"]["value"] == "2022-10-13"

    def test_terminated_mandate(self) -> None:
        """Row 1: Astorre's mandate terminated (deceased 2023-03-03)."""
        data = json.loads((FIXTURES / "senato_mandati.json").read_text())
        b = data["results"]["bindings"][1]
        assert b["cognome"]["value"] == "Astorre"
        assert b["fine"]["value"] == "2023-03-03"

    def test_ongoing_mandate_missing_fine(self) -> None:
        """Row 2: Marton's mandate ongoing — fine absent."""
        data = json.loads((FIXTURES / "senato_mandati.json").read_text())
        b = data["results"]["bindings"][2]
        assert "fine" not in b
        assert b["inizio"]["value"] == "2022-10-13"

    def test_iso_date_format_parses(self) -> None:
        """Confirm Senato YYYY-MM-DD format works with _parse_date_senato."""
        parsed = _parse_date_senato("2022-10-13")
        assert parsed is not None
        assert parsed.isoformat() == "2022-10-13"

    def test_all_rows_yield_stable_person_id(self) -> None:
        data = json.loads((FIXTURES / "senato_mandati.json").read_text())
        for b in data["results"]["bindings"]:
            sen_uri = b["sen"]["value"]
            pid = parse_senato_person_id(sen_uri)
            assert pid is not None
            assert pid.isdigit(), f"Senato id must be numeric, got {pid!r}"
