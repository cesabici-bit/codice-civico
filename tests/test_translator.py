"""Tests for the Legislative Translator (F7).

L1: Unit tests for prompt building, response parsing, article splitting.
L2: Tests with real Italian legislative text (SOURCE: Camera.it / Normattiva.it).
L3: Property-based tests via Hypothesis.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import given
from hypothesis import settings as hsettings
from hypothesis import strategies as st

from codicecivico.nlp.translator import (
    _build_prompt,
    _parse_llm_response,
    check_ollama_available,
    split_into_articles,
    translate_article,
    translate_law,
)

# =========================================================================
# Fixtures
# =========================================================================

# SOURCE: Art. 1 del Decreto-Legge 30 aprile 2019, n. 34 (Decreto Crescita)
# https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legge:2019-04-30;34
REAL_ARTICLE_1 = (
    "Art. 1. Maggiorazione dell'ammortamento per i beni strumentali nuovi. "
    "1. Ai fini delle imposte sui redditi, per i soggetti titolari di reddito "
    "d'impresa e per gli esercenti arti e professioni che effettuano "
    "investimenti in beni strumentali nuovi, esclusi i veicoli e gli altri "
    "mezzi di trasporto di cui all'articolo 164, comma 1, del testo unico "
    "delle imposte sui redditi, il costo di acquisizione è maggiorato del "
    "30 per cento."
)

# SOURCE: Art. 2 del Decreto-Legge 30 aprile 2019, n. 34
REAL_ARTICLE_2 = (
    "Art. 2. Revisione mini-IRES. "
    "1. A decorrere dal periodo d'imposta successivo a quello in corso al 31 "
    "dicembre 2018, il reddito complessivo netto dichiarato dalle società e "
    "dagli enti di cui all'articolo 73, comma 1, lettere a) e b), è assoggettato "
    "all'aliquota ridotta del 20,5 per cento per la parte corrispondente agli "
    "utili del periodo d'imposta precedente."
)

MULTI_ARTICLE_TEXT = f"{REAL_ARTICLE_1}\n\n{REAL_ARTICLE_2}"

# Simulated LLM response (well-formatted)
MOCK_LLM_RESPONSE_GOOD = (
    "COSA CAMBIA: Le imprese e i professionisti che comprano nuovi "
    "macchinari possono scaricare dalle tasse il 30% in più del costo. "
    "Sono escluse le auto aziendali.\n\n"
    "CHI BENEFICIA: Imprese e liberi professionisti che investono in "
    "nuovi beni strumentali (macchinari, computer, attrezzature).\n\n"
    "CHI PERDE: Lo Stato incassa meno tasse nel breve periodo.\n\n"
    "PRIMA vs DOPO: Prima le imprese potevano scaricare solo il costo "
    "effettivo del bene. Ora possono scaricare il costo maggiorato "
    "del 30%, riducendo le tasse da pagare."
)

# Simulated LLM response (poorly formatted — missing sections)
MOCK_LLM_RESPONSE_PARTIAL = """COSA CAMBIA: Le imprese pagano meno tasse sugli investimenti.

