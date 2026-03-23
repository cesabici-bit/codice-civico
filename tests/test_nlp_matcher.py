"""Tests for NLP promise-legislation matcher.

L1: Unit tests for matching functions
L2: External oracle test with real legislative act titles
"""

import pytest

from codicecivico.nlp.matcher import (
    cosine_similarity,
    encode_texts,
    find_best_matches,
)

# ---------------------------------------------------------------------------
# L1: Unit tests — cosine similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    """L1: Unit tests for cosine similarity computation."""

    def test_identical_vectors(self) -> None:
        assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_opposite_vectors(self) -> None:
        assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_zero_vector(self) -> None:
        assert cosine_similarity([0, 0], [1, 1]) == pytest.approx(0.0)

    def test_non_unit_vectors(self) -> None:
        sim = cosine_similarity([2, 0], [3, 0])
        assert sim == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# L1: Unit tests — encoding
# ---------------------------------------------------------------------------


class TestEncodeTexts:
    """L1: Unit tests for text encoding."""

    def test_returns_list_of_lists(self) -> None:
        result = encode_texts(["ciao", "mondo"])
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert all(isinstance(v, float) for v in result[0])

    def test_same_text_same_embedding(self) -> None:
        result = encode_texts(["test test", "test test"])
        sim = cosine_similarity(result[0], result[1])
        assert sim > 0.99

    def test_different_texts_different_embeddings(self) -> None:
        result = encode_texts(["gatto nero", "economia fiscale"])
        sim = cosine_similarity(result[0], result[1])
        assert sim < 0.9  # Should not be identical


# ---------------------------------------------------------------------------
# L1: Unit tests — matching
# ---------------------------------------------------------------------------


class TestFindBestMatches:
    """L1: Unit tests for promise-act matching."""

    def test_empty_promises(self) -> None:
        assert find_best_matches([], ["atto uno"]) == []

    def test_empty_acts(self) -> None:
        assert find_best_matches(["promessa uno"], []) == []

    def test_returns_match_structure(self) -> None:
        matches = find_best_matches(
            ["riforma della scuola"],
            ["disposizioni in materia di istruzione"],
            threshold=0.0,
        )
        assert len(matches) >= 1
        m = matches[0]
        assert "promise_idx" in m
        assert "act_idx" in m
        assert "similarity" in m

    def test_threshold_filtering(self) -> None:
        matches_low = find_best_matches(
            ["gatto nero"],
            ["riforma fiscale"],
            threshold=0.0,
        )
        matches_high = find_best_matches(
            ["gatto nero"],
            ["riforma fiscale"],
            threshold=0.99,
        )
        assert len(matches_low) >= len(matches_high)


# ---------------------------------------------------------------------------
# L2: External oracle — real legislative act titles
# ---------------------------------------------------------------------------


class TestMatcherExternalOracles:
    """L2: Tests with real Italian legislative act titles."""

    def test_semantic_match_istruzione(self) -> None:
        """L2: Promise about school reform matches education legislation.

        # SOURCE: Camera dei Deputati — DDL XIX Legislatura
        # "Disposizioni in materia di istruzione" is a common DDL title format
        # from dati.camera.it atti legislativi.
        """
        matches = find_best_matches(
            ["Investiremo nella scuola pubblica e nell'istruzione"],
            [
                "Disposizioni in materia di istruzione pubblica",
                "Interventi per la difesa nazionale",
                "Ratifica trattato internazionale con la Germania",
            ],
            threshold=0.1,
        )
        assert len(matches) >= 1
        best = matches[0]
        assert best["act_idx"] == 0  # Should match istruzione, not difesa

    def test_semantic_match_giustizia(self) -> None:
        """L2: Promise about justice reform matches civil procedure legislation.

        # SOURCE: Camera dei Deputati — common DDL title patterns
        # "Modifiche al codice di procedura civile" from dati.camera.it
        """
        matches = find_best_matches(
            ["Riformeremo la giustizia civile per accelerare i processi"],
            [
                "Modifiche al codice di procedura civile",
                "Disposizioni in materia di bilancio dello Stato",
                "Norme sulla tutela ambientale",
            ],
            threshold=0.1,
        )
        assert len(matches) >= 1
        best = matches[0]
        assert best["act_idx"] == 0  # Should match procedura civile

    def test_unrelated_promise_low_similarity(self) -> None:
        """L2: Unrelated promise/act pair should have low similarity.

        # SOURCE: Semantic distance — a promise about taxes should not
        # strongly match a defense treaty ratification.
        """
        matches = find_best_matches(
            ["Ridurremo le tasse sul reddito da lavoro"],
            ["Ratifica del trattato NATO per la cooperazione militare"],
            threshold=0.5,
        )
        # Should NOT match at threshold 0.5
        assert len(matches) == 0
