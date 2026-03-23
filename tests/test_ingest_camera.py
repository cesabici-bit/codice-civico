"""Tests for Camera dei Deputati SPARQL ingestor."""

import json
from pathlib import Path
from unittest.mock import patch

from codicecivico.ingest.camera import CameraIngestor, _parse_date

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# L1: Unit tests — _parse_date
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_yyyymmdd(self) -> None:
        assert _parse_date("19770115") is not None
        assert _parse_date("19770115").isoformat() == "1977-01-15"

    def test_iso_format(self) -> None:
        assert _parse_date("1977-01-15") is not None
        assert _parse_date("1977-01-15").isoformat() == "1977-01-15"

    def test_empty(self) -> None:
        assert _parse_date("") is None
        assert _parse_date(None) is None  # type: ignore[arg-type]

    def test_garbage(self) -> None:
        assert _parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# L2: Domain sanity — SPARQL response parsing
# SOURCE: dati.camera.it/sparql — Legislatura 19, verified 2026-03-23
# Deputies include Giorgia Meloni (Fratelli d'Italia), Elly Schlein (PD)
# ---------------------------------------------------------------------------


class TestCameraSparqlParsing:
    """Test that SPARQL JSON responses are correctly parsed into rows."""

    def test_deputati_fixture_has_known_politicians(self) -> None:
        """L2: Fixture must contain Meloni and Schlein (leg 19 deputies).
        # SOURCE: camera.it legislature 19 deputies page
        """
        data = json.loads((FIXTURES / "camera_deputati.json").read_text())
        bindings = data["results"]["bindings"]
        names = {b["cognome"]["value"] for b in bindings}
        assert "MELONI" in names, "Meloni must be a leg 19 deputy"
        assert "SCHLEIN" in names, "Schlein must be a leg 19 deputy"

    def test_deputati_row_parsing(self) -> None:
        """Verify _sparql_query output format matches expected structure."""
        data = json.loads((FIXTURES / "camera_deputati.json").read_text())
        bindings = data["results"]["bindings"]
        rows = [
            {k: v.get("value", "") for k, v in row.items()}
            for row in bindings
        ]
        assert len(rows) == 3
        meloni = rows[0]
        assert meloni["nome"] == "GIORGIA"
        assert meloni["cognome"] == "MELONI"
        assert "dep" in meloni
        assert meloni["dep"].startswith("http://dati.camera.it/ocd/")

    def test_deputati_date_parsing(self) -> None:
        """L2: Birth date of Meloni is 1977-01-15.
        # SOURCE: camera.it legislature 19 deputies page
        """
        data = json.loads((FIXTURES / "camera_deputati.json").read_text())
        meloni = data["results"]["bindings"][0]
        birth = _parse_date(meloni["dataNascita"]["value"])
        assert birth is not None
        assert birth.year == 1977
        assert birth.month == 1
        assert birth.day == 15

    def test_atti_fixture_parsing(self) -> None:
        """Verify atti fixture has correct structure."""
        data = json.loads((FIXTURES / "camera_atti.json").read_text())
        bindings = data["results"]["bindings"]
        assert len(bindings) == 2
        first = bindings[0]
        assert "atto" in first
        assert "titolo" in first
        assert first["atto"]["value"].startswith("http://dati.camera.it/")


# ---------------------------------------------------------------------------
# L1: CameraIngestor unit — _sparql_query mocked
# ---------------------------------------------------------------------------


class TestCameraIngestorMocked:
    """Test CameraIngestor with mocked SPARQL responses (no network)."""

    def test_sparql_query_returns_rows(self) -> None:
        """_sparql_query must return list of dicts."""
        fixture = json.loads((FIXTURES / "camera_deputati.json").read_text())

        mock_result = type("R", (), {
            "convert": lambda self: fixture,
        })()
        mock_wrapper = type("W", (), {
            "setQuery": lambda self, q: None,
            "setReturnFormat": lambda self, f: None,
            "setTimeout": lambda self, t: None,
            "query": lambda self: mock_result,
        })()

        with patch("codicecivico.ingest.base.SPARQLWrapper", return_value=mock_wrapper):
            rows = CameraIngestor._sparql_query(
                "http://fake-endpoint/sparql",
                "SELECT * WHERE { ?s ?p ?o } LIMIT 1",
            )
            assert len(rows) == 3
            assert rows[0]["cognome"] == "MELONI"
