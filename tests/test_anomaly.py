"""Tests for anomaly detection module (rules, ML, scorer)."""

from decimal import Decimal

import numpy as np

from codicecivico.anomaly.ml import (
    extract_features,
    predict_anomaly_scores,
    train_model,
)
from codicecivico.anomaly.rules import (
    FlagType,
    Severity,
    check_all_rules,
    check_extension_abuse,
    check_last_minute,
    check_price_spike,
    check_revolving_door,
    check_short_duration,
    check_single_bid,
    check_split_contracts,
)
from codicecivico.anomaly.scorer import compute_risk_score

# ---------------------------------------------------------------------------
# L1: Unit tests — individual rules
# ---------------------------------------------------------------------------


class TestSingleBid:
    def test_fires_when_n_bids_is_1(self) -> None:
        flag = check_single_bid({"n_bids": 1, "amount_original": Decimal("200000")})
        assert flag is not None
        assert flag.flag_type == FlagType.SINGLE_BID
        assert flag.severity == Severity.HIGH  # > €150k

    def test_medium_for_small_amount(self) -> None:
        flag = check_single_bid({"n_bids": 1, "amount_original": Decimal("50000")})
        assert flag is not None
        assert flag.severity == Severity.MEDIUM

    def test_no_flag_when_multiple_bids(self) -> None:
        assert check_single_bid({"n_bids": 5}) is None

    def test_no_flag_when_n_bids_missing(self) -> None:
        assert check_single_bid({}) is None


class TestLastMinute:
    def test_fires_when_very_short_deadline(self) -> None:
        flag = check_last_minute({"contract_duration_days": 5})
        assert flag is not None
        assert flag.flag_type == FlagType.LAST_MINUTE
        assert flag.severity == Severity.HIGH  # < 7 days

    def test_medium_for_10_days(self) -> None:
        flag = check_last_minute({"contract_duration_days": 10})
        assert flag is not None
        assert flag.severity == Severity.MEDIUM

    def test_no_flag_for_normal_deadline(self) -> None:
        assert check_last_minute({"contract_duration_days": 30}) is None


class TestShortDuration:
    def test_fires_for_large_fast_contract(self) -> None:
        flag = check_short_duration({
            "contract_duration_days": 15,
            "amount_original": Decimal("100000"),
        })
        assert flag is not None
        assert flag.flag_type == FlagType.SHORT_DURATION

    def test_no_flag_for_small_contract(self) -> None:
        """Sub-threshold contracts can legitimately be fast."""
        assert check_short_duration({
            "contract_duration_days": 15,
            "amount_original": Decimal("30000"),
        }) is None


