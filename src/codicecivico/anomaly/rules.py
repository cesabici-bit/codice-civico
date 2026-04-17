"""Rule-based red flag detection for procurement contracts.

7 rules inspired by ANAC's own indicators + EU procurement best practices:
- SOURCE: ANAC Rapporto Annuale 2023 — indicatori di rischio
- SOURCE: EU Single Market Scoreboard — procurement indicators
- SOURCE: OECD "Preventing Corruption in Public Procurement" (2016)
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

# Thresholds (calibrated empirically against ANAC 2025-12 dataset)
SPLIT_THRESHOLD_EUR = 40_000  # Under €40k = affidamento diretto allowed
SPLIT_LOOKBACK_DAYS = 90  # Same buyer+CPV within 90 days
SPLIT_MIN_SIMILAR = 5  # N contratti simili per flaggare (era 3, troppo permissivo)
# Filtro A: diversità fornitori. Se ≥60% dei contratti nel cluster ha fornitori
# DIVERSI, non è frazionamento artificioso (procurement operativo normale).
# Il vero frazionamento ha tipicamente pochi fornitori ricorrenti sui lotti spezzati.
SPLIT_SUPPLIER_DIVERSITY_MAX = 0.6
# Filtro B: cluster "giganti" (>20) su CPV-8 stretto = procurement continuo di
# grande PA centralizzata, non frazionamento. Declassato a LOW severity.
SPLIT_GIANT_CLUSTER_SIZE = 20
LAST_MINUTE_DAYS = 15  # < 15 days between publication and deadline
SHORT_DURATION_DAYS = 30  # Contract duration < 30 days
# PRICE_SPIKE: z-score on log(amount) per CPV-8 bucket.
# Procurement amounts are log-normal — a flat ratio vs median over-flags
# legitimate long-tail contracts. 3 sigma ≈ p99.87 of a normal distribution.
PRICE_SPIKE_Z_THRESHOLD = 3.0
PRICE_SPIKE_MIN_SAMPLES = 30  # need at least 30 contracts to fit (mu, sigma)


class FlagType(str, Enum):
    """Procurement anomaly flag types."""

    SPLIT_CONTRACTS = "SPLIT_CONTRACTS"
    SINGLE_BID = "SINGLE_BID"
    LAST_MINUTE = "LAST_MINUTE"
    PRICE_SPIKE = "PRICE_SPIKE"
    REVOLVING_DOOR = "REVOLVING_DOOR"
    SHORT_DURATION = "SHORT_DURATION"
    EXTENSION_ABUSE = "EXTENSION_ABUSE"


class Severity(str, Enum):
    """Anomaly severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RedFlag:
    """A detected anomaly flag."""

    flag_type: FlagType
    severity: Severity
    details: dict[str, object]


# ---------------------------------------------------------------------------
# Individual rule checks
# ---------------------------------------------------------------------------


def check_single_bid(contract: dict[str, object]) -> RedFlag | None:
    """SINGLE_BID: Only one bidder submitted an offer.

    A single bid is the strongest single indicator of reduced competition.
    SOURCE: EU Single Market Scoreboard — single bidding rate > 30% = warning
    """
    n_bids = contract.get("n_bids")
    if n_bids is not None and n_bids == 1:
        amount = contract.get("amount_original") or contract.get("amount_awarded")
        severity = Severity.HIGH if _to_float(amount) > 150_000 else Severity.MEDIUM
        return RedFlag(
            flag_type=FlagType.SINGLE_BID,
            severity=severity,
            details={"n_bids": 1, "amount": _safe_str(amount)},
        )
    return None


