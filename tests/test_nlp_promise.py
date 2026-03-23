"""Tests for NLP promise extraction pipeline.

L1: Unit tests for each function
L2: External oracle tests with SOURCE citations
L3: Property-based tests with Hypothesis
"""

import asyncio

from hypothesis import given, settings
from hypothesis import strategies as st

from codicecivico.nlp.ner import split_sentences
from codicecivico.nlp.promise import (
    TOPIC_KEYWORDS,
    ClaimResult,
    classify_topic,
    detect_claims,
    extract_promises,
    score_specificity,
)
from tests.fixtures.promise_samples import PROMISE_SAMPLES

# ---------------------------------------------------------------------------
# L1: Unit tests — sentence splitting
# ---------------------------------------------------------------------------


class TestSplitSentences:
    """L1: Unit tests for sentence splitting."""

    def test_multiple_sentences(self) -> None:
        result = split_sentences("Prima. Seconda. Terza.")
        assert len(result) >= 3

    def test_preserves_content(self) -> None:
        text = "Ci impegniamo a ridurre le tasse."
        result = split_sentences(text)
        assert any("impegniamo" in s for s in result)

    def test_handles_exclamation(self) -> None:
        result = split_sentences("Basta! Dobbiamo agire!")
        assert len(result) >= 2

    def test_no_empty_strings(self) -> None:
        result = split_sentences("  Prima.   Seconda.  ")
        assert all(s.strip() for s in result)


# ---------------------------------------------------------------------------
# L1: Unit tests — claim detection
# ---------------------------------------------------------------------------


class TestDetectClaims:
    """L1: Unit tests for commitment verb detection."""

    def test_ci_impegniamo(self) -> None:
        result = detect_claims(["Ci impegniamo a ridurre le tasse."])
        assert result[0].is_promise is True
        assert result[0].raw_confidence >= 0.8

    def test_future_tense_remo(self) -> None:
        result = detect_claims(["Investiremo nella scuola pubblica."])
        assert result[0].is_promise is True

    def test_future_tense_ra(self) -> None:
        result = detect_claims(["Il Governo garantirà l'accesso alla sanità."])
        assert result[0].is_promise is True

    def test_vogliamo(self) -> None:
        result = detect_claims(["Vogliamo riformare la giustizia."])
        assert result[0].is_promise is True

    def test_e_necessario(self) -> None:
        result = detect_claims(["È necessario aumentare le pensioni minime."])
        assert result[0].is_promise is True

    def test_dobbiamo(self) -> None:
        result = detect_claims(["Dobbiamo costruire 500.000 alloggi."])
        assert result[0].is_promise is True

    def test_proponiamo(self) -> None:
        result = detect_claims(["Proponiamo di abolire il canone RAI."])
        assert result[0].is_promise is True

    def test_question_excluded(self) -> None:
        result = detect_claims(["Quale sarà l'impatto sulla spesa?"])
        assert result[0].is_promise is False

    def test_procedural_excluded(self) -> None:
        result = detect_claims(["La seduta è aperta alle ore 10."])
        assert result[0].is_promise is False

    def test_factual_excluded(self) -> None:
        result = detect_claims(["Il PIL è cresciuto del 2% nel 2024."])
        assert result[0].is_promise is False

    def test_vagueness_reduces_confidence(self) -> None:
        vague = detect_claims(["Faremo di tutto per migliorare."])
        specific = detect_claims(["Ci impegniamo a ridurre le tasse del 5%."])
        assert vague[0].raw_confidence < specific[0].raw_confidence

    def test_returns_claim_result_type(self) -> None:
        results = detect_claims(["Una frase qualunque."])
        assert isinstance(results[0], ClaimResult)

    def test_empty_list(self) -> None:
        assert detect_claims([]) == []


# ---------------------------------------------------------------------------
# L1: Unit tests — topic classification
# ---------------------------------------------------------------------------