class TestSplitContracts:
    def test_fires_when_5_similar_contracts_in_window(self) -> None:
        """L2: Split contracts are ANAC's most investigated anomaly.
        # SOURCE: ANAC Rapporto Annuale 2023 — frazionamento artificioso
        """
        from datetime import date
        buyer_contracts = [
            {"cpv_code": "90911000-1", "buyer_cf": "ABC",
             "amount_original": Decimal("35000"), "publication_date": date(2025, 6, 5)},
            {"cpv_code": "90911000-2", "buyer_cf": "ABC",
             "amount_original": Decimal("38000"), "publication_date": date(2025, 6, 10)},
            {"cpv_code": "90911000-3", "buyer_cf": "ABC",
             "amount_original": Decimal("39000"), "publication_date": date(2025, 6, 20)},
            {"cpv_code": "90911000-4", "buyer_cf": "ABC",
             "amount_original": Decimal("36000"), "publication_date": date(2025, 7, 1)},
            {"cpv_code": "90911000-5", "buyer_cf": "ABC",
             "amount_original": Decimal("37000"), "publication_date": date(2025, 7, 15)},
        ]
        contract = {
            "cpv_code": "90911000-6", "buyer_cf": "ABC",
            "amount_original": Decimal("35000"),
            "publication_date": date(2025, 7, 1),
        }
        flag = check_split_contracts(contract, buyer_contracts)
        assert flag is not None
        assert flag.flag_type == FlagType.SPLIT_CONTRACTS
        assert flag.details["n_similar_contracts"] >= 5

    def test_no_flag_when_outside_90_day_window(self) -> None:
        """Contracts spread across >90 days are not clustered fragmentation."""
        from datetime import date
        buyer_contracts = [
            {"cpv_code": "90911000", "buyer_cf": "ABC",
             "amount_original": Decimal("35000"), "publication_date": date(2024, 1, 1)},
            {"cpv_code": "90911000", "buyer_cf": "ABC",
             "amount_original": Decimal("38000"), "publication_date": date(2024, 6, 1)},
            {"cpv_code": "90911000", "buyer_cf": "ABC",
             "amount_original": Decimal("39000"), "publication_date": date(2024, 12, 1)},
            {"cpv_code": "90911000", "buyer_cf": "ABC",
             "amount_original": Decimal("36000"), "publication_date": date(2025, 6, 1)},
            {"cpv_code": "90911000", "buyer_cf": "ABC",
             "amount_original": Decimal("37000"), "publication_date": date(2025, 12, 1)},
        ]
        contract = {
            "cpv_code": "90911000", "buyer_cf": "ABC",
            "amount_original": Decimal("35000"),
            "publication_date": date(2025, 12, 15),
        }
        assert check_split_contracts(contract, buyer_contracts) is None

    def test_no_flag_below_min_threshold(self) -> None:
        """3 contratti simili non bastano più (n>=5)."""
        from datetime import date
        buyer_contracts = [
            {"cpv_code": "90911000", "buyer_cf": "ABC",
             "amount_original": Decimal("35000"), "publication_date": date(2025, 6, 5)},
            {"cpv_code": "90911000", "buyer_cf": "ABC",
             "amount_original": Decimal("38000"), "publication_date": date(2025, 6, 10)},
            {"cpv_code": "90911000", "buyer_cf": "ABC",
             "amount_original": Decimal("39000"), "publication_date": date(2025, 6, 20)},
        ]
        contract = {
            "cpv_code": "90911000", "buyer_cf": "ABC",
            "amount_original": Decimal("35000"),
            "publication_date": date(2025, 6, 15),
        }
        assert check_split_contracts(contract, buyer_contracts) is None

    def test_no_flag_without_context(self) -> None:
        contract = {"cpv_code": "12345678", "amount_original": Decimal("30000")}
        assert check_split_contracts(contract) is None

    def test_no_flag_when_suppliers_are_diverse(self) -> None:
        """Filtro A: ≥60% fornitori diversi = procurement ordinario, non split.

        # SOURCE: ANAC Rapporto 2023 — il frazionamento artificioso si
        # riconosce per la concentrazione su pochi fornitori; la varietà
        # di fornitori su stesso CPV/buyer indica procurement operativo.
        """
        from datetime import date
        # 6 contratti con 6 fornitori diversi → diversity = 1.0
        buyer_contracts = [
            {"cpv_code": "33690000", "buyer_cf": "ABC", "supplier_cf": f"S{i:03d}",
             "amount_original": Decimal("35000"),
             "publication_date": date(2025, 6, 1 + i)}
            for i in range(6)
        ]
        contract = {
            "cpv_code": "33690000", "buyer_cf": "ABC", "supplier_cf": "S999",
            "amount_original": Decimal("35000"),
            "publication_date": date(2025, 6, 15),
        }
        assert check_split_contracts(contract, buyer_contracts) is None

    def test_fires_when_suppliers_concentrated(self) -> None:
        """Pattern sospetto: molti contratti, pochi fornitori ripetuti."""
        from datetime import date
        # 6 contratti con solo 2 fornitori → diversity = 2/7 ≈ 0.29
        buyer_contracts = [
            {"cpv_code": "33690000", "buyer_cf": "ABC", "supplier_cf": "S001",
             "amount_original": Decimal("35000"),
             "publication_date": date(2025, 6, 1)},
            {"cpv_code": "33690000", "buyer_cf": "ABC", "supplier_cf": "S001",
             "amount_original": Decimal("38000"),
             "publication_date": date(2025, 6, 5)},
            {"cpv_code": "33690000", "buyer_cf": "ABC", "supplier_cf": "S002",
             "amount_original": Decimal("39000"),
             "publication_date": date(2025, 6, 10)},
            {"cpv_code": "33690000", "buyer_cf": "ABC", "supplier_cf": "S001",
             "amount_original": Decimal("37000"),
             "publication_date": date(2025, 6, 15)},
            {"cpv_code": "33690000", "buyer_cf": "ABC", "supplier_cf": "S002",
             "amount_original": Decimal("36000"),
             "publication_date": date(2025, 6, 20)},
        ]
        contract = {
            "cpv_code": "33690000", "buyer_cf": "ABC", "supplier_cf": "S001",
            "amount_original": Decimal("35000"),
            "publication_date": date(2025, 6, 25),
        }
        flag = check_split_contracts(contract, buyer_contracts)
        assert flag is not None
        assert flag.details["supplier_diversity"] < 0.6

    def test_giant_cluster_declassed_to_low(self) -> None:
        """Filtro B: >20 contratti simili = procurement continuo, severity=LOW."""
        from datetime import date
        # 21 contratti con solo 3 fornitori (diversity 3/22 ≈ 0.14, pass filtro A)
        buyer_contracts = [
            {"cpv_code": "33690000", "buyer_cf": "ABC",
             "supplier_cf": f"S{i % 3:03d}",
             "amount_original": Decimal("35000"),
             "publication_date": date(2025, 6, 1)}
            for i in range(21)
        ]
        contract = {
            "cpv_code": "33690000", "buyer_cf": "ABC", "supplier_cf": "S000",
            "amount_original": Decimal("35000"),
            "publication_date": date(2025, 6, 15),
        }
        flag = check_split_contracts(contract, buyer_contracts)
        assert flag is not None
        assert flag.severity == Severity.LOW


