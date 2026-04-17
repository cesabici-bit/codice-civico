"""Tests for anomaly pipeline orchestration (unit-level, no DB).

The full integration test is the live VPS run on 170k contracts.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from codicecivico.anomaly.pipeline import _contract_to_dict
from codicecivico.models import Contract


def test_contract_to_dict_preserves_all_rule_relevant_fields() -> None:
    """_contract_to_dict must pass every field used by check_all_rules/extract_features.

    # SOURCE: `anomaly/rules.py` + `anomaly/ml.py` field lookups
    """
    c = Contract(
        id=uuid.uuid4(),
        ocid="ocds-hu01ve-TEST123",
        buyer_name="COMUNE DI TEST",
        buyer_cf="01234567890",
        supplier_name="Azienda Test SRL",
        supplier_cf="09876543210",
        cpv_code="33690000-3",
        amount_original=Decimal("100000.00"),
        amount_awarded=Decimal("95000.00"),
        n_bids=1,
        contract_duration_days=10,
        publication_date=date(2025, 12, 1),
        award_date=date(2025, 12, 20),
    )

    d = _contract_to_dict(c)

    # Fields used by rules.py
    assert d["n_bids"] == 1
    assert d["contract_duration_days"] == 10
    assert d["amount_original"] == Decimal("100000.00")
    assert d["amount_awarded"] == Decimal("95000.00")
    assert d["buyer_cf"] == "01234567890"
    assert d["supplier_cf"] == "09876543210"
    assert d["cpv_code"] == "33690000-3"
    # Fields used by ml.py extract_features
    assert d["ocid"] == "ocds-hu01ve-TEST123"
    assert d["publication_date"] == date(2025, 12, 1)


def test_contract_to_dict_handles_nulls() -> None:
    """Nullable fields (supplier not yet known) must map to None, not raise."""
    c = Contract(
        id=uuid.uuid4(),
        ocid="ocds-hu01ve-NULL",
        buyer_name="N/A",
        buyer_cf=None,
        supplier_name=None,
        supplier_cf=None,
        cpv_code=None,
        amount_original=None,
        amount_awarded=None,
        n_bids=None,
        contract_duration_days=None,
    )
    d = _contract_to_dict(c)
    assert d["supplier_cf"] is None
    assert d["amount_original"] is None
    assert d["n_bids"] is None
