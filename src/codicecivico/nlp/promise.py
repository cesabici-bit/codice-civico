"""Promise extraction and classification from political speeches.

Pipeline:
1. Sentence splitting (spaCy it_core_news_lg / regex fallback)
2. Claim detection (Italian commitment verb heuristics)
3. Topic classification (keyword-based)
4. Specificity scoring (rule-based 0-1)

Architecture follows anomaly/rules.py pattern: pure functions, dict I/O.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from codicecivico.nlp.ner import extract_entities, split_sentences

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Italian commitment verbs and patterns (lemmatized / surface forms)
COMMITMENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bci impegniamo\b", re.IGNORECASE),
    re.compile(r"\bmi impegno\b", re.IGNORECASE),
    re.compile(r"\bpromettiamo\b", re.IGNORECASE),
    re.compile(r"\bprometto\b", re.IGNORECASE),
    re.compile(r"\bvogliamo\b", re.IGNORECASE),
    re.compile(r"\bintendiamo\b", re.IGNORECASE),
    re.compile(r"\bproponiamo\b", re.IGNORECASE),
    re.compile(r"\bdobbiamo\b", re.IGNORECASE),
    re.compile(r"\bbisogna\b", re.IGNORECASE),
    re.compile(r"\boccorre\b", re.IGNORECASE),
    re.compile(r"\bè necessario\b", re.IGNORECASE),
    re.compile(r"\bserve\b", re.IGNORECASE),
    re.compile(r"\bil governo (?:intende|vuole|si impegna)\b", re.IGNORECASE),
    re.compile(r"\bla maggioranza (?:intende|vuole|si impegna)\b", re.IGNORECASE),
]

# Future tense conjugation (1st plural -remo, 3rd sing -rà, 3rd plur -ranno)
# Only match actual verb-like words (min 5 chars to avoid noise)
FUTURE_TENSE_RE = re.compile(
    r"\b\w{3,}(?:remo|rete|rà|ranno)\b",
    re.IGNORECASE,
)

# Vague language patterns (reduce confidence / specificity)
VAGUE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bfaremo (?:di tutto|il possibile)\b", re.IGNORECASE),
    re.compile(r"\bin qualche modo\b", re.IGNORECASE),
    re.compile(r"\bprima o poi\b", re.IGNORECASE),
    re.compile(r"\bsperiamo\b", re.IGNORECASE),
    re.compile(r"\bcercheremo\b", re.IGNORECASE),
    re.compile(r"\bse possibile\b", re.IGNORECASE),
    re.compile(r"\bcompatibilmente con\b", re.IGNORECASE),
]

# Question pattern — exclude questions from promises
QUESTION_RE = re.compile(r"\?\s*$")

# Procedural patterns — exclude procedural statements
PROCEDURAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bla seduta è\b", re.IGNORECASE),
    re.compile(r"\bdichiaro (?:aperta|chiusa)\b", re.IGNORECASE),
    re.compile(r"\bpassiamo (?:ora |all')\b", re.IGNORECASE),
    re.compile(r"\bordine dei lavori\b", re.IGNORECASE),
    re.compile(r"\bchiedo di intervenire\b", re.IGNORECASE),
    re.compile(r"\bè iscritto a parlare\b", re.IGNORECASE),
    re.compile(r"\bha facoltà di\b", re.IGNORECASE),
    re.compile(r"\bmetto ai voti\b", re.IGNORECASE),
]

# Date patterns (e.g. "entro il 2027", "dal 2025", "15 marzo")
DATE_RE = re.compile(
    r"\b(?:entro|dal|a partire dal?|nel)\s+(?:il\s+)?\d{4}\b"
    r"|\b\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno"
    r"|luglio|agosto|settembre|ottobre|novembre|dicembre)\b",
    re.IGNORECASE,
)

# Number patterns (e.g. "5 miliardi", "1.000 euro", "28.000")
NUMBER_RE = re.compile(
    r"\b\d[\d.,]*\s*(?:miliardi|milioni|mila|euro|%|per cento)\b"
    r"|\b\d{1,3}(?:\.\d{3})+\b",
    re.IGNORECASE,
)

# Specific action verbs (beyond generic future tense)
SPECIFIC_ACTION_VERBS = re.compile(
    r"\b(?:abolir|riform|costruir|istituir|finanziar|stanzi|assum|digitaliz"
    r"|dimezz|raddoppi|eliminar|introdur|approv|ratific)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Topic Classification
# ---------------------------------------------------------------------------

# 13 topics with keyword dictionaries
# SOURCE: Taxonomy based on Camera dei Deputati commission categories
# (dati.camera.it — 14 standing committees)
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "economia": [
        "tasse", "fisco", "fiscale", "irpef", "iva", "bilancio", "debito",
        "deficit", "pil", "inflazione", "banca", "credito", "finanz",
        "economic", "imposta", "aliquot", "manovra", "spread",
    ],
    "sanita": [
        "sanità", "sanitari", "ospedal", "medic", "salute", "vaccin",
        "farmac", "ssn", "pronto soccorso", "infermier", "pazient",
    ],
    "istruzione": [
        "scuol", "istruzion", "università", "docent", "insegnant",
        "studenti", "formazione", "didattic", "ricerca", "laurea",
    ],
    "giustizia": [
        "giustizia", "giudic", "tribunal", "process", "magistrat",
        "penale", "civile", "carceri", "detenuti", "riforma della giustizia",
        "prescrizione", "reato",
    ],
    "sicurezza": [
        "sicurezza", "polizia", "carabinieri", "forze dell'ordine",
        "criminalità", "mafi", "terrorismo", "difesa", "militar",
    ],
    "ambiente": [
        "ambiente", "ambient", "clima", "climatico", "rinnovabil",
        "energi", "emissioni", "sostenibil", "ricicl", "inquinament",
        "transizione ecologic", "verde",
    ],
    "lavoro": [
        "lavoro", "lavorator", "occupazione", "disoccupazione", "stipendi",
        "salario", "contratt", "pensioni", "previdenz", "inps", "inail",
        "assunzion", "impiego",
    ],
    "immigrazione": [
        "immigra", "migrant", "profughi", "rifugiat", "accoglienza",
        "frontiera", "sbarchi", "asilo", "stranieri", "integrazione",
    ],
    "esteri": [
        "esteri", "internazional", "europa", "nato", "onu", "diplomat",
        "cooperazione", "missioni all'estero", "trattato", "g7", "g20",
    ],
    "infrastrutture": [
        "infrastruttur", "strad", "autostrad", "ferrovi", "ponte",
        "tunnel", "trasport", "porto", "aeroporto", "alta velocità",
        "mezzo pubblico", "mobilità",
    ],
    "welfare": [
        "welfare", "sociale", "assistenza", "reddito di", "assegno",
        "disabilità", "anziani", "famiglia", "natalità", "bonus",
        "povertà", "inclusione",
    ],
    "digitale": [
        "digital", "tecnologi", "innovazione", "startup", "intelligenza artificiale",
        "cybersec", "broadband", "fibra", "spid", "pa digitale",
    ],
}


@dataclass
class ClaimResult:
    """Result of claim detection on a single sentence."""

    sentence: str
    is_promise: bool
    trigger_pattern: str  # The pattern that matched
    raw_confidence: float  # 0-1, based on strength of match


@dataclass
class PromiseResult:
    """A fully extracted and classified promise."""

    sentence: str
    topic: str
    topic_confidence: float
    specificity_score: float
    confidence: float


# ---------------------------------------------------------------------------
# Claim Detection
# ---------------------------------------------------------------------------


def detect_claims(sentences: list[str]) -> list[ClaimResult]:
    """Detect political promises/commitments in a list of sentences.

    Uses Italian commitment verb heuristics + future tense patterns.
    Excludes questions and procedural statements.

    Returns list of ClaimResult for ALL sentences (is_promise=True/False).
    """
    results: list[ClaimResult] = []

    for sent in sentences:
        # Skip questions
        if QUESTION_RE.search(sent):
            results.append(ClaimResult(sent, False, "question", 0.0))
            continue

        # Skip procedural statements
        if any(p.search(sent) for p in PROCEDURAL_PATTERNS):
            results.append(ClaimResult(sent, False, "procedural", 0.0))
            continue

        # Check commitment patterns (high confidence)
        matched_pattern = ""
        confidence = 0.0

        for pattern in COMMITMENT_PATTERNS:
            if pattern.search(sent):
                matched_pattern = pattern.pattern
                confidence = 0.85
                break

        # Check future tense (medium confidence)
        if not matched_pattern:
            future_match = FUTURE_TENSE_RE.search(sent)
            if future_match:
                matched_pattern = f"future:{future_match.group()}"
                confidence = 0.6

        # No match
        if not matched_pattern:
            results.append(ClaimResult(sent, False, "none", 0.0))
            continue

        # Apply vagueness penalty
        vague_count = sum(1 for p in VAGUE_PATTERNS if p.search(sent))
        if vague_count > 0:
            confidence -= 0.15 * vague_count
            confidence = max(confidence, 0.1)

        is_promise = confidence >= 0.3
        results.append(ClaimResult(sent, is_promise, matched_pattern, round(confidence, 2)))

    return results


# ---------------------------------------------------------------------------
# Topic Classification
# ---------------------------------------------------------------------------


def classify_topic(sentence: str) -> tuple[str, float]:
    """Classify a promise sentence into one of 13 policy topics.

    Returns (topic_name, confidence). Uses keyword matching.
    Falls back to 'altro' if no topic matches.
    """
    sentence_lower = sentence.lower()
    scores: dict[str, int] = {}

    for topic, keywords in TOPIC_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in sentence_lower)
        if count > 0:
            scores[topic] = count

    if not scores:
        return ("altro", 0.3)

    best_topic = max(scores, key=scores.get)  # type: ignore[arg-type]
    # Confidence based on how many keywords matched vs total
    total_keywords = len(TOPIC_KEYWORDS[best_topic])
    confidence = min(0.5 + (scores[best_topic] / total_keywords) * 2.0, 1.0)

    return (best_topic, round(confidence, 2))


# ---------------------------------------------------------------------------
# Specificity Scoring
# ---------------------------------------------------------------------------


def score_specificity(sentence: str) -> float:
    """Score how specific a promise is (0.0 = vague, 1.0 = highly specific).

    Additive heuristic:
    - Contains numbers: +0.2
    - Contains dates: +0.2
    - Contains named entities (NER): +0.2
    - Sentence length > 20 words: +0.1
    - Specific action verbs: +0.1
    - Vague language: -0.2 per pattern
    """
    score = 0.2  # Base score (it was detected as a promise)

    # Numbers
    if NUMBER_RE.search(sentence):
        score += 0.2

    # Dates
    if DATE_RE.search(sentence):
        score += 0.2

    # Named entities (try spaCy, skip if unavailable)
    entities = extract_entities(sentence)
    if entities:
        score += 0.2

    # Sentence length
    word_count = len(sentence.split())
    if word_count > 20:
        score += 0.1

    # Specific action verbs
    if SPECIFIC_ACTION_VERBS.search(sentence):
        score += 0.1

    # Vagueness penalty
    vague_count = sum(1 for p in VAGUE_PATTERNS if p.search(sentence))
    score -= 0.2 * vague_count

    return round(max(0.0, min(1.0, score)), 2)


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------


async def extract_promises(text: str) -> list[dict[str, object]]:
    """Extract committal statements from a political speech.

    Pipeline:
    1. Sentence splitting (spaCy it_core_news_lg / regex fallback)
    2. Claim detection (Italian commitment verb heuristics)
    3. Topic classification (keyword-based)
    4. Specificity scoring (0-1)

    Returns list of dicts: {sentence, topic, topic_confidence,
    specificity_score, confidence}
    """
    if not text or not text.strip():
        return []

    # Step 1: Split into sentences
    sentences = split_sentences(text)

    # Step 2: Detect claims
    claims = detect_claims(sentences)

    # Step 3-4: Classify and score each detected promise
    promises: list[dict[str, object]] = []
    for claim in claims:
        if not claim.is_promise:
            continue

        topic, topic_conf = classify_topic(claim.sentence)
        specificity = score_specificity(claim.sentence)

        promises.append({
            "sentence": claim.sentence,
            "topic": topic,
            "topic_confidence": topic_conf,
            "specificity_score": specificity,
            "confidence": claim.raw_confidence,
        })

    logger.info(
        "Extracted %d promises from %d sentences", len(promises), len(sentences)
    )
    return promises
