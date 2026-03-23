"""Legislative text translation to plain Italian via LLM."""



async def translate_article(article_text: str) -> dict[str, str] | None:
    """Translate a law article to plain Italian via Ollama/LLaMAntino.

    Returns dict with keys: cosa_cambia, chi_beneficia, chi_perde, prima_vs_dopo.
    Returns None if Ollama is unavailable (graceful fallback).
    """
    raise NotImplementedError("Legislative translation not yet implemented (F5)")


def _build_prompt(article_text: str) -> str:
    """Build the translation prompt for the LLM."""
    return (
        "Sei un giurista che spiega le leggi ai cittadini. "
        "Riscrivi questo articolo di legge in linguaggio semplice.\n"
        "Per ogni articolo rispondi con:\n"
        "1. COSA CAMBIA: [spiegazione in 2-3 frasi semplici]\n"
        "2. CHI BENEFICIA: [gruppi di persone]\n"
        "3. CHI PERDE: [gruppi di persone, se applicabile]\n"
        "4. PRIMA vs DOPO: [confronto sintetico]\n\n"
        f"Articolo:\n{article_text}"
    )
