"""Isolation Forest anomaly detection for procurement data.

Features (7):
1. log_amount: log10 of contract value (higher = rarer)
2. n_bids: number of bidders (1 = monopoly signal)
3. duration_days: publication-to-deadline duration
4. amount_vs_cpv_mean: ratio of amount to CPV category mean
5. buyer_concentration: fraction of buyer's spend going to this supplier
6. supplier_win_rate: fraction of CPV contracts won by this supplier
7. time_pressure: 1/days_to_deadline (higher = more pressure)

SOURCE: scikit-learn IsolationForest — verified docs.scikit-learn.org v1.6
"""

import logging
import math
from collections import defaultdict

import numpy as np
from numpy.typing import NDArray
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

# Model hyperparameters
CONTAMINATION = 0.05  # Expected fraction of anomalies
N_ESTIMATORS = 200
RANDOM_STATE = 42


def extract_features(
    contracts: list[dict[str, object]],
) -> tuple[NDArray[np.float64], list[str]]:
    """Extract 7-feature matrix from a list of contract dicts.

    Args:
        contracts: List of dicts with keys matching Contract model fields.

    Returns:
        (features_matrix [N x 7], cig_ids [N])
        Rows with all-NaN features are excluded.
    """
    # Pre-compute aggregates for context features
    cpv_amounts: dict[str, list[float]] = defaultdict(list)
    buyer_supplier_spend: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    buyer_total_spend: dict[str, float] = defaultdict(float)
    cpv_supplier_wins: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    cpv_total_contracts: dict[str, int] = defaultdict(int)

    for c in contracts:
        amt = _safe_float(c.get("amount_original") or c.get("amount_awarded"))
        cpv = str(c.get("cpv_code", ""))[:5]  # First 5 digits = category
        buyer = str(c.get("buyer_cf", ""))
        supplier = str(c.get("supplier_cf", ""))

        if amt > 0 and cpv:
            cpv_amounts[cpv].append(amt)
        if amt > 0 and buyer and supplier:
            buyer_supplier_spend[buyer][supplier] += amt
            buyer_total_spend[buyer] += amt
        if cpv and supplier:
            cpv_supplier_wins[cpv][supplier] += 1
            cpv_total_contracts[cpv] += 1

    # Compute CPV means
    cpv_mean: dict[str, float] = {
        cpv: sum(amounts) / len(amounts)
        for cpv, amounts in cpv_amounts.items()
        if amounts
    }

    # Build feature matrix
    features = []
    cig_ids = []

    for c in contracts:
        ocid = str(c.get("ocid", ""))
        amt = _safe_float(c.get("amount_original") or c.get("amount_awarded"))
        n_bids = _safe_float(c.get("n_bids"))
        duration = _safe_float(c.get("contract_duration_days"))
        cpv = str(c.get("cpv_code", ""))[:5]
        buyer = str(c.get("buyer_cf", ""))
        supplier = str(c.get("supplier_cf", ""))

        # Feature 1: log_amount
        log_amount = math.log10(amt) if amt > 0 else 0.0

        # Feature 2: n_bids (0 if unknown)
        feat_n_bids = n_bids if n_bids > 0 else 0.0

        # Feature 3: duration_days
        feat_duration = duration if duration > 0 else 0.0

        # Feature 4: amount_vs_cpv_mean
        mean = cpv_mean.get(cpv, 0.0)
        feat_amt_ratio = (amt / mean) if mean > 0 and amt > 0 else 0.0

        # Feature 5: buyer_concentration
        feat_buyer_conc = 0.0
        if buyer and supplier and buyer_total_spend[buyer] > 0:
            feat_buyer_conc = (
                buyer_supplier_spend[buyer][supplier] / buyer_total_spend[buyer]
            )

        # Feature 6: supplier_win_rate
        feat_supplier_rate = 0.0
        if cpv and supplier and cpv_total_contracts[cpv] > 0:
            feat_supplier_rate = (
                cpv_supplier_wins[cpv][supplier] / cpv_total_contracts[cpv]
            )

        # Feature 7: time_pressure (inverse of duration)
        feat_time_pressure = (1.0 / duration) if duration > 0 else 0.0

        row = [
            log_amount,
            feat_n_bids,
            feat_duration,
            feat_amt_ratio,
            feat_buyer_conc,
            feat_supplier_rate,
            feat_time_pressure,
        ]

        # Skip rows where amount is 0 (no useful signal)
        if amt <= 0:
            continue

        features.append(row)
        cig_ids.append(ocid)

    return np.array(features, dtype=np.float64), cig_ids


FEATURE_NAMES = [
    "log_amount",
    "n_bids",
    "duration_days",
    "amount_vs_cpv_mean",
    "buyer_concentration",
    "supplier_win_rate",
    "time_pressure",
]


def train_model(
    features: NDArray[np.float64],
) -> IsolationForest:
    """Train Isolation Forest on procurement features.

    Args:
        features: Matrix of shape (N, 7).

    Returns:
        Fitted IsolationForest model.
    """
    assert features.shape[1] == 7, f"Expected 7 features, got {features.shape[1]}"
    assert features.shape[0] >= 10, f"Need at least 10 samples, got {features.shape[0]}"

    model = IsolationForest(
        contamination=CONTAMINATION,
        n_estimators=N_ESTIMATORS,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(features)
    logger.info(
        "Trained IsolationForest on %d samples (contamination=%.2f).",
        features.shape[0],
        CONTAMINATION,
    )
    return model


def predict_anomaly_scores(
    model: IsolationForest,
    features: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Get anomaly scores for each sample.

    Returns:
        Array of scores in [0, 1] range where 1 = most anomalous.
        (Inverted from sklearn's convention where lower = more anomalous.)
    """
    # sklearn score_samples: lower = more anomalous
    raw_scores = model.score_samples(features)
    # Normalize to [0, 1]: 1 = most anomalous
    min_s, max_s = raw_scores.min(), raw_scores.max()
    if max_s - min_s < 1e-10:
        return np.zeros(len(raw_scores), dtype=np.float64)
    normalized = 1.0 - (raw_scores - min_s) / (max_s - min_s)
    result: NDArray[np.float64] = normalized.astype(np.float64)
    return result


def _safe_float(value: object) -> float:
    """Safely convert to float."""
    if value is None:
        return 0.0
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return 0.0
