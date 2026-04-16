"""Tests for BaseIngestor helpers (SPARQL pagination, etc)."""

from unittest.mock import patch

from codicecivico.ingest.base import BaseIngestor


class TestSparqlPaginated:
    """Regression tests for _sparql_paginated.

    The template substitution used to call `str.format()` which crashes on
    any SPARQL query containing literal `{...}` blocks (WHERE, UNION, etc),
    because `str.format` interprets them as named placeholders.
    """

    def test_accepts_sparql_with_literal_braces(self) -> None:
        """Regression: SPARQL query with WHERE block must not raise KeyError."""
        query = """
            PREFIX ocd: <http://dati.camera.it/ocd/>
            SELECT ?vot ?title WHERE {
              ?vot a ocd:Votazione .
              ?vot ocd:titolo ?title .
              FILTER (?title != "")
            }
            LIMIT {limit} OFFSET {offset}
        """

        captured_queries: list[str] = []

        def fake_query(_endpoint: str, q: str) -> list[dict[str, str]]:
            captured_queries.append(q)
            return []  # empty result -> single page, loop exits

        with patch.object(BaseIngestor, "_sparql_query", side_effect=fake_query):
            rows = BaseIngestor._sparql_paginated(
                "http://example.org/sparql",
                query,
                page_size=100,
            )

        assert rows == []
        assert len(captured_queries) == 1
        sent = captured_queries[0]
        assert "LIMIT 100 OFFSET 0" in sent
        # Braces in WHERE block must be preserved untouched
        assert "?vot a ocd:Votazione" in sent
        assert "WHERE {" in sent

    def test_paginates_until_short_page(self) -> None:
        """Multiple pages: stops when a page returns fewer rows than page_size."""
        query = "SELECT ?x WHERE { ?x a ?t } LIMIT {limit} OFFSET {offset}"
        pages = [
            [{"x": f"n{i}"} for i in range(10)],  # full page
            [{"x": "n10"}, {"x": "n11"}],  # short page -> stop
        ]
        call_count = {"n": 0}

        def fake_query(_endpoint: str, _q: str) -> list[dict[str, str]]:
            result = pages[call_count["n"]]
            call_count["n"] += 1
            return result

        with patch.object(BaseIngestor, "_sparql_query", side_effect=fake_query):
            rows = BaseIngestor._sparql_paginated(
                "http://example.org/sparql",
                query,
                page_size=10,
            )

        assert len(rows) == 12
        assert call_count["n"] == 2