class TestPriceSpike:
    def test_fires_when_z_over_3(self) -> None:
        """L2: log-normal z-score > 3 sigma (~p99.87) on CPV-8 bucket.

        # SOURCE: OECD "Preventing Corruption in Public Procurement" (2016),
        # Ch.3 — price benchmarking via statistical distribution of offers.
        """
        import math
        # Bucket: geometric mean €100k, sigma log = 1.0 (moderate dispersion)
        # Contract of €3M → log = 14.91, z = (14.91 - 11.51) / 1.0 ≈ 3.4
        mu = math.log(100_000)
        flag = check_price_spike(
            {"amount_original": Decimal("3000000")},
            cpv_log_stats=(mu, 1.0, 100),
        )
        assert flag is not None
        assert flag.flag_type == FlagType.PRICE_SPIKE
        assert flag.details["z_score"] > 3.0

    def test_no_flag_within_one_sigma(self) -> None:
        """Prezzo nella coda normale della distribuzione — nessun flag."""
        import math
        mu = math.log(100_000)
        flag = check_price_spike(
            {"amount_original": Decimal("200000")},  # z ≈ 0.69
            cpv_log_stats=(mu, 1.0, 100),
        )
        assert flag is None

    def test_no_flag_when_bucket_too_small(self) -> None:
        """Bucket con <30 samples: skip (non abbastanza dati per fittare)."""
        import math
        mu = math.log(100_000)
        flag = check_price_spike(
            {"amount_original": Decimal("10000000")},
            cpv_log_stats=(mu, 1.0, 10),  # solo 10 samples
        )
        assert flag is None

    def test_no_flag_when_stats_missing(self) -> None:
        assert check_price_spike(
            {"amount_original": Decimal("1000000")},
            cpv_log_stats=None,
        ) is None


class TestRevolvingDoor:
    def test_fires_when_supplier_dominates(self) -> None:
        """L2: Supplier concentration is a key ANAC indicator.
        # SOURCE: ANAC Rapporto 2023 — concentrazione aggiudicatari
        """
        flag = check_revolving_door(
            {}, supplier_win_count=8, buyer_total_contracts=10,
        )
        assert flag is not None
        assert flag.flag_type == FlagType.REVOLVING_DOOR
        assert flag.severity == Severity.HIGH  # 80% > 75%

    def test_no_flag_for_diverse_suppliers(self) -> None:
        assert check_revolving_door(
            {}, supplier_win_count=2, buyer_total_contracts=10,
        ) is None

    def test_no_flag_for_few_contracts(self) -> None:
        """Too few contracts to judge."""
        assert check_revolving_door(
            {}, supplier_win_count=2, buyer_total_contracts=3,
        ) is None


class TestExtensionAbuse:
    def test_fires_when_many_extensions(self) -> None:
        flag = check_extension_abuse({}, extensions_count=4)
        assert flag is not None
        assert flag.severity == Severity.HIGH

    def test_no_flag_for_single_extension(self) -> None:
        assert check_extension_abuse({}, extensions_count=1) is None


# ---------------------------------------------------------------------------
# L1: check_all_rules aggregate
# ---------------------------------------------------------------------------


class TestCheckAllRules:
    def test_multiple_flags_at_once(self) -> None:
        """A contract can trigger multiple red flags simultaneously."""
        contract = {
            "n_bids": 1,
            "contract_duration_days": 5,
            "amount_original": Decimal("200000"),
        }
        flags = check_all_rules(contract)
        types = {f.flag_type for f in flags}
        assert FlagType.SINGLE_BID in types
        assert FlagType.LAST_MINUTE in types
        assert len(flags) >= 2

    def test_clean_contract_no_flags(self) -> None:
        contract = {
            "n_bids": 5,
            "contract_duration_days": 45,
            "amount_original": Decimal("100000"),
        }
        flags = check_all_rules(contract)
        assert len(flags) == 0


# ---------------------------------------------------------------------------
# L1: ML feature extraction
# ---------------------------------------------------------------------------