CHI BENEFICIA: Le imprese che investono."""

# Simulated LLM response (no sections at all)
MOCK_LLM_RESPONSE_UNSTRUCTURED = (
    "Questa legge permette alle imprese di pagare meno tasse quando comprano "
    "nuovi macchinari. Il risparmio è del 30% sul costo."
)


# =========================================================================
# L1: Unit Tests — _build_prompt
# =========================================================================


class TestBuildPrompt:
    """L1: prompt construction."""

    def test_contains_article_text(self) -> None:
        prompt = _build_prompt("Articolo di test")
        assert "Articolo di test" in prompt

    def test_contains_section_headers(self) -> None:
        prompt = _build_prompt("test")
        assert "COSA CAMBIA" in prompt
        assert "CHI BENEFICIA" in prompt
        assert "CHI PERDE" in prompt
        assert "PRIMA vs DOPO" in prompt

    def test_system_instruction_in_italian(self) -> None:
        prompt = _build_prompt("test")
        assert "giurista" in prompt.lower()

    def test_empty_article(self) -> None:
        prompt = _build_prompt("")
        # Should still build a valid prompt
        assert "COSA CAMBIA" in prompt


# =========================================================================
# L1: Unit Tests — _parse_llm_response
# =========================================================================


class TestParseLlmResponse:
    """L1: response parsing."""

    def test_parse_well_formatted(self) -> None:
        result = _parse_llm_response(MOCK_LLM_RESPONSE_GOOD)
        assert result["cosa_cambia"] != ""
        assert "30%" in result["cosa_cambia"]
        assert result["chi_beneficia"] != ""
        assert result["chi_perde"] != ""
        assert result["prima_vs_dopo"] != ""

    def test_parse_partial_response(self) -> None:
        result = _parse_llm_response(MOCK_LLM_RESPONSE_PARTIAL)
        assert result["cosa_cambia"] != ""
        assert result["chi_beneficia"] != ""
        assert result["chi_perde"] == ""
        assert result["prima_vs_dopo"] == ""

    def test_parse_unstructured_response(self) -> None:
        result = _parse_llm_response(MOCK_LLM_RESPONSE_UNSTRUCTURED)
        # No sections found — all empty
        assert all(v == "" for v in result.values())

    def test_parse_empty_string(self) -> None:
        result = _parse_llm_response("")
        assert len(result) == 4
        assert all(v == "" for v in result.values())

    def test_parse_numbered_format(self) -> None:
        """Handle '1. COSA CAMBIA:' format."""
        text = (
            "1. COSA CAMBIA: Nuove regole.\n"
            "2. CHI BENEFICIA: Tutti.\n"
            "3. CHI PERDE: Nessuno.\n"
            "4. PRIMA vs DOPO: Prima male, ora bene."
        )
        result = _parse_llm_response(text)
        assert result["cosa_cambia"] == "Nuove regole."
        assert result["chi_beneficia"] == "Tutti."
        assert result["chi_perde"] == "Nessuno."
        assert "Prima male" in result["prima_vs_dopo"]

    def test_parse_case_insensitive(self) -> None:
        text = "cosa cambia: Test insensitivo.\nchi beneficia: Tutti."
        result = _parse_llm_response(text)
        assert result["cosa_cambia"] == "Test insensitivo."


# =========================================================================
# L1: Unit Tests — split_into_articles
# =========================================================================


class TestSplitIntoArticles:
    """L1: article splitting."""

    def test_split_two_articles(self) -> None:
        articles = split_into_articles(MULTI_ARTICLE_TEXT)
        assert len(articles) == 2
        assert "Maggiorazione" in articles[0]
        assert "mini-IRES" in articles[1]

    def test_no_articles_returns_full_text(self) -> None:
        text = "Questo è un testo senza articoli numerati."
        articles = split_into_articles(text)
        assert len(articles) == 1
        assert articles[0] == text

    def test_empty_text(self) -> None:
        assert split_into_articles("") == []
        assert split_into_articles("   ") == []

    def test_single_article(self) -> None:
        articles = split_into_articles(REAL_ARTICLE_1)
        assert len(articles) == 1

    def test_articolo_spelled_out(self) -> None:
        text = "Articolo 1\nPrimo.\n\nArticolo 2\nSecondo."
        articles = split_into_articles(text)
        assert len(articles) == 2

    def test_art_bis_ter(self) -> None:
        text = "Art. 1\nPrimo.\n\nArt. 1-bis\nBis.\n\nArt. 2\nSecondo."
        articles = split_into_articles(text)
        assert len(articles) == 3

    def test_uppercase_art(self) -> None:
        text = "ART. 1\nPrimo.\n\nART. 2\nSecondo."
        articles = split_into_articles(text)
        assert len(articles) == 2


# =========================================================================
# L1: Unit Tests — translate_article (mocked Ollama)
# =========================================================================


class TestTranslateArticle:
    """L1: translate_article with mocked Ollama."""

    @pytest.mark.asyncio
    async def test_successful_translation(self) -> None:
        with patch(
            "codicecivico.nlp.translator._call_ollama",
            new_callable=AsyncMock,
            return_value=MOCK_LLM_RESPONSE_GOOD,
        ):
            result = await translate_article(REAL_ARTICLE_1)
            assert result is not None
            assert "cosa_cambia" in result
            assert "chi_beneficia" in result
            assert result["cosa_cambia"] != ""

    @pytest.mark.asyncio
    async def test_ollama_unavailable_returns_none(self) -> None:
        with patch(
            "codicecivico.nlp.translator._call_ollama",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await translate_article(REAL_ARTICLE_1)
            assert result is None

    @pytest.mark.asyncio
    async def test_empty_text_returns_none(self) -> None:
        result = await translate_article("")
        assert result is None

    @pytest.mark.asyncio
    async def test_whitespace_text_returns_none(self) -> None:
        result = await translate_article("   \n  ")
        assert result is None

    @pytest.mark.asyncio
    async def test_unstructured_response_falls_back(self) -> None:
        """If LLM doesn't use section format, raw text goes to cosa_cambia."""
        with patch(
            "codicecivico.nlp.translator._call_ollama",
            new_callable=AsyncMock,
            return_value=MOCK_LLM_RESPONSE_UNSTRUCTURED,
        ):
            result = await translate_article(REAL_ARTICLE_1)
            assert result is not None
            assert result["cosa_cambia"] != ""
            assert "macchinari" in result["cosa_cambia"]


# =========================================================================
# L1: Unit Tests — translate_law (mocked Ollama)
# =========================================================================