def check_last_minute(contract: dict[str, object]) -> RedFlag | None:
    """LAST_MINUTE: Very short time between publication and offer deadline.

    Short deadlines limit competition. EU directives set minimums (30-52 days
    for open procedures). Below 15 days is a red flag.
    SOURCE: EU Directive 2014/24/EU Art. 27-28 — minimum time limits
    """
    raw_duration = contract.get("contract_duration_days")
    duration_days = int(str(raw_duration)) if raw_duration is not None else None
    if duration_days is not None and 0 < duration_days < LAST_MINUTE_DAYS:
        severity = Severity.HIGH if duration_days < 7 else Severity.MEDIUM
        return RedFlag(
            flag_type=FlagType.LAST_MINUTE,
            severity=severity,
            details={
                "days_to_deadline": duration_days,
                "threshold": LAST_MINUTE_DAYS,
            },
        )
    return None


def check_short_duration(contract: dict[str, object]) -> RedFlag | None:
    """SHORT_DURATION: Contract executed in abnormally short time.

    Very short execution times may indicate pre-arranged outcomes.
    Only relevant for contracts > €40k (small ones can legitimately be fast).
    """
    raw_duration = contract.get("contract_duration_days")
    duration_days = int(str(raw_duration)) if raw_duration is not None else None
    amount = _to_float(contract.get("amount_original") or contract.get("amount_awarded"))
    if (
        duration_days is not None
        and 0 < duration_days < SHORT_DURATION_DAYS
        and amount > SPLIT_THRESHOLD_EUR
    ):
        return RedFlag(
            flag_type=FlagType.SHORT_DURATION,
            severity=Severity.LOW,
            details={
                "duration_days": duration_days,
                "threshold": SHORT_DURATION_DAYS,
                "amount": amount,
            },
        )
    return None


def check_split_contracts(
    contract: dict[str, object],
    buyer_contracts: list[dict[str, object]] | None = None,
) -> RedFlag | None:
    """SPLIT_CONTRACTS: Buyer splits a larger procurement into pieces < €40k.

    Detects when a buyer has multiple sub-threshold contracts with same full
    CPV-8 code within a 90-day rolling window — the pattern of artificial
    fragmentation to avoid competitive procedures.

    Calibrazione (vs ANAC 2025-12, 170k contratti):
    - CPV[:8] (era CPV[:5]): il prefisso-5 aggregava famiglie merceologiche
      eterogenee; enti grandi con procurement ordinario venivano flaggati.
    - Finestra 90gg (era: nessun filtro temporale — bug): richiesto pattern
      di frazionamento temporalmente clustered, non "3+ sub-soglia nel 2025".
    - n >= 5 (era n >= 3): 3 affidamenti diretti same-CPV8 in 90gg sono
      ordinary procurement per enti medi; 5+ alza significativamente il prior.

    SOURCE: ANAC Rapporto 2023 — frazionamento artificioso degli appalti
    """
    if buyer_contracts is None:
        return None

    amount = _to_float(contract.get("amount_original") or contract.get("amount_awarded"))
    if amount >= SPLIT_THRESHOLD_EUR:
        return None  # Not a sub-threshold contract

    cpv = contract.get("cpv_code", "")
    buyer_cf = contract.get("buyer_cf", "")
    if not cpv or not buyer_cf:
        return None

    cpv_full = _cpv_main(cpv)
    pub_date = _as_date(contract.get("publication_date"))
    window_start = pub_date - timedelta(days=SPLIT_LOOKBACK_DAYS) if pub_date else None
    window_end = pub_date + timedelta(days=SPLIT_LOOKBACK_DAYS) if pub_date else None

    similar = []
    for c in buyer_contracts:
        if _cpv_main(c.get("cpv_code", "")) != cpv_full:
            continue
        if c.get("buyer_cf") != buyer_cf:
            continue
        c_amt = _to_float(c.get("amount_original") or c.get("amount_awarded"))
        if c_amt >= SPLIT_THRESHOLD_EUR:
            continue
        # Rolling 90-day window around the contract's publication date.
        # If either date missing, fall back to including the sibling (conservative).
        c_pub = _as_date(c.get("publication_date"))
        if window_start and window_end and c_pub:
            if not (window_start <= c_pub <= window_end):
                continue
        similar.append(c)

    if len(similar) < SPLIT_MIN_SIMILAR:
        return None

    # Filtro A: supplier diversity. Cluster con fornitori molto diversificati
    # = procurement ordinario, non frazionamento artificioso.
    cluster_contracts = [*similar, contract]
    suppliers = {
        str(c.get("supplier_cf")).strip()
        for c in cluster_contracts
        if c.get("supplier_cf")
    }
    n_with_supplier = sum(
        1 for c in cluster_contracts if c.get("supplier_cf")
    )
    if n_with_supplier >= SPLIT_MIN_SIMILAR:
        diversity = len(suppliers) / n_with_supplier
        if diversity >= SPLIT_SUPPLIER_DIVERSITY_MAX:
            return None
    else:
        diversity = None  # Troppi supplier mancanti per giudicare — procedi

    total = sum(
        _to_float(c.get("amount_original") or c.get("amount_awarded"))
        for c in similar
    )

    # Filtro B: cluster giganti (>20) = procurement continuo, non splitting.
    # Declassato a LOW (contribuisce poco al risk_score ma resta visibile).
    if len(similar) >= SPLIT_GIANT_CLUSTER_SIZE:
        severity = Severity.LOW
    elif total > SPLIT_THRESHOLD_EUR * 2:
        severity = Severity.HIGH
    else:
        severity = Severity.MEDIUM

    return RedFlag(
        flag_type=FlagType.SPLIT_CONTRACTS,
        severity=severity,
        details={
            "n_similar_contracts": len(similar),
            "total_amount": round(total, 2),
            "cpv_full": cpv_full,
            "window_days": SPLIT_LOOKBACK_DAYS,
            "threshold": SPLIT_THRESHOLD_EUR,
            "n_unique_suppliers": len(suppliers),
            "supplier_diversity": (
                round(diversity, 3) if diversity is not None else None
            ),
        },
    )


