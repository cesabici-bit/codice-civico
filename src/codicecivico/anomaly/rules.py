"""Rule-based red flag detection for procurement contracts.

7 rules inspired by ANAC's own indicators + EU procurement best practices:
- SOURCE: ANAC Rapporto Annuale 2023 — indicatori di rischio
- SOURCE: EU Single Market Scoreboard — procurement indicators
- SOURCE: OECD "Preventing Corruption in Public Procurement" (2016)
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

# Thresholds (tunable, based on ANAC/EU benchmarks)
SPLIT_THRESHOLD_EUR = 40_000  # Under €40k = affidamento diretto allowed
SPLIT_LOOKBACK_DAYS = 90  # Same buyer+CPV within 90 days
LAST_MINUTE_DAYS = 15  # < 15 days between publication and deadline
SHORT_DURATION_DAYS = 30  # Contract duration < 30 days
PRICE_SPIKE_FACTOR = 3.0  # > 3x the CPV median = anomalous


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

    Detects when a buyer has multiple contracts with same CPV code, each just
    below the threshold that would require a competitive procedure.
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

    # Count contracts from same buyer with same CPV prefix (first 5 digits)
    cpv_prefix = str(cpv)[:5]
    similar = [
        c for c in buyer_contracts
        if (
            str(c.get("cpv_code", ""))[:5] == cpv_prefix
            and c.get("buyer_cf") == buyer_cf
            and _to_float(c.get("amount_original") or c.get("amount_awarded"))
            < SPLIT_THRESHOLD_EUR
        )
    ]

    if len(similar) >= 3:
        total = sum(
            _to_float(c.get("amount_original") or c.get("amount_awarded"))
            for c in similar
        )
        return RedFlag(
            flag_type=FlagType.SPLIT_CONTRACTS,
            severity=Severity.HIGH if total > SPLIT_THRESHOLD_EUR * 2 else Severity.MEDIUM,
            details={
                "n_similar_contracts": len(similar),
                "total_amount": round(total, 2),
                "cpv_prefix": cpv_prefix,
                "threshold": SPLIT_THRESHOLD_EUR,
            },
        )
    return None


def check_price_spike(
    contract: dict[str, object],
    cpv_median: float | None = None,
) -> RedFlag | None:
    """PRICE_SPIKE: Contract amount anomalously high for its CPV code.

    Compares amount to the median for the same CPV category.
    SOURCE: OECD "Preventing Corruption in Public Procurement" — price benchmarking
    """
    if cpv_median is None or cpv_median <= 0:
        return None

    amount = _to_float(contract.get("amount_original") or contract.get("amount_awarded"))
    if amount <= 0:
        return None

    ratio = amount / cpv_median
    if ratio > PRICE_SPIKE_FACTOR:
        severity = Severity.HIGH if ratio > 10 else Severity.MEDIUM
        return RedFlag(
            flag_type=FlagType.PRICE_SPIKE,
            severity=severity,
            details={
                "amount": amount,
                "cpv_median": round(cpv_median, 2),
                "ratio": round(ratio, 2),
                "threshold_factor": PRICE_SPIKE_FACTOR,
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
    cpv_median: float | None = None,
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
        check_price_spike(contract, cpv_median),
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
