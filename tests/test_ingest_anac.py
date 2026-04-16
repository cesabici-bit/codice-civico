"""Tests for ANAC procurement data ingestor."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from codicecivico.ingest.anac import (
    _detect_delimiter,
    _map_cig_to_contract,
    _parse_date_anac,
    _parse_decimal,
    parse_aggiudicatari_csv,
    parse_cig_csv,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# L1: Unit tests — helper functions
# ---------------------------------------------------------------------------


class TestParseDateAnac:
    def test_iso_format(self) -> None:
        assert _parse_date_anac("2024-01-15") == date(2024, 1, 15)

    def test_italian_format(self) -> None:
        assert _parse_date_anac("15/01/2024") == date(2024, 1, 15)

    def test_datetime_format(self) -> None:
        assert _parse_date_anac("2024-01-15T10:30:00") == date(2024, 1, 15)

    def test_empty(self) -> None:
        assert _parse_date_anac("") is None
        assert _parse_date_anac("   ") is None

    def test_garbage(self) -> None:
        assert _parse_date_anac("not-a-date") is None


class TestParseDecimal:
    def test_italian_amount(self) -> None:
        """Italian CSV: dots for thousands, comma for decimal."""
        assert _parse_decimal("50.000,00") == Decimal("50000.00")

    def test_simple(self) -> None:
        assert _parse_decimal("125000,50") == Decimal("125000.50")

    def test_empty(self) -> None:
        assert _parse_decimal("") is None
        assert _parse_decimal("   ") is None

    def test_english_decimal(self) -> None:
        """ANAC open-data CSV: dot = decimal, no thousands separator.

        Regression: 2026-04-16 production deploy hit numeric overflow
        because "74936922.41800001" was being parsed as 7493692241800001
        (100x inflated) — all "." were stripped as thousands separators.
        """
        assert _parse_decimal("74936922.41800001") == Decimal("74936922.41800001")
        assert _parse_decimal("1234567.89") == Decimal("1234567.89")

    def test_english_amount_with_thousands(self) -> None:
        """English-style: commas for thousands, dot for decimal."""
        assert _parse_decimal("1,234,567.89") == Decimal("1234567.89")


class TestDetectDelimiter:
    def test_semicolon(self) -> None:
        assert _detect_delimiter("a;b;c;d\n1;2;3;4") == ";"

    def test_comma(self) -> None:
        assert _detect_delimiter("a,b,c,d\n1,2,3,4") == ","


# ---------------------------------------------------------------------------
# L2: Domain sanity — ANAC CSV parsing from fixtures
# SOURCE: dati.anticorruzione.it/opendata — CIG dataset field names confirmed
# from PNRR datibenecomune documentation (pnrr.datibenecomune.it/fonti/anac)
# ---------------------------------------------------------------------------


class TestCigCsvParsing:
    """Test parsing of CIG CSV fixture data."""

    def test_parse_cig_fixture(self) -> None:
        """L2: CIG CSV must contain expected ANAC fields.
        # SOURCE: pnrr.datibenecomune.it/fonti/anac/informazioni-cig.html — field names
        """
        csv_text = (FIXTURES / "anac_cig_sample.csv").read_text(encoding="utf-8")
        rows = parse_cig_csv(csv_text)
        assert len(rows) == 3

        first = rows[0]
        assert first["cig"] == "Z123456789"
        assert first["denominazione_amministrazione_appaltante"] == "COMUNE DI ROMA"
        assert first["cf_amministrazione_appaltante"] == "02438750586"
        assert first["cod_cpv"] == "90911200-8"
        assert first["tipo_scelta_contraente"] == "PROCEDURA APERTA"

    def test_buyer_cf_is_valid_codice_fiscale(self) -> None:
        """L2: Buyer CF for Comune di Roma must be 02438750586.
        # SOURCE: agenziagov.it — Codice Fiscale Comune di Roma
        """
        csv_text = (FIXTURES / "anac_cig_sample.csv").read_text(encoding="utf-8")
        rows = parse_cig_csv(csv_text)
        roma = rows[0]
        cf = roma["cf_amministrazione_appaltante"]
        assert cf == "02438750586"
        assert len(cf) == 11  # PA codice fiscale is always 11 digits

    def test_amounts_parseable(self) -> None:
        """All importo_complessivo_gara must parse to Decimal."""
        csv_text = (FIXTURES / "anac_cig_sample.csv").read_text(encoding="utf-8")
        rows = parse_cig_csv(csv_text)
        for row in rows:
            amount = _parse_decimal(row["importo_complessivo_gara"])
            assert amount is not None, f"Could not parse amount: {row['importo_complessivo_gara']}"
            assert amount > 0


class TestAggiudicatariParsing:
    def test_parse_aggiudicatari_fixture(self) -> None:
        csv_text = (FIXTURES / "anac_aggiudicatari_sample.csv").read_text(encoding="utf-8")
        by_cig = parse_aggiudicatari_csv(csv_text)
        assert len(by_cig) == 2
        assert "Z123456789" in by_cig
        assert by_cig["Z123456789"]["ragione_sociale"] == "Puliservice S.r.l."

    def test_aggiudicatari_keyed_by_cig(self) -> None:
        csv_text = (FIXTURES / "anac_aggiudicatari_sample.csv").read_text(encoding="utf-8")
        by_cig = parse_aggiudicatari_csv(csv_text)
        # CIG Z987654321 has no winner in fixture
        assert "Z987654321" not in by_cig


# ---------------------------------------------------------------------------
# L1: Contract field mapping
# ---------------------------------------------------------------------------


class TestMapCigToContract:
    def test_basic_mapping(self) -> None:
        csv_text = (FIXTURES / "anac_cig_sample.csv").read_text(encoding="utf-8")
        rows = parse_cig_csv(csv_text)
        agg_text = (FIXTURES / "anac_aggiudicatari_sample.csv").read_text(encoding="utf-8")
        by_cig = parse_aggiudicatari_csv(agg_text)

        cig_row = rows[0]
        agg_row = by_cig.get(cig_row["cig"])
        fields = _map_cig_to_contract(cig_row, agg_row)

        assert fields["ocid"] == "ocds-hu01ve-Z123456789"
        assert fields["buyer_name"] == "COMUNE DI ROMA"
        assert fields["buyer_cf"] == "02438750586"
        assert fields["supplier_name"] == "Puliservice S.r.l."
        assert fields["supplier_cf"] == "12345678901"
        assert fields["cpv_code"] == "90911200-8"
        assert fields["procedure_type"] == "PROCEDURA APERTA"
        assert fields["publication_date"] == date(2024, 1, 15)
        assert fields["amount_original"] == Decimal("50000.00")
        assert fields["amount_awarded"] == Decimal("48500.00")
        assert fields["n_bids"] == 3

    def test_mapping_without_aggiudicatari(self) -> None:
        """Contract without winner data should still work."""
        csv_text = (FIXTURES / "anac_cig_sample.csv").read_text(encoding="utf-8")
        rows = parse_cig_csv(csv_text)
        # Z987654321 has no aggiudicatari
        fields = _map_cig_to_contract(rows[1], None)
        assert fields["buyer_name"] == "MINISTERO DELL'INTERNO"
        assert fields["supplier_name"] is None
        assert fields["amount_awarded"] is None

    def test_duration_computed(self) -> None:
        """Duration = scadenza - pubblicazione (if both present)."""
        csv_text = (FIXTURES / "anac_cig_sample.csv").read_text(encoding="utf-8")
        rows = parse_cig_csv(csv_text)
        fields = _map_cig_to_contract(rows[0], None)
        # 2024-02-15 - 2024-01-15 = 31 days
        assert fields["contract_duration_days"] == 31