class TestFeatureExtraction:
    def _make_contracts(self, n: int = 20) -> list[dict[str, object]]:
        """Generate n synthetic contracts for testing."""
        contracts = []
        for i in range(n):
            contracts.append({
                "ocid": f"ocds-test-{i:04d}",
                "amount_original": Decimal(str(50000 + i * 10000)),
                "n_bids": (i % 5) + 1,
                "contract_duration_days": 30 + i * 2,
                "cpv_code": f"4521{i % 3}000-{i % 10}",
                "buyer_cf": f"BUYER{i % 3:03d}",
                "supplier_cf": f"SUPP{i % 4:03d}",
            })
        return contracts

    def test_extract_returns_correct_shape(self) -> None:
        contracts = self._make_contracts(20)
        features, cig_ids = extract_features(contracts)
        assert features.shape == (20, 7)
        assert len(cig_ids) == 20

    def test_extract_skips_zero_amount(self) -> None:
        contracts = [{"ocid": "test", "amount_original": Decimal("0")}]
        features, cig_ids = extract_features(contracts)
        assert features.shape[0] == 0

    def test_features_are_finite(self) -> None:
        contracts = self._make_contracts(20)
        features, _ = extract_features(contracts)
        assert np.all(np.isfinite(features))


# ---------------------------------------------------------------------------
# L1: ML model training + prediction
# ---------------------------------------------------------------------------


class TestIsolationForest:
    def test_train_and_predict(self) -> None:
        """Train on synthetic data, predict anomaly scores."""
        np.random.seed(42)
        # Normal contracts
        normal = np.random.normal(loc=5, scale=1, size=(100, 7))
        # Inject 5 anomalies
        anomalies = np.random.normal(loc=15, scale=0.5, size=(5, 7))
        features = np.vstack([normal, anomalies]).astype(np.float64)

        model = train_model(features)
        scores = predict_anomaly_scores(model, features)

        assert scores.shape == (105,)
        assert scores.min() >= 0.0
        assert scores.max() <= 1.0

        # Anomalies should score higher than most normal points
        normal_mean = scores[:100].mean()
        anomaly_mean = scores[100:].mean()
        assert anomaly_mean > normal_mean, (
            f"Anomalies ({anomaly_mean:.3f}) should score higher than "
            f"normal ({normal_mean:.3f})"
        )


# ---------------------------------------------------------------------------
# L1: Composite risk scorer
# ---------------------------------------------------------------------------


class TestRiskScorer:
    def test_clean_contract_zero_score(self) -> None:
        score = compute_risk_score([], ml_anomaly_score=0.0)
        assert score == 0.0

    def test_single_high_flag(self) -> None:
        from codicecivico.anomaly.rules import RedFlag
        flags = [RedFlag(FlagType.SINGLE_BID, Severity.HIGH, {})]
        score = compute_risk_score(flags, ml_anomaly_score=0.0)
        # 40 * 0.6 = 24
        assert score == 24.0

    def test_multiple_flags_plus_ml(self) -> None:
        from codicecivico.anomaly.rules import RedFlag
        flags = [
            RedFlag(FlagType.SINGLE_BID, Severity.HIGH, {}),
            RedFlag(FlagType.LAST_MINUTE, Severity.HIGH, {}),
        ]
        score = compute_risk_score(flags, ml_anomaly_score=0.8)
        # Rules: (40+40)*0.6 = 48.0, ML: 0.8*100*0.4 = 32.0 → 80.0
        assert score == 80.0

    def test_score_clamped_to_100(self) -> None:
        from codicecivico.anomaly.rules import RedFlag
        flags = [
            RedFlag(FlagType.SINGLE_BID, Severity.HIGH, {}),
            RedFlag(FlagType.LAST_MINUTE, Severity.HIGH, {}),
            RedFlag(FlagType.PRICE_SPIKE, Severity.HIGH, {}),
        ]
        score = compute_risk_score(flags, ml_anomaly_score=1.0)
        assert score <= 100.0

    def test_high_risk_threshold(self) -> None:
        """L2: Contracts with 2+ HIGH flags should score > 70 (dashboard threshold).
        # SOURCE: Design spec — Contracts > 70 surfaced in dashboard
        """
        from codicecivico.anomaly.rules import RedFlag
        flags = [
            RedFlag(FlagType.SINGLE_BID, Severity.HIGH, {}),
            RedFlag(FlagType.REVOLVING_DOOR, Severity.HIGH, {}),
        ]
        score = compute_risk_score(flags, ml_anomaly_score=0.6)
        assert score > 70, f"Score {score} should exceed dashboard threshold of 70"