class TestTranslateLaw:
    """L1: translate_law orchestration."""

    @pytest.mark.asyncio
    async def test_full_law_translation(self) -> None:
        with (
            patch(
                "codicecivico.nlp.translator.check_ollama_available",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "codicecivico.nlp.translator._call_ollama",
                new_callable=AsyncMock,
                return_value=MOCK_LLM_RESPONSE_GOOD,
            ),
        ):
            result = await translate_law(MULTI_ARTICLE_TEXT)
            assert result is not None
            assert "articles" in result
            assert len(result["articles"]) == 2
            assert "summary" in result
            assert "translated_at" in result

    @pytest.mark.asyncio
    async def test_max_articles_limit(self) -> None:
        with (
            patch(
                "codicecivico.nlp.translator.check_ollama_available",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "codicecivico.nlp.translator._call_ollama",
                new_callable=AsyncMock,
                return_value=MOCK_LLM_RESPONSE_GOOD,
            ),
        ):
            result = await translate_law(MULTI_ARTICLE_TEXT, max_articles=1)
            assert result is not None
            assert len(result["articles"]) == 1

    @pytest.mark.asyncio
    async def test_ollama_unavailable(self) -> None:
        with patch(
            "codicecivico.nlp.translator.check_ollama_available",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await translate_law(MULTI_ARTICLE_TEXT)
            assert result is None

    @pytest.mark.asyncio
    async def test_empty_text_returns_none(self) -> None:
        result = await translate_law("")
        assert result is None


# =========================================================================
# L1: Unit Tests — check_ollama_available
# =========================================================================


class TestCheckOllamaAvailable:
    """L1: Ollama health check."""

    @pytest.mark.asyncio
    async def test_available(self) -> None:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("codicecivico.nlp.translator.httpx.AsyncClient", return_value=mock_client):
            assert await check_ollama_available() is True

    @pytest.mark.asyncio
    async def test_unavailable_connection_error(self) -> None:
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("codicecivico.nlp.translator.httpx.AsyncClient", return_value=mock_client):
            assert await check_ollama_available() is False


# =========================================================================
# L2: Domain Sanity Tests (real Italian legal text)
# =========================================================================


class TestL2DomainSanity:
    """L2: tests with real legislative text and SOURCE citations."""

    def test_prompt_for_real_article(self) -> None:
        """L2: prompt includes real article text.
        # SOURCE: Art. 1 D.L. 34/2019 (Decreto Crescita)
        # https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legge:2019-04-30;34
        """
        prompt = _build_prompt(REAL_ARTICLE_1)
        assert "30 per cento" in prompt
        assert "beni strumentali" in prompt

    def test_split_real_decreto(self) -> None:
        """L2: splitting a real decreto-legge.
        # SOURCE: D.L. 34/2019 structure — Arts 1-2
        """
        articles = split_into_articles(MULTI_ARTICLE_TEXT)
        assert len(articles) == 2
        # Art 1 should contain ammortamento
        assert "ammortamento" in articles[0].lower()
        # Art 2 should contain mini-IRES
        assert "mini-ires" in articles[1].lower()

    @pytest.mark.asyncio
    async def test_translation_preserves_domain_content(self) -> None:
        """L2: translation of real article preserves key domain terms.
        # SOURCE: Art. 1 D.L. 34/2019 — ammortamento beni strumentali
        """
        with patch(
            "codicecivico.nlp.translator._call_ollama",
            new_callable=AsyncMock,
            return_value=MOCK_LLM_RESPONSE_GOOD,
        ):
            result = await translate_article(REAL_ARTICLE_1)
            assert result is not None
            # The translation should reference the 30% from the original
            assert "30" in result.get("cosa_cambia", "")

    def test_parse_response_extracts_all_four_sections(self) -> None:
        """L2: well-formatted response yields exactly 4 non-empty sections.
        # SOURCE: Expected output format per Codice Civico design doc
        """
        result = _parse_llm_response(MOCK_LLM_RESPONSE_GOOD)
        non_empty = [k for k, v in result.items() if v]
        assert len(non_empty) == 4


# =========================================================================
# L3: Property-Based Tests (Hypothesis)
# =========================================================================


class TestL3PropertyBased:
    """L3: property-based tests for translator functions."""

    @given(st.text(min_size=0, max_size=500))
    @hsettings(max_examples=50)
    def test_build_prompt_always_returns_string(self, text: str) -> None:
        """For any input, _build_prompt returns a non-empty string."""
        result = _build_prompt(text)
        assert isinstance(result, str)
        assert len(result) > 0

    @given(st.text(min_size=0, max_size=1000))
    @hsettings(max_examples=50)
    def test_parse_response_always_returns_four_keys(self, text: str) -> None:
        """For any input, _parse_llm_response returns dict with exactly 4 keys."""
        result = _parse_llm_response(text)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"cosa_cambia", "chi_beneficia", "chi_perde", "prima_vs_dopo"}

    @given(st.text(min_size=0, max_size=2000))
    @hsettings(max_examples=50)
    def test_split_articles_returns_list(self, text: str) -> None:
        """For any input, split_into_articles returns a list."""
        result = split_into_articles(text)
        assert isinstance(result, list)

    @given(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N", "P", "Z"),
            ),
            min_size=10,
            max_size=500,
        ),
    )
    @hsettings(max_examples=30)
    def test_split_single_text_without_markers(self, text: str) -> None:
        """Text without 'Art.' markers yields at most 1 article."""
        # Filter out texts that accidentally contain 'Art.'
        if "Art." in text or "Articolo" in text:
            return
        result = split_into_articles(text)
        assert len(result) <= 1