def check_price_spike(
    contract: dict[str, object],
    cpv_log_stats: tuple[float, float, int] | None = None,
) -> RedFlag | None:
    """PRICE_SPIKE: Contract amount statistically anomalous for its CPV-8 bucket.

    Procurement amounts within a CPV-8 code follow a log-normal distribution.
    Flag if log(amount) > mu + 3*sigma (≈ p99.87 of the log-normal), computed
    over same CPV-8 bucket from the current dataset.

    Args:
        cpv_log_stats: (mu, sigma, n) of log(amount) for this contract's CPV-8
                       bucket. None = bucket too small or missing, skip.

    Calibrazione (vs ANAC 2025-12, 170k contratti):
    - Metrica: z-score su log(amount) per CPV-8 (era: amount > 3x median su CPV-5).
      La distribuzione degli importi è log-normale con p95/mediana fino a 29.000x
      per alcuni CPV — 3x mediana corrispondeva al ~p60, generando il 22% flag rate.
    - Threshold z=3: ~p99.87 (one-tailed) — riduce drasticamente falsi positivi
      mantenendo rilevazione di outlier reali.
    - Min 30 samples per bucket: sotto tale soglia (mu, sigma) non sono affidabili.

    SOURCE: OECD "Preventing Corruption in Public Procurement" — price benchmarking
    """
    if cpv_log_stats is None:
        return None
    mu, sigma, n_samples = cpv_log_stats
    if n_samples < PRICE_SPIKE_MIN_SAMPLES or sigma <= 0:
        return None

    amount = _to_float(contract.get("amount_original") or contract.get("amount_awarded"))
    if amount <= 0:
        return None

    log_amt = math.log(amount)
    z = (log_amt - mu) / sigma
    if z > PRICE_SPIKE_Z_THRESHOLD:
        severity = Severity.HIGH if z > 5.0 else Severity.MEDIUM
        return RedFlag(
            flag_type=FlagType.PRICE_SPIKE,
            severity=severity,
            details={
                "amount": amount,
                "cpv_geometric_mean": round(math.exp(mu), 2),
                "cpv_log_mean": round(mu, 3),
                "cpv_log_stddev": round(sigma, 3),
                "z_score": round(z, 2),
                "cpv_sample_size": n_samples,
                "threshold_z": PRICE_SPIKE_Z_THRESHOLD,
            },
        )
    return None


