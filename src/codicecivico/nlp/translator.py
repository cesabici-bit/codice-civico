"""Legislative text translation to plain Italian via LLM.

Uses Ollama (local LLM) with graceful fallback when unavailable.
Endpoint: POST /api/generate (non-streaming).
Source: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import httpx

from codicecivico.config import settings

logger = logging.getLogger(__name__)

# Ollama API timeout: generous because local LLM can be slow on first load
_OLLAMA_TIMEOUT = httpx.Timeout(connect=5.0, read=120.0, write=5.0, pool=5.0)

# Section markers in the LLM response
_SECTION_KEYS = ("cosa_cambia", "chi_beneficia", "chi_perde", "prima_vs_dopo")
_SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "cosa_cambia": re.compile(
        r"(?:1[\.\)]\s*)?COSA\s+CAMBIA\s*:\s*(.*?)(?=(?:\d[\.\)]\s*)?(?:CHI\s+BENEFICIA|CHI\s+PERDE|PRIMA\s+vs|$))",
        re.IGNORECASE | re.DOTALL,
    ),
    "chi_beneficia": re.compile(
        r"(?:2[\.\)]\s*)?CHI\s+BENEFICIA\s*:\s*(.*?)(?=(?:\d[\.\)]\s*)?(?:CHI\s+PERDE|PRIMA\s+vs|$))",
        re.IGNORECASE | re.DOTALL,
    ),
    "chi_perde": re.compile(
        r"(?:3[\.\)]\s*)?CHI\s+PERDE\s*:\s*(.*?)(?=(?:\d[\.\)]\s*)?(?:PRIMA\s+vs|$))",
        re.IGNORECASE | re.DOTALL,
    ),
    "prima_vs_dopo": re.compile(
        r"(?:4[\.\)]\s*)?PRIMA\s+vs\s+DOPO\s*:\s*(.*)",
        re.IGNORECASE | re.DOTALL,
    ),
}


async def check_ollama_available() -> bool:
    """Check if Ollama server is reachable."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=3.0)) as client:
            resp = await client.get(f"{settings.ollama_url}/api/version")
            return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def _build_prompt(article_text: str) -> str:
    """Build the translation prompt for the LLM."""
    return (
        "Sei un giurista esperto che spiega le leggi ai cittadini comuni. "
        "Riscrivi il seguente articolo di legge in linguaggio semplice e chiaro.\n\n"
        "Rispondi ESATTAMENTE con questo formato (mantieni le intestazioni):\n\n"
        "COSA CAMBIA: [spiegazione in 2-3 frasi semplici di cosa introduce o modifica "
        "questa norma]\n\n"
        "CHI BENEFICIA: [elenco dei gruppi di persone che traggono vantaggio]\n\n"
        "CHI PERDE: [elenco dei gruppi di persone svantaggiate, oppure 'Nessuno in "
        "modo diretto' se non applicabile]\n\n"
        "PRIMA vs DOPO: [confronto sintetico tra la situazione precedente e quella "
        "nuova]\n\n"
        f"Articolo di legge:\n\n{article_text}"
    )


def _parse_llm_response(raw_text: str) -> dict[str, str]:
    """Parse structured sections from the LLM response text.

    Returns a dict with keys: cosa_cambia, chi_beneficia, chi_perde, prima_vs_dopo.
    Missing sections get an empty string.
    """
    result: dict[str, str] = {}
    for key, pattern in _SECTION_PATTERNS.items():
        match = pattern.search(raw_text)
        result[key] = match.group(1).strip() if match else ""
    return result


async def _call_ollama(prompt: str) -> str | None:
    """Call Ollama /api/generate and return the response text.

    Returns None if Ollama is unreachable or returns an error.
    """
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 1024,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.ollama_url}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            result: str = data.get("response", "")
            return result
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.warning("Ollama unreachable: %s", exc)
        return None
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Ollama error %s: %s", exc.response.status_code, exc.response.text[:200],
        )
        return None


async def translate_article(article_text: str) -> dict[str, str] | None:
    """Translate a single law article to plain Italian via Ollama.

    Returns dict with keys: cosa_cambia, chi_beneficia, chi_perde, prima_vs_dopo.
    Returns None if Ollama is unavailable (graceful fallback).
    """
    if not article_text or not article_text.strip():
        return None

    prompt = _build_prompt(article_text)
    raw = await _call_ollama(prompt)
    if raw is None:
        return None

    parsed = _parse_llm_response(raw)

    # If no sections were extracted, return the raw text as cosa_cambia
    if not any(parsed.values()):
        parsed["cosa_cambia"] = raw.strip()

    return parsed


async def translate_law(
    full_text: str,
    *,
    max_articles: int | None = None,
) -> dict[str, object] | None:
    """Translate an entire law text (split into articles) to plain Italian.

    Returns a dict with:
        - articles: list of {article_number, original, translation}
        - summary: overall summary (first article's cosa_cambia if available)
        - translated_at: ISO timestamp

    Returns None if Ollama is unavailable.
    """
    if not full_text or not full_text.strip():
        return None

    # Check Ollama availability before starting
    if not await check_ollama_available():
        logger.info("Ollama not available — skipping translation")
        return None

    articles = split_into_articles(full_text)
    if max_articles:
        articles = articles[:max_articles]

    translated_articles: list[dict[str, str | int | dict[str, str]]] = []
    for i, article_text in enumerate(articles, 1):
        translation = await translate_article(article_text)
        if translation is None:
            # Ollama went down mid-translation
            logger.warning("Ollama became unavailable at article %d", i)
            break
        translated_articles.append({
            "article_number": i,
            "original": article_text,
            "translation": translation,
        })

    if not translated_articles:
        return None

    # Build summary from first article
    first_translation = translated_articles[0].get("translation", {})
    summary = (
        first_translation.get("cosa_cambia", "")
        if isinstance(first_translation, dict)
        else ""
    )

    return {
        "articles": translated_articles,
        "summary": summary,
        "translated_at": datetime.now(timezone.utc).isoformat(),
    }


def split_into_articles(text: str) -> list[str]:
    """Split a law full text into individual articles.

    Handles common Italian legislative formatting:
    - 'Art. 1', 'Art. 1.', 'Articolo 1', 'ART. 1'
    - 'Art. 1-bis', 'Art. 1-ter'

    If no article markers are found, returns the full text as a single item.
    """
    # Pattern: "Art." or "Articolo" followed by number (and optional -bis/-ter etc.)
    article_pattern = re.compile(
        r"(?:^|\n)\s*(?:Art(?:icolo)?\.?\s+\d+(?:-\w+)?\.?)",
        re.IGNORECASE,
    )

    splits = list(article_pattern.finditer(text))
    if not splits:
        return [text.strip()] if text.strip() else []

    articles: list[str] = []
    for i, match in enumerate(splits):
        start = match.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            articles.append(chunk)

    return articles