class TestClassifyTopic:
    """L1: Unit tests for keyword-based topic classification."""

    def test_economia(self) -> None:
        topic, _ = classify_topic("Ridurremo le tasse e le aliquote IRPEF.")
        assert topic == "economia"

    def test_istruzione(self) -> None:
        topic, _ = classify_topic("Investiremo nella scuola e nell'università.")
        assert topic == "istruzione"

    def test_giustizia(self) -> None:
        topic, _ = classify_topic("Riformeremo la giustizia civile e i tribunali.")
        assert topic == "giustizia"

    def test_sanita(self) -> None:
        topic, _ = classify_topic("Potenziare la sanità e gli ospedali.")
        assert topic == "sanita"

    def test_lavoro(self) -> None:
        topic, _ = classify_topic("Aumenteremo gli stipendi dei lavoratori.")
        assert topic == "lavoro"

    def test_ambiente(self) -> None:
        topic, _ = classify_topic("Investiremo nelle energie rinnovabili per il clima.")
        assert topic == "ambiente"

    def test_altro_fallback(self) -> None:
        topic, conf = classify_topic("Faremo grandi cose per il paese.")
        assert topic == "altro"
        assert conf <= 0.5

    def test_confidence_positive(self) -> None:
        _, conf = classify_topic("Ridurremo le tasse sul lavoro.")
        assert conf > 0.0


# ---------------------------------------------------------------------------
# L1: Unit tests — specificity scoring
# ---------------------------------------------------------------------------


class TestSpecificity:
    """L1: Unit tests for specificity scoring."""

    def test_specific_with_numbers_and_dates(self) -> None:
        score = score_specificity(
            "Investiremo 5 miliardi entro il 2027 per la scuola pubblica."
        )
        assert score >= 0.5

    def test_vague_promise(self) -> None:
        score = score_specificity("Faremo di tutto per migliorare la situazione.")
        assert score <= 0.2

    def test_bare_commitment(self) -> None:
        score = score_specificity("Ci impegniamo a ridurre le tasse.")
        assert 0.1 <= score <= 0.5

    def test_score_range(self) -> None:
        score = score_specificity("Una frase qualunque senza impegni.")
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# L2: External oracle tests
# ---------------------------------------------------------------------------


class TestExternalOracles:
    """L2: Tests with values from external sources."""

    def test_hand_labeled_samples_precision(self) -> None:
        """L2: Hand-labeled Italian parliamentary sentence classification.

        # SOURCE: Sentences modeled on Camera dei Deputati XIX Legislatura
        # (dati.camera.it) — speech patterns and procedural formulas.
        # Expected: precision >= 0.7 on 20 hand-labeled sentences.
        """
        sentences = [s["sentence"] for s in PROMISE_SAMPLES]
        results = detect_claims(sentences)

        tp = fp = fn = tn = 0
        for sample, result in zip(PROMISE_SAMPLES, results):
            expected = sample["is_promise"]
            actual = result.is_promise
            if expected and actual:
                tp += 1
            elif not expected and not actual:
                tn += 1
            elif expected and not actual:
                fn += 1
            else:
                fp += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        assert precision >= 0.7, f"Precision {precision:.2f} < 0.7 (TP={tp}, FP={fp})"
        assert recall >= 0.7, f"Recall {recall:.2f} < 0.7 (TP={tp}, FN={fn})"

    def test_italian_future_tense_conjugation(self) -> None:
        """L2: Italian future tense detection.

        # SOURCE: Treccani grammatica italiana — futuro semplice
        # Regular verbs: parlare→parleremo, ridurre→ridurremo, finire→finiremo
        # https://www.treccani.it/enciclopedia/futuro_(Enciclopedia-dell'Italiano)/
        """
        future_sentences = [
            "Parleremo di questo in Aula.",
            "Ridurremo le aliquote fiscali.",
            "Costruiremo nuove infrastrutture.",
        ]
        results = detect_claims(future_sentences)
        detected = sum(1 for r in results if r.is_promise)
        assert detected >= 2, f"Only {detected}/3 future tense sentences detected"

    def test_known_political_commitment_patterns(self) -> None:
        """L2: Common Italian political commitment formulas.

        # SOURCE: Camera dei Deputati — Resoconto stenografico XIX Legislatura
        # Common patterns used by speakers when making commitments:
        # "Il Governo intende...", "Ci impegniamo a...", "Proponiamo di..."
        """
        patterns = [
            "Il Governo intende procedere con la riforma del fisco.",
            "Ci impegniamo a portare a termine questo percorso legislativo.",
            "Proponiamo di introdurre un salario minimo a livello nazionale.",
        ]
        results = detect_claims(patterns)
        detected = sum(1 for r in results if r.is_promise)
        assert detected == 3, f"Only {detected}/3 commitment patterns detected"


