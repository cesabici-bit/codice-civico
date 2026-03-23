"""Composite risk scorer combining rule-based and ML anomaly scores.

Scoring formula:
  risk_score = (rule_score * RULE_WEIGHT) + (ml_score * ML_WEIGHT)

Rule score: sum of severity weights for each triggered flag.
ML score: normalized anomaly score from IsolationForest.

Final score clamped to [0, 100].
"""

from codicecivico.anomaly.rules import RedFlag, Severity

# Weights for composite score
RULE_WEIGHT = 0.6  # 60% rules, 40% ML
ML_WEIGHT = 0.4

# Severity points (contribute to rule_score out of 100)
SEVERITY_POINTS: dict[Severity, float] = {
    Severity.LOW: 10.0,
    Severity.MEDIUM: 25.0,
    Severity.HIGH: 40.0,
}

# Max rule score before clamping (a contract with 3 HIGH flags = 120 → capped)
MAX_RULE_RAW = 100.0


def compute_risk_score(
    rule_flags: list[RedFlag],
    ml_anomaly_score: float = 0.0,
) -> float:
    """Compute composite risk score (0-100).

    Args:
        rule_flags: List of triggered RedFlag instances.
        ml_anomaly_score: Normalized ML score in [0, 1] range.

    Returns:
        Risk score in [0, 100] range.
        Contracts > 70 should be surfaced in the dashboard.
    """
    # Rule component
    rule_raw = sum(SEVERITY_POINTS.get(f.severity, 0.0) for f in rule_flags)
    rule_component = min(rule_raw, MAX_RULE_RAW)

    # ML component (scale to 0-100)
    ml_component = max(0.0, min(1.0, ml_anomaly_score)) * 100.0

    # Weighted combination
    score = (rule_component * RULE_WEIGHT) + (ml_component * ML_WEIGHT)

    return round(min(100.0, max(0.0, score)), 2)
