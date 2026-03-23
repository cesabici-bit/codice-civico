"""Tests for Senato della Repubblica SPARQL ingestor."""

import json
from pathlib import Path
from unittest.mock import patch

from codicecivico.ingest.senato import SenatoIngestor, _parse_date_senato

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# L1: Unit tests — _parse_date_senato
# ---------------------------------------------------------------------------


class TestParseDateSenato:
    def test_iso_format(self) -> None:
        assert _parse_date_senato("1947-07-18") is not None
        assert _parse_date_senato("1947-07-18").isoformat() == "1947-07-18"

    def test_yyyymmdd(self) -> None:
        assert _parse_date_senato("19470718") is not None
        assert _parse_date_senato("19470718").isoformat() == "1947-07-18"

    def test_slash_format(self) -> None:
        assert _parse_date_senato("18/07/1947") is not None
        assert _parse_date_senato("18/07/1947").isoformat() == "1947-07-18"

    def test_empty(self) -> None:
        assert _parse_date_senato("") is None
        assert _parse_date_senato(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# L2: Domain sanity — SPARQL response parsing
# SOURCE: dati.senato.it/sparql — Legislatura 19, verified 2026-03-23
# Senators include Ignazio La Russa (Presidente), Matteo Renzi
# ---------------------------------------------------------------------------


class TestSenatoSparqlParsing:
    """Test that Senato SPARQL JSON responses are correctly parsed."""

    def test_senatori_fixture_has_known_senators(self) -> None:
        """L2: Fixture must contain La Russa and Renzi (leg 19 senators).
        # SOURCE: senato.it legislature 19 senators page
        """
        data = json.loads((FIXTURES / "senato_senatori.json").read_text())
        bindings = data["results"]["bindings"]
        names = {b["cognome"]["value"] for b in bindings}
        assert "La Russa" in names, "La Russa must be a leg 19 senator"
        assert "Renzi" in names, "Renzi must be a leg 19 senator"

    def test_senatori_date_parsing(self) -> None:
        """L2: Birth date of La Russa is 1947-07-18.
        # SOURCE: senato.it legislature 19 senators page
        """
        data = json.loads((FIXTURES / "senato_senatori.json").read_text())
        la_russa = data["results"]["bindings"][0]
        birth = _parse_date_senato(la_russa["dataNascita"]["value"])
        assert birth is not None
        assert birth.year == 1947
        assert birth.month == 7
        assert birth.day == 18

    def test_ddl_fixture_parsing(self) -> None:
        """Verify DDL fixture has correct structure."""
        data = json.loads((FIXTURES / "senato_ddl.json").read_text())
        bindings = data["results"]["bindings"]
        assert len(bindings) == 2
        first = bindings[0]
        assert "ddl" in first
        assert "titolo" in first
        assert first["ddl"]["value"].startswith("http://dati.senato.it/")


# ---------------------------------------------------------------------------
# L1: SenatoIngestor unit — _sparql_query mocked
# ---------------------------------------------------------------------------


class TestSenatoIngestorMocked:
    """Test SenatoIngestor with mocked SPARQL responses (no network)."""

    def test_sparql_query_returns_rows(self) -> None:
        """_sparql_query must return list of dicts."""
        fixture = json.loads((FIXTURES / "senato_senatori.json").read_text())

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
            rows = SenatoIngestor._sparql_query(
                "http://fake-endpoint/sparql",
                "SELECT * WHERE { ?s ?p ?o } LIMIT 1",
            )
            assert len(rows) == 2
            assert rows[0]["cognome"] == "La Russa"