# ---------------------------------------------------------------------------
# L3: Property-based tests (Hypothesis)
# ---------------------------------------------------------------------------


class TestPropertyBased:
    """L3: Property-based tests for NLP pipeline invariants."""

    @given(text=st.text(min_size=1, max_size=500, alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
    )))
    @settings(max_examples=50)
    def test_split_returns_list_of_strings(self, text: str) -> None:
        """split_sentences always returns a list of strings."""
        result = split_sentences(text)
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    @given(text=st.text(min_size=1, max_size=200))
    @settings(max_examples=50)
    def test_detect_claims_returns_for_all_sentences(self, text: str) -> None:
        """detect_claims returns one result per input sentence."""
        sentences = split_sentences(text)
        if sentences:
            results = detect_claims(sentences)
            assert len(results) == len(sentences)

    @given(text=st.text(min_size=1, max_size=200))
    @settings(max_examples=50)
    def test_specificity_score_always_in_range(self, text: str) -> None:
        """score_specificity always returns a float in [0, 1]."""
        score = score_specificity(text)
        assert 0.0 <= score <= 1.0, f"Score {score} out of range for: {text!r}"

    @given(text=st.text(min_size=1, max_size=200))
    @settings(max_examples=50)
    def test_classify_topic_always_valid(self, text: str) -> None:
        """classify_topic always returns a valid topic name."""
        valid_topics = set(TOPIC_KEYWORDS.keys()) | {"altro"}
        topic, conf = classify_topic(text)
        assert topic in valid_topics, f"Invalid topic: {topic}"
        assert 0.0 <= conf <= 1.0, f"Confidence {conf} out of range"

    @given(text=st.text(min_size=10, max_size=500, alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
    )))
    @settings(max_examples=20)
    def test_promise_count_leq_sentence_count(self, text: str) -> None:
        """Number of extracted promises <= number of sentences."""
        sentences = split_sentences(text)
        promises = asyncio.run(extract_promises(text))
        assert len(promises) <= len(sentences)

    @given(text=st.text(min_size=10, max_size=300))
    @settings(max_examples=20)
    def test_extract_promises_all_fields_present(self, text: str) -> None:
        """Every extracted promise has all required fields."""
        promises = asyncio.run(extract_promises(text))
        required_keys = {
            "sentence", "topic", "topic_confidence",
            "specificity_score", "confidence",
        }
        for p in promises:
            assert required_keys.issubset(p.keys()), f"Missing keys: {required_keys - p.keys()}"


# ---------------------------------------------------------------------------
# Full pipeline integration
# ---------------------------------------------------------------------------


class TestFullPipeline:
    """Integration test for the complete extraction pipeline."""

    def test_parliamentary_speech_extraction(self) -> None:
        """Full pipeline on a realistic parliamentary speech."""
        speech = (
            "Signor Presidente, colleghi deputati. "
            "Il Governo si impegna a ridurre le aliquote IRPEF per i redditi fino a 28.000 euro. "
            "Investiremo 3 miliardi di euro nella sanità pubblica entro il 2027. "
            "Ringrazio il Ministro per la sua risposta. "
            "Vogliamo riformare la giustizia civile per dimezzare i tempi dei processi. "
            "La seduta è tolta."
        )
        promises = asyncio.run(extract_promises(speech))

        # Should detect 3 promises (IRPEF, sanità, giustizia)
        assert len(promises) >= 3, f"Expected >= 3 promises, got {len(promises)}"

        # Check topics make sense
        topics = [p["topic"] for p in promises]
        assert "economia" in topics or "lavoro" in topics
        assert "giustizia" in topics

        # Procedural/courtesy sentences should NOT be promises
        promise_texts = [p["sentence"] for p in promises]
        assert not any("Ringrazio" in t for t in promise_texts)
        assert not any("seduta è tolta" in t for t in promise_texts)

    def test_empty_input(self) -> None:
        assert asyncio.run(extract_promises("")) == []
        assert asyncio.run(extract_promises("   ")) == []
