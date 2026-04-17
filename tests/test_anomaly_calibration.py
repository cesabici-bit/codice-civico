"""L2 calibration tests for anomaly rules against external oracles.

These tests assert the rule set behaves plausibly vs published ANAC/EU/OECD
base rates, and guard against regressions that would re-inflate the flag rate.

Oracle sources (cited inline per test):
- ANAC Rapporto Annuale 2023 — indicatori di rischio appalti
- EU Single Market Scoreboard — procurement indicators (single bidding)
- OECD "Preventing Corruption in Public Procurement" (2016)

Context (2026-04-17 calibration):
Before tuning, the rules flagged ~48% of live ANAC 2025-12 contracts
(81,947 flags / 170,667 contracts), with PRICE_SPIKE + SPLIT_CONTRACTS
accounting for 86% of flags — empirically implausible vs published base rates
(frazionamento stimato 5-8% di contratti sub-soglia; OECD price benchmarking
implies single-digit % outliers).  After z-score log-normal PRICE_SPIKE and
90-day rolling-window + supplier-diversity SPLIT, target is <15% global.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from codicecivico.anomaly.rules import (
    FlagType,
    PRICE_SPIKE_MIN_SAMPLES,
    _cpv_main,
    check_all_rules,
)


def _build_aggregates(
    contracts: list[dict[str, object]],
) -> dict[str, object]:
    """Replicate the aggregates computed in pipeline.run_anomaly_pipeline."""
    cpv_log_amounts: dict[str, list[float]] = defaultdict(list)
    buyer_total: dict[str, int] = defaultdict(int)
    supplier_wins: dict[tuple[str, str], int] = defaultdict(int)
    buyer_lookup: dict[str, list[dict[str, object]]] = defaultdict(list)

    for d in contracts:
        cpv8 = _cpv_main(d.get("cpv_code"))
        buyer = str(d.get("buyer_cf") or "")
        supplier = str(d.get("supplier_cf") or "")
        amt_raw = d.get("amount_original") or d.get("amount_awarded")
        amt = float(amt_raw) if amt_raw is not None else 0.0

        if cpv8 and amt > 0:
            cpv_log_amounts[cpv8].append(math.log(amt))
        if buyer:
            buyer_total[buyer] += 1
            buyer_lookup[buyer].append(d)
        if buyer and supplier:
            supplier_wins[(buyer, supplier)] += 1

    cpv_log_stats: dict[str, tuple[float, float, int]] = {}
    for cpv8, logs in cpv_log_amounts.items():
        n = len(logs)
        if n < PRICE_SPIKE_MIN_SAMPLES:
            continue
        cpv_log_stats[cpv8] = (
            statistics.fmean(logs),
            statistics.stdev(logs) if n >= 2 else 0.0,
            n,
        )

    return {
        "cpv_log_stats": cpv_log_stats,
        "buyer_total": buyer_total,
        "supplier_wins": supplier_wins,
        "buyer_lookup": buyer_lookup,
    }


def _run_rules(
    contracts: list[dict[str, object]],
    aggs: dict[str, object],
) -> list[list]:
    """Run check_all_rules on every contract. Returns list of flags per contract."""
    results = []
    for d in contracts:
        cpv8 = _cpv_main(d.get("cpv_code"))
        buyer = str(d.get("buyer_cf") or "")
        supplier = str(d.get("supplier_cf") or "")
        flags = check_all_rules(
            d,
            buyer_contracts=aggs["buyer_lookup"].get(buyer) if buyer else None,
            cpv_log_stats=aggs["cpv_log_stats"].get(cpv8),
            supplier_win_count=(
                aggs["supplier_wins"].get((buyer, supplier))
                if buyer and supplier else None
            ),
            buyer_total_contracts=aggs["buyer_total"].get(buyer),
        )
        results.append(flags)
    return results


def _synthetic_realistic_population(
    n_normal: int = 800,
    seed_base_date: date = date(2025, 6, 1),
) -> list[dict[str, object]]:
    """Build a population mimicking ANAC distribution characteristics.

    - ~30 distinct CPV-8 codes (covers PRICE_SPIKE_MIN_SAMPLES per bucket)
    - ~40 distinct buyers, ~200 suppliers
    - Log-normal amounts per CPV (geometric mean 20k–300k, sigma 0.8–1.4)
    - Normal publication dates spread over 6 months
    """
    import random
    rng = random.Random(42)
    cpvs = [f"{30_000_000 + i * 1_000_000:08d}" for i in range(30)]
    buyers = [f"BUY{i:03d}" for i in range(40)]
    suppliers = [f"SUP{i:03d}" for i in range(200)]

    contracts: list[dict[str, object]] = []
    for i in range(n_normal):
        cpv = rng.choice(cpvs)
        # each CPV has its own geometric mean & sigma
        cpv_idx = int(cpv[1:4]) % 30
        mu_log = math.log(20_000 + cpv_idx * 8_000)
        sigma = 0.8 + (cpv_idx % 4) * 0.15
        amt = round(math.exp(rng.gauss(mu_log, sigma)), 2)
        contracts.append({
            "ocid": f"N-{i:06d}",
            "buyer_cf": rng.choice(buyers),
            "supplier_cf": rng.choice(suppliers),
            "cpv_code": f"{cpv}-{i % 10}",
            "amount_original": Decimal(str(max(100.0, amt))),
            "amount_awarded": Decimal(str(max(100.0, amt))),
            "n_bids": rng.randint(2, 8),
            "contract_duration_days": rng.randint(30, 365),
            "publication_date": seed_base_date + timedelta(days=rng.randint(0, 180)),
        })
    return contracts


def _inject_frazionamento(
    contracts: list[dict[str, object]],
    *,
    buyer: str = "BUY_SPLIT",
    supplier: str = "SUP_FAV",
    cpv: str = "45200000",
    n: int = 6,
    base_date: date = date(2025, 6, 15),
) -> list[str]:
    """Inject a textbook artificial-fragmentation cluster: same buyer+CPV,
    sub-threshold amounts, concentrated supplier, within 30 days.

    Returns list of OCIDs of injected contracts (for recall measurement).
    """
    ocids = []
    for i in range(n):
        ocid = f"FRAZ-{buyer}-{i:02d}"
        ocids.append(ocid)
        contracts.append({
            "ocid": ocid,
            "buyer_cf": buyer,
            "supplier_cf": supplier if i < n - 1 else f"{supplier}2",
            "cpv_code": f"{cpv}-{i}",
            "amount_original": Decimal(str(35000 + i * 500)),
            "amount_awarded": Decimal(str(35000 + i * 500)),
            "n_bids": 2,
            "contract_duration_days": 60,
            "publication_date": base_date + timedelta(days=i * 4),
        })
    return ocids


def _inject_price_spike(
    contracts: list[dict[str, object]],
    *,
    cpv: str,
    amount: Decimal,
    ocid: str,
) -> str:
    contracts.append({
        "ocid": ocid,
        "buyer_cf": "BUY_SPIKE",
        "supplier_cf": "SUP_SPIKE",
        "cpv_code": f"{cpv}-0",
        "amount_original": amount,
        "amount_awarded": amount,
        "n_bids": 3,
        "contract_duration_days": 90,
        "publication_date": date(2025, 8, 1),
    })
    return ocid


# ---------------------------------------------------------------------------
# L2 Guard tests
# ---------------------------------------------------------------------------


def test_global_flag_rate_under_15_percent_on_realistic_population() -> None:
    """L2 Guard: flag rate globale ≤ 15% su distribuzione realistica.

    # SOURCE: ANAC Rapporto Annuale 2023 — indicatori di rischio.
    # Published base rates imply single-digit % genuine anomalies across
    # frazionamento + single-bid + price outliers; a system flagging >15%
    # has lost signal-to-noise.
    # SOURCE: pre-calibration live baseline 2026-04-17: 48% → unusable.
    # Target post-calibration: < 15% → pool investigativo utile.
    """
    contracts = _synthetic_realistic_population(n_normal=800)
    # Inject a handful of known-suspect patterns so the rate isn't trivially zero
    _inject_frazionamento(contracts, buyer="BUY_SPLIT_1")
    _inject_frazionamento(contracts, buyer="BUY_SPLIT_2", supplier="SUP_FAV2")

    aggs = _build_aggregates(contracts)
    flags_per_contract = _run_rules(contracts, aggs)

    flagged = sum(1 for flags in flags_per_contract if flags)
    rate = flagged / len(contracts)
    assert rate <= 0.15, (
        f"Flag rate {rate:.1%} exceeds 15% guard on realistic synthetic "
        f"population — rules likely over-sensitive. Threshold regression?"
    )
    print(f"\n[L2 GUARD] flag rate on realistic synth: {rate:.2%} ({flagged}/{len(contracts)})")


def test_injected_frazionamento_is_detected() -> None:
    """L2 Recall: un cluster di frazionamento noto DEVE generare SPLIT flag.

    # SOURCE: ANAC Rapporto 2023 — frazionamento artificioso è il pattern
    # più investigato negli appalti sotto-soglia. Se il nostro detector
    # non lo rileva, è inutile.
    """
    contracts = _synthetic_realistic_population(n_normal=800)
    injected = _inject_frazionamento(
        contracts, buyer="BUY_FRAZ", supplier="SUP_FAV", n=6,
    )

    aggs = _build_aggregates(contracts)
    flags_per_contract = _run_rules(contracts, aggs)

    ocid_to_flags = {
        contracts[i].get("ocid"): flags
        for i, flags in enumerate(flags_per_contract)
    }

    split_detected = sum(
        1 for ocid in injected
        if any(f.flag_type == FlagType.SPLIT_CONTRACTS for f in ocid_to_flags[ocid])
    )
    recall = split_detected / len(injected)
    assert recall >= 0.5, (
        f"SPLIT recall {recall:.0%} on injected frazionamento "
        f"({split_detected}/{len(injected)}) — detector blind to textbook pattern"
    )


def test_extreme_price_spike_is_detected() -> None:
    """L2 Recall: contratto 10x geometric mean del CPV deve flaggare PRICE_SPIKE.

    # SOURCE: OECD "Preventing Corruption in Public Procurement" (2016) Ch.3
    # — price benchmarking flags outliers statistically distant from peers.
    """
    # Need n_normal >= 30 * n_cpvs so each CPV-8 bucket has enough samples
    # to pass PRICE_SPIKE_MIN_SAMPLES guard (30 expected fit, else skip).
    contracts = _synthetic_realistic_population(n_normal=1500)
    target_cpv = "35000000"  # one of the 30 generated codes
    spike_amount = Decimal("5000000")  # ~83x mean → very high z
    spike_ocid = _inject_price_spike(
        contracts, cpv=target_cpv, amount=spike_amount, ocid="SPIKE-TEST-1",
    )

    aggs = _build_aggregates(contracts)
    flags_per_contract = _run_rules(contracts, aggs)
    ocid_to_flags = {
        contracts[i].get("ocid"): flags
        for i, flags in enumerate(flags_per_contract)
    }

    flags = ocid_to_flags[spike_ocid]
    assert any(f.flag_type == FlagType.PRICE_SPIKE for f in flags), (
        f"PRICE_SPIKE should fire on 83x geometric-mean contract; got {flags}"
    )


def test_diverse_procurement_not_flagged_as_split() -> None:
    """L2 Specificity: grande PA con 10 contratti stesso CPV in 90gg ma 10
    fornitori DIVERSI non è frazionamento — filtro A deve sopprimere.

    # SOURCE: procurement ordinario di ASL/ospedali/atenei: acquisto continuo
    # sub-soglia di materiali di consumo è legittimo e prevalente.
    """
    contracts = _synthetic_realistic_population(n_normal=500)
    # Inject a diverse-supplier cluster — should NOT flag as SPLIT
    base = date(2025, 6, 1)
    diverse_ocids = []
    for i in range(10):
        ocid = f"DIV-{i:02d}"
        diverse_ocids.append(ocid)
        contracts.append({
            "ocid": ocid,
            "buyer_cf": "BIG_HOSPITAL",
            "supplier_cf": f"DIV_SUP_{i:03d}",  # 10 different suppliers
            "cpv_code": f"33690000-{i}",
            "amount_original": Decimal(str(30000 + i * 1000)),
            "amount_awarded": Decimal(str(30000 + i * 1000)),
            "n_bids": 3,
            "contract_duration_days": 60,
            "publication_date": base + timedelta(days=i * 8),
        })

    aggs = _build_aggregates(contracts)
    flags_per_contract = _run_rules(contracts, aggs)
    ocid_to_flags = {
        contracts[i].get("ocid"): flags
        for i, flags in enumerate(flags_per_contract)
    }

    split_flagged = [
        ocid for ocid in diverse_ocids
        if any(f.flag_type == FlagType.SPLIT_CONTRACTS for f in ocid_to_flags[ocid])
    ]
    assert not split_flagged, (
        f"Diverse-supplier cluster should NOT trigger SPLIT flag, "
        f"but {len(split_flagged)}/{len(diverse_ocids)} were flagged: {split_flagged}"
    )


def test_single_bid_rate_matches_eu_scoreboard_ballpark() -> None:
    """L2 Sanity: il detector SINGLE_BID non inflaziona oltre il plausibile.

    # SOURCE: EU Single Market Scoreboard — Italy's single-bidding rate
    # è storicamente nell'ordine del 20-30% per procedure aperte.
    # Il nostro rule fires solo per n_bids == 1 (fatto osservabile), quindi
    # il rate è una funzione dei dati, non delle soglie. Qui verifichiamo
    # che su dati realistici (simulati con n_bids in [2,8]) il flag non fire
    # mai — garantisce che la soglia di severity non sia rotta.
    """
    contracts = _synthetic_realistic_population(n_normal=500)
    aggs = _build_aggregates(contracts)
    flags_per_contract = _run_rules(contracts, aggs)

    single_bid_flags = sum(
        1 for flags in flags_per_contract
        for f in flags if f.flag_type == FlagType.SINGLE_BID
    )
    # Nessun contratto sintetico ha n_bids==1 → zero flag
    assert single_bid_flags == 0, (
        f"SINGLE_BID fired {single_bid_flags} times on synth with n_bids>=2 — "
        "rule logic regression"
    )
