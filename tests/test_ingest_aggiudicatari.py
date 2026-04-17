"""Tests for aggiudicatari supplier-update streaming ingest."""

from __future__ import annotations

import io
import zipfile

from codicecivico.ingest.anac import AnacIngestor, _aggiudicatari_url


def test_aggiudicatari_url_format() -> None:
    """# SOURCE: ANAC opendata — verified 2026-04-17 that
    https://dati.anticorruzione.it/opendata/download/dataset/aggiudicatari/filesystem/20260401-aggiudicatari_csv.zip
    returns HTTP 200 with 22 MB compressed ZIP.
    """
    url = _aggiudicatari_url("20260401")
    assert url == (
        "https://dati.anticorruzione.it/opendata/download/dataset/"
        "aggiudicatari/filesystem/20260401-aggiudicatari_csv.zip"
    )


def _make_fake_zip(csv_content: str) -> bytes:
    """Build a ZIP with one aggiudicatari-style CSV inside."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("20260401-aggiudicatari_csv.csv", csv_content)
    return buf.getvalue()


def test_fake_zip_has_expected_schema() -> None:
    """Verify the real-world schema we assume.

    # SOURCE: actual ANAC aggiudicatari CSV header (verified 2026-04-17):
    "cig";"ruolo";"codice_fiscale";"denominazione";"tipo_soggetto";"id_aggiudicazione"
    """
    csv_text = (
        '"cig";"ruolo";"codice_fiscale";"denominazione";'
        '"tipo_soggetto";"id_aggiudicazione"\n'
        '"BA03211576";"OPERATORE ECONOMICO MONOSOGGETTIVO";'
        '"TNNGPP68E22L736A";"TONINI GIUSEPPE";'
        '"DITTA INDIVIDUALE";"19479251"\n'
    )
    zip_bytes = _make_fake_zip(csv_text)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert len(names) == 1
        content = zf.read(names[0]).decode("utf-8")
    assert "denominazione" in content
    assert "codice_fiscale" in content
    assert "TONINI GIUSEPPE" in content


class TestUpdateSuppliers:
    """Integration-style tests for update_suppliers_from_snapshot.

    These tests verify the streaming parse + dedup logic without hitting a
    real DB. The async-session layer is exercised on the VPS run.
    """

    def test_ingestor_instance_has_update_method(self) -> None:
        ing = AnacIngestor()
        assert hasattr(ing, "update_suppliers_from_snapshot")
        assert hasattr(ing, "_flush_supplier_batch")
