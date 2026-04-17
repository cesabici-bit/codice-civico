r"""Tests for F10 Camera bitemporal graph ingestion (mandati + party memberships).

Target: `ingest/camera.py::parse_camera_person_id` + `_ingest_mandati`.

Oracles used (L2):
- Live SPARQL dati.camera.it on 2026-04-18 (WebFetch) — verified URI pattern
  `deputato.rdf/d\d+_\d+` for Republic legislature 19, and that the numeric
  component is persona-stable across legislatures (Meloni `d302103` in
  leg 15, 16, 17, 18, 19).
- Historical Kingdom-of-Italy legislatures use prefixes `dd` / `dr` and are
  deferred per EC-015 (KNOWN_ISSUES.md) — regex must reject them.
"""

import json
from pathlib import Path

from codicecivico.ingest.camera import (
    _parse_date,
    parse_camera_person_id,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# L1: parse_camera_person_id — regex on deputato RDF URI
# ---------------------------------------------------------------------------


class TestParseCameraPersonId:
    """Unit tests for the Camera person-id extractor."""

    def test_modern_uri_meloni(self) -> None:
        uri = "http://dati.camera.it/ocd/deputato.rdf/d302103_19"
        assert parse_camera_person_id(uri) == ("d302103", 19)

    def test_modern_uri_different_leg(self) -> None:
        """L2: same stable id `d302103` appears in leg 15-19.
        # SOURCE: dati.camera.it SPARQL live 2026-04-18 — Meloni d302103
        """
        uri_15 = "http://dati.camera.it/ocd/deputato.rdf/d302103_15"
        uri_19 = "http://dati.camera.it/ocd/deputato.rdf/d302103_19"
        pid_15 = parse_camera_person_id(uri_15)
        pid_19 = parse_camera_person_id(uri_19)
        assert pid_15 is not None
        assert pid_19 is not None
        # Same stable id, different legislatures
        assert pid_15[0] == pid_19[0] == "d302103"
        assert pid_15[1] == 15
        assert pid_19[1] == 19

    def test_rejects_double_d_historical(self) -> None:
        """Historical `dd` prefix deferred per EC-015 — regex rejects it."""
        uri = "http://dati.camera.it/ocd/deputato.rdf/dd00018_13"
        assert parse_camera_person_id(uri) is None

    def test_rejects_dr_kingdom(self) -> None:
        """Kingdom-of-Italy `dr` prefix deferred per EC-015 — regex rejects it."""
        uri = "http://dati.camera.it/ocd/deputato.rdf/dr3325_22"
        assert parse_camera_person_id(uri) is None

    def test_rejects_senatore_uri(self) -> None:
        """Senato URIs must not match Camera parser."""
        uri = "http://dati.senato.it/loc/senatore/3923"
        assert parse_camera_person_id(uri) is None

    def test_rejects_garbage(self) -> None:
        assert parse_camera_person_id("") is None
        assert parse_camera_person_id("not a uri") is None
        assert parse_camera_person_id("http://dati.camera.it/") is None

    def test_rejects_no_leg_suffix(self) -> None:
        """Without `_LL` suffix it is not a mandate-bound person URI."""
        assert parse_camera_person_id(
            "http://dati.camera.it/ocd/deputato.rdf/d302103",
        ) is None


# ---------------------------------------------------------------------------
# L2: mandate row parsing from live-captured SPARQL fixture
# SOURCE: dati.camera.it/sparql live 2026-04-18 — ocd:mandatoCamera for leg 19
# ---------------------------------------------------------------------------


class TestMandateFixtureParsing:
    """Verify the fixture reflects real SPARQL shape and can be parsed."""

    def test_fixture_loads(self) -> None:
        data = json.loads((FIXTURES / "camera_mandati.json").read_text())
        assert "results" in data
        assert len(data["results"]["bindings"]) == 3

    def test_fixture_has_required_fields(self) -> None:
        data = json.loads((FIXTURES / "camera_mandati.json").read_text())
        for b in data["results"]["bindings"]:
            assert "mandato" in b
            assert "dep" in b
            assert "startDate" in b, "startDate is M5-required (valid_from NOT NULL)"
            assert "leg" in b

    def test_first_row_is_meloni_ongoing(self) -> None:
        """L2: row 0 = Meloni, mandate ongoing (no endDate/motivo).
        # SOURCE: Meloni PM since 2022-10-13, still in charge 2026-04-18
        """
        data = json.loads((FIXTURES / "camera_mandati.json").read_text())
        b = data["results"]["bindings"][0]
        assert b["cognome"]["value"] == "MELONI"
        assert b["startDate"]["value"] == "20221013"
        assert "endDate" not in b, "ongoing mandate must lack endDate"
        assert "motivo" not in b

    def test_terminated_mandate_has_motivo(self) -> None:
        """Row 1 shows a terminated mandate: startDate + endDate + motivoTermine."""
        data = json.loads((FIXTURES / "camera_mandati.json").read_text())
        b = data["results"]["bindings"][1]
        assert b["startDate"]["value"] == "20221008"
        assert b["endDate"]["value"] == "20260202"
        assert "Dimissioni" in b["motivo"]["value"]

    def test_date_format_is_yyyymmdd(self) -> None:
        """Confirm YYYYMMDD format parses via existing _parse_date."""
        parsed = _parse_date("20221013")
        assert parsed is not None
        assert parsed.isoformat() == "2022-10-13"

    def test_all_mandate_uris_parse_to_stable_person(self) -> None:
        """Every row yields a (person_id, legislature) pair via regex."""
        data = json.loads((FIXTURES / "camera_mandati.json").read_text())
        for b in data["results"]["bindings"]:
            dep_uri = b["dep"]["value"]
            parsed = parse_camera_person_id(dep_uri)
            assert parsed is not None, f"Failed to parse {dep_uri}"
            stable_id, leg = parsed
            assert stable_id.startswith("d") and stable_id[1].isdigit()
            assert leg == 19


# ---------------------------------------------------------------------------
# L1: mandate model surface — ensures new ORM entities exist and bind correctly
# ---------------------------------------------------------------------------


class TestGraphModelImports:
    """F10 ORM imports are available from codicecivico.models."""

    def test_person_model_importable(self) -> None:
        from codicecivico.models import Mandate, Person, PersonExternalId

        assert Person.__tablename__ == "persons"
        assert PersonExternalId.__tablename__ == "person_external_ids"
        assert Mandate.__tablename__ == "mandates"

    def test_mandate_requires_source_url(self) -> None:
        """M5 enforcement at ORM surface: source_url has nullable=False."""
        from codicecivico.models import Mandate

        col = Mandate.__table__.c["source_url"]
        assert col.nullable is False

    def test_mandate_requires_start_date(self) -> None:
        """M5 extended: start_date (valid_from) is NOT NULL."""
        from codicecivico.models import Mandate

        col = Mandate.__table__.c["start_date"]
        assert col.nullable is False

    def test_party_membership_requires_start_date(self) -> None:
        from codicecivico.models import PartyMembership

        col = PartyMembership.__table__.c["start_date"]
        assert col.nullable is False

    def test_relationship_requires_valid_from(self) -> None:
        from codicecivico.models import Relationship

        col = Relationship.__table__.c["valid_from"]
        assert col.nullable is False
