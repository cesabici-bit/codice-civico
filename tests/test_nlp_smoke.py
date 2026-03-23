"""M3 Smoke tests for NLP module — run BEFORE unit tests.

These tests verify that the NLP pipeline is importable and produces
human-readable output without requiring a database or heavy ML models.
"""

from codicecivico.nlp.ner import split_sentences

# ---------------------------------------------------------------------------
# Smoke: sentence splitting
# ---------------------------------------------------------------------------


class TestSentenceSplitSmoke:
    """Smoke tests for sentence splitting (spaCy or regex fallback)."""

    def test_split_basic_italian(self) -> None:
        """Three Italian sentences should produce 3 parts."""
        text = "Buongiorno. Ci impegniamo a ridurre le tasse. Grazie."
        result = split_sentences(text)
        assert len(result) >= 3, f"Expected >= 3 sentences, got {len(result)}: {result}"

    def test_split_empty_text(self) -> None:
        """Empty or whitespace text returns empty list."""
        assert split_sentences("") == []
        assert split_sentences("   ") == []

    def test_split_single_sentence(self) -> None:
        """A single sentence without period still returns 1 element."""
        result = split_sentences("Vogliamo riformare la giustizia")
        assert len(result) == 1

    def test_split_parliamentary_style(self) -> None:
        """Parliamentary speech with complex punctuation."""
        text = (
            "Signor Presidente, colleghi deputati! "
            "Il Governo intende procedere con la riforma fiscale. "
            "Ridurremo le aliquote IRPEF dal 2027. "
            "Questo è un impegno che prendiamo davanti al Paese."
        )
        result = split_sentences(text)
        assert len(result) >= 3, f"Expected >= 3 sentences, got {len(result)}: {result}"
        # Verify no empty strings
        assert all(s.strip() for s in result)

    def test_split_returns_strings(self) -> None:
        """All returned items are non-empty strings."""
        result = split_sentences("Prima frase. Seconda frase.")
        assert all(isinstance(s, str) and len(s) > 0 for s in result)


class TestNlpImportSmoke:
    """Smoke tests that NLP modules are importable."""

    def test_import_promise(self) -> None:
        from codicecivico.nlp.promise import extract_promises  # noqa: F401

    def test_import_matcher(self) -> None:
        from codicecivico.nlp.matcher import match_promise_to_votes  # noqa: F401

    def test_import_ner(self) -> None:
        from codicecivico.nlp.ner import extract_entities, split_sentences  # noqa: F401
