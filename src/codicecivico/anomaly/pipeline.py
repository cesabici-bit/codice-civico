"""Anomaly detection pipeline — DB integration for procurement contracts.

Loads Contract rows, runs rule-based checks + ML anomaly scoring,
writes AnomalyFlag rows and updates Contract.risk_score.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.anomaly.ml import (
    extract_features,
    predict_anomaly_scores,
    train_model,
)
from codicecivico.anomaly.rules import check_all_rules
from codicecivico.anomaly.scorer import compute_risk_score
from codicecivico.models import AnomalyFlag, Contract

logger = logging.getLogger(__name__)


def _contract_to_dict(c: Contract) -> dict[str, object]:
    """Convert a Contract ORM row to the dict shape expected by rules/ml."""
    return {
        "ocid": c.ocid,
        "buyer_cf": c.buyer_cf,
        "buyer_name": c.buyer_name,
        "supplier_cf": c.supplier_cf,
        "supplier_name": c.supplier_name,
        "cpv_code": c.cpv_code,
        "amount_original": c.amount_original,
        "amount_awarded": c.amount_awarded,
        "n_bids": c.n_bids,
        "contract_duration_days": c.contract_duration_days,
        "publication_date": c.publication_date,
        "award_date": c.award_date,
    }


async def run_anomaly_pipeline(
    session: AsyncSession,
    *,
    limit: int | None = None,
) -> tuple[int, int]:
    """Score all contracts, insert AnomalyFlag rows, update risk_score.

    Idempotent: deletes existing AnomalyFlag rows and recomputes.

    Returns:
        (contracts_scored, flags_inserted)
    """
    stmt = select(Contract).order_by(Contract.created_at)
    if limit is not None:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    contracts = list(result.scalars().all())

    if not contracts:
        logger.info("No contracts in DB; nothing to score.")
        return 0, 0

    logger.info("Loaded %d contracts for anomaly analysis.", len(contracts))
    dicts = [_contract_to_dict(c) for c in contracts]

    # --- Aggregates for rule context ---
    cpv_amounts: dict[str, list[float]] = defaultdict(list)
    buyer_total_contracts: dict[str, int] = defaultdict(int)
    supplier_wins_per_buyer: dict[tuple[str, str], int] = defaultdict(int)
    buyer_contracts_lookup: dict[str, list[dict[str, object]]] = defaultdict(list)

    for d in dicts:
        cpv = str(d.get("cpv_code") or "")[:5]
        buyer = str(d.get("buyer_cf") or "")
        supplier = str(d.get("supplier_cf") or "")
        amt_raw = d.get("amount_original") or d.get("amount_awarded")
        amt = float(amt_raw) if amt_raw is not None else 0.0

        if cpv and amt > 0:
            cpv_amounts[cpv].append(amt)
        if buyer:
            buyer_total_contracts[buyer] += 1
            buyer_contracts_lookup[buyer].append(d)
        if buyer and supplier:
            supplier_wins_per_buyer[(buyer, supplier)] += 1

    cpv_median = {
        cpv: statistics.median(vals) for cpv, vals in cpv_amounts.items() if vals
    }

    # --- ML training + scoring ---
    features, cig_ids = extract_features(dicts)
    ocid_to_score: dict[str, float] = {}
    if features.shape[0] >= 10:
        model = train_model(features)
        scores = predict_anomaly_scores(model, features)
        ocid_to_score = dict(zip(cig_ids, scores.tolist(), strict=False))
    else:
        logger.warning(
            "Skipping ML: only %d samples (need >= 10).", features.shape[0],
        )

    # --- Clear old flags (idempotent recompute) ---
    await session.execute(delete(AnomalyFlag))
    await session.flush()

    # --- Rules + flag insert + risk_score update ---
    total_flags = 0
    for idx, (contract_row, d) in enumerate(zip(contracts, dicts, strict=False)):
        ocid = str(d.get("ocid") or "")
        buyer = str(d.get("buyer_cf") or "")
        cpv = str(d.get("cpv_code") or "")[:5]
        supplier = str(d.get("supplier_cf") or "")
        ml_score = ocid_to_score.get(ocid, 0.0)

        flags = check_all_rules(
            d,
            buyer_contracts=buyer_contracts_lookup.get(buyer) if buyer else None,
            cpv_median=cpv_median.get(cpv),
            supplier_win_count=(
                supplier_wins_per_buyer.get((buyer, supplier))
                if buyer and supplier
                else None
            ),
            buyer_total_contracts=buyer_total_contracts.get(buyer),
        )

        risk = compute_risk_score(flags, ml_score)
        contract_row.risk_score = Decimal(str(round(risk, 2)))

        for flag in flags:
            session.add(
                AnomalyFlag(
                    contract_id=contract_row.id,
                    flag_type=flag.flag_type.value,
                    severity=flag.severity.value,
                    details=flag.details,
                    ml_anomaly_score=round(ml_score, 4),
                ),
            )
            total_flags += 1

        if (idx + 1) % 5000 == 0:
            await session.flush()
            logger.info("Scored %d/%d contracts...", idx + 1, len(contracts))

    await session.flush()
    logger.info(
        "Anomaly pipeline complete: %d flags across %d contracts.",
        total_flags,
        len(contracts),
    )
    return len(contracts), total_flags