def check_revolving_door(
    contract: dict[str, object],
    supplier_win_count: int | None = None,
    buyer_total_contracts: int | None = None,
) -> RedFlag | None:
    """REVOLVING_DOOR: Same supplier repeatedly wins from same buyer.

    When one supplier captures > 50% of a buyer's contracts, it suggests
    reduced competition or collusion.
    SOURCE: ANAC Rapporto 2023 — concentrazione degli aggiudicatari
    """
    if supplier_win_count is None or buyer_total_contracts is None:
        return None
    if buyer_total_contracts < 5:
        return None  # Too few contracts to judge

    ratio = supplier_win_count / buyer_total_contracts
    if ratio > 0.5:
        severity = Severity.HIGH if ratio > 0.75 else Severity.MEDIUM
        return RedFlag(
            flag_type=FlagType.REVOLVING_DOOR,
            severity=severity,
            details={
                "supplier_wins": supplier_win_count,
                "buyer_total": buyer_total_contracts,
                "win_ratio": round(ratio, 3),
            },
        )
    return None


def check_extension_abuse(
    contract: dict[str, object],
    extensions_count: int | None = None,
) -> RedFlag | None:
    """EXTENSION_ABUSE: Contract repeatedly extended beyond original scope.

    Multiple extensions indicate poor planning or circumvention of
    competitive procedures. >=2 extensions = red flag.
    """
    if extensions_count is not None and extensions_count >= 2:
        severity = Severity.HIGH if extensions_count >= 4 else Severity.MEDIUM
        return RedFlag(
            flag_type=FlagType.EXTENSION_ABUSE,
            severity=severity,
            details={"extensions_count": extensions_count},
        )
    return None


# ---------------------------------------------------------------------------
# Aggregate checker
# ---------------------------------------------------------------------------


def check_all_rules(
    contract: dict[str, object],
    *,
    buyer_contracts: list[dict[str, object]] | None = None,
    cpv_log_stats: tuple[float, float, int] | None = None,
    supplier_win_count: int | None = None,
    buyer_total_contracts: int | None = None,
    extensions_count: int | None = None,
) -> list[RedFlag]:
    """Run all 7 rule-based checks on a contract.

    Context-dependent rules (split, price_spike, revolving_door, extension)
    require optional extra parameters. Without context, only standalone rules
    (single_bid, last_minute, short_duration) will fire.

    Returns list of triggered RedFlag instances.
    """
    flags: list[RedFlag] = []
    checkers = [
        check_single_bid(contract),
        check_last_minute(contract),
        check_short_duration(contract),
        check_split_contracts(contract, buyer_contracts),
        check_price_spike(contract, cpv_log_stats),
        check_revolving_door(contract, supplier_win_count, buyer_total_contracts),
        check_extension_abuse(contract, extensions_count),
    ]
    for flag in checkers:
        if flag is not None:
            flags.append(flag)
    return flags


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_float(value: object) -> float:
    """Safely convert a value to float."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return 0.0


def _safe_str(value: object) -> str:
    """Convert value to string for details dict."""
    if value is None:
        return "N/A"
    return str(value)


def _cpv_main(cpv: object) -> str:
    """Extract the 8-digit main CPV code (strip check-digit suffix like '-8')."""
    if not cpv:
        return ""
    s = str(cpv).split("-", 1)[0].strip()
    return s[:8]


def _as_date(value: object) -> date | None:
    """Coerce a value to date, accepting date, datetime, or ISO string."""
    if value is None:
        return None
    if isinstance(value, date):
        # datetime is subclass of date — date() normalizes both
        return value if type(value) is date else value.date()  # type: ignore[attr-defined]
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None
