"""ANAC (Anticorruzione) procurement data ingestor.

Data source: https://dati.anticorruzione.it/opendata
Format: Monthly ZIP → CSV files for CIG (tenders), aggiudicatari (winners)

Bulk download URLs (verified 2026-03-23):
- CIG:          cig_csv_{YYYY}_{MM}.zip  (tender info, buyer, CPV, amounts)
- Aggiudicatari: {YYYYMMDD}-aggiudicatari_csv.zip (award winners, supplier info)

We join CIG + aggiudicatari by CIG code to build Contract records.
"""

import csv
import io
import logging
import zipfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from codicecivico.ingest.base import BaseIngestor
from codicecivico.models import Contract

logger = logging.getLogger(__name__)

# ANAC WAF requires browser-like User-Agent
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}

ANAC_BASE = "https://dati.anticorruzione.it/opendata/download/dataset"
HTTP_TIMEOUT = 120.0  # seconds — ZIP files can be large


def _cig_url(year: int, month: int) -> str:
    """Build download URL for a CIG monthly CSV ZIP."""
    return f"{ANAC_BASE}/cig-{year}/filesystem/cig_csv_{year}_{month:02d}.zip"


def _aggiudicatari_url(snapshot_date: str) -> str:
    """Build download URL for aggiudicatari dataset.

    snapshot_date format: YYYYMMDD (e.g. '20250201').
    """
    return (
        f"{ANAC_BASE}/aggiudicatari/filesystem/"
        f"{snapshot_date}-aggiudicatari_csv.zip"
    )


def _parse_date_anac(raw: str) -> date | None:
    """Parse ANAC date formats: YYYY-MM-DD, DD/MM/YYYY, or empty."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(raw: str) -> Decimal | None:
    """Parse an amount string to Decimal, auto-detecting italian vs english format.

    - "1234567.89"    -> 1234567.89 (english, dot = decimal)
    - "1234567,89"    -> 1234567.89 (italian, comma = decimal)
    - "1.234.567,89"  -> 1234567.89 (italian: dots = thousands, comma = decimal)
    - "1,234,567.89"  -> 1234567.89 (english: commas = thousands, dot = decimal)

    The last separator wins as the decimal mark when both are present.
    ANAC open-data CSVs use the english convention; older government
    Excel exports use the italian one. Robust to both.
    """
    if not raw or not raw.strip():
        return None
    try:
        s = raw.strip()
        has_dot = "." in s
        has_comma = "," in s
        if has_dot and has_comma:
            if s.rindex(",") > s.rindex("."):
                cleaned = s.replace(".", "").replace(",", ".")
            else:
                cleaned = s.replace(",", "")
        elif has_comma:
            cleaned = s.replace(",", ".")
        else:
            cleaned = s
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _detect_delimiter(sample: str) -> str:
    """Detect CSV delimiter (comma or semicolon) from first line."""
    first_line = sample.split("\n")[0]
    if first_line.count(";") > first_line.count(","):
        return ";"
    return ","


async def _download_zip(url: str) -> bytes | None:
    """Download a ZIP file from ANAC. Returns bytes or None on failure."""
    logger.info("Downloading %s ...", url)
    async with httpx.AsyncClient(headers=_HEADERS, timeout=HTTP_TIMEOUT) as client:
        try:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPStatusError as exc:
            logger.warning("HTTP %d for %s: %s", exc.response.status_code, url, exc)
            return None
        except httpx.RequestError as exc:
            logger.warning("Request error for %s: %s", url, exc)
            return None


def _extract_csv_from_zip(zip_bytes: bytes, pattern: str = ".csv") -> str:
    """Extract the first CSV file from a ZIP archive, return content as string."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(pattern)]
        if not csv_names:
            msg = f"No {pattern} file found in ZIP"
            raise ValueError(msg)
        # Pick the largest CSV (main data file)
        csv_name = max(csv_names, key=lambda n: zf.getinfo(n).file_size)
        logger.info("Extracting %s from ZIP", csv_name)
        raw = zf.read(csv_name)
        # Try UTF-8 first, fall back to latin-1
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("latin-1", errors="replace")


def parse_cig_csv(csv_text: str) -> list[dict[str, str]]:
    """Parse CIG CSV text into list of row dicts."""
    delimiter = _detect_delimiter(csv_text)
    reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)
    return list(reader)


def parse_aggiudicatari_csv(csv_text: str) -> dict[str, dict[str, str]]:
    """Parse aggiudicatari CSV, return dict keyed by CIG code.

    If multiple winners per CIG, keeps the first one (primary awardee).
    """
    delimiter = _detect_delimiter(csv_text)
    reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)
    by_cig: dict[str, dict[str, str]] = {}
    for row in reader:
        cig = row.get("cig", "").strip()
        if cig and cig not in by_cig:
            by_cig[cig] = row
    return by_cig


def _map_cig_to_contract(
    cig_row: dict[str, str],
    agg_row: dict[str, str] | None = None,
) -> dict[str, object]:
    """Map CIG + aggiudicatari CSV rows to Contract model fields."""
    cig_code = cig_row.get("cig", "").strip()

    # Buyer info from CIG dataset
    buyer_name = (
        cig_row.get("denominazione_amministrazione_appaltante", "")
        or cig_row.get("denominazione_sa", "")
        or ""
    ).strip()
    buyer_cf = (
        cig_row.get("cf_amministrazione_appaltante", "")
        or cig_row.get("cf_sa", "")
        or ""
    ).strip()

    # Region/province from CIG
    buyer_region = cig_row.get("sezione_regionale", "").strip() or None
    buyer_province = cig_row.get("provincia", "").strip() or None

    # Amount: use importo_complessivo_gara (total tender) or importo_lotto
    amount_str = (
        cig_row.get("importo_complessivo_gara", "")
        or cig_row.get("importo_lotto", "")
        or ""
    )
    amount = _parse_decimal(amount_str)

    # Dates
    pub_date = _parse_date_anac(cig_row.get("data_pubblicazione", ""))

    # Procedure type
    procedure = cig_row.get("tipo_scelta_contraente", "").strip() or None

    # CPV code
    cpv = cig_row.get("cod_cpv", "").strip() or None

    # Supplier info from aggiudicatari (if available)
    supplier_name = None
    supplier_cf = None
    award_date = None
    n_bids = None
    amount_awarded = None

    if agg_row:
        supplier_name = (
            agg_row.get("ragione_sociale", "")
            or agg_row.get("denominazione", "")
            or ""
        ).strip() or None
        supplier_cf = (
            agg_row.get("codice_fiscale", "")
            or agg_row.get("cf", "")
            or ""
        ).strip() or None
        award_date = _parse_date_anac(agg_row.get("data_aggiudicazione", ""))
        n_bids_str = agg_row.get("numero_offerte_ricevute", "").strip()
        if n_bids_str and n_bids_str.isdigit():
            n_bids = int(n_bids_str)
        awarded_str = agg_row.get("importo_aggiudicazione", "")
        if awarded_str:
            amount_awarded = _parse_decimal(awarded_str)

    # Duration: compute from dates if possible
    duration_days = None
    scadenza_str = cig_row.get("data_scadenza_offerta", "")
    scadenza = _parse_date_anac(scadenza_str)
    if pub_date and scadenza and scadenza > pub_date:
        duration_days = (scadenza - pub_date).days

    return {
        "ocid": f"ocds-hu01ve-{cig_code}" if cig_code else None,
        "buyer_name": buyer_name or "N/A",
        "buyer_cf": buyer_cf or None,
        "buyer_region": buyer_region,
        "buyer_province": buyer_province,
        "supplier_name": supplier_name,
        "supplier_cf": supplier_cf,
        "cpv_code": cpv,
        "amount_awarded": amount_awarded,
        "amount_original": amount,
        "procedure_type": procedure,
        "publication_date": pub_date,
        "award_date": award_date,
        "n_bids": n_bids,
        "contract_duration_days": duration_days,
        "source_url": "https://dati.anticorruzione.it/opendata/dataset/cig",
    }


class AnacIngestor(BaseIngestor):
    """Ingest public procurement data from ANAC bulk CSV datasets.

    Ingestion flow:
    1. Download CIG monthly ZIP (or range of months)
    2. Download aggiudicatari snapshot ZIP
    3. Parse both CSVs
    4. Join by CIG code
    5. Upsert into Contract table
    """

    source_name = "anac"

    async def ingest(
        self,
        session: AsyncSession,
        *,
        limit: int | None = None,
        year: int | None = None,
        month: int | None = None,
        aggiudicatari_snapshot: str | None = None,
    ) -> int:
        """Fetch and store ANAC procurement contracts.

        Args:
            session: Async DB session.
            limit: Max number of contracts to process (for testing).
            year: Year to ingest (default: current year).
            month: Month to ingest (default: current month - 1).
            aggiudicatari_snapshot: YYYYMMDD date for aggiudicatari ZIP.
        """
        log_entry = await self.log_ingestion_start(session)
        total = 0
        errors: dict[str, str] = {}

        if year is None:
            year = date.today().year
        if month is None:
            # Default to previous month (current month may not be published yet)
            today = date.today()
            if today.month == 1:
                month = 12
                year = today.year - 1
            else:
                month = today.month - 1

        try:
            # --- Step 1: Download CIG CSV ---
            cig_zip = await _download_zip(_cig_url(year, month))
            if cig_zip is None:
                errors["cig"] = f"Failed to download CIG for {year}-{month:02d}"
                await self.log_ingestion_end(
                    session, log_entry, records=0, status="failed", errors=errors,
                )
                await session.commit()
                return 0

            cig_csv_text = _extract_csv_from_zip(cig_zip)
            cig_rows = parse_cig_csv(cig_csv_text)
            logger.info("ANAC: parsed %d CIG rows for %d-%02d.", len(cig_rows), year, month)

            # --- Step 2: Download aggiudicatari (optional, best-effort) ---
            agg_by_cig: dict[str, dict[str, str]] = {}
            if aggiudicatari_snapshot:
                agg_zip = await _download_zip(_aggiudicatari_url(aggiudicatari_snapshot))
                if agg_zip:
                    agg_csv_text = _extract_csv_from_zip(agg_zip)
                    agg_by_cig = parse_aggiudicatari_csv(agg_csv_text)
                    logger.info("ANAC: loaded %d aggiudicatari records.", len(agg_by_cig))
                else:
                    logger.warning("ANAC: could not download aggiudicatari, proceeding without.")

            # --- Step 3: Map and upsert contracts ---
            for i, cig_row in enumerate(cig_rows):
                if limit and i >= limit:
                    break

                cig_code = cig_row.get("cig", "").strip()
                if not cig_code:
                    continue

                agg_row = agg_by_cig.get(cig_code)
                fields = _map_cig_to_contract(cig_row, agg_row)

                ocid = fields["ocid"]
                if not ocid:
                    continue

                # Upsert by ocid
                stmt = select(Contract).where(Contract.ocid == ocid)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update supplier info if we now have aggiudicatari data
                    if agg_row and not existing.supplier_name:
                        existing.supplier_name = fields["supplier_name"]  # type: ignore[assignment]
                        existing.supplier_cf = fields["supplier_cf"]  # type: ignore[assignment]
                        existing.amount_awarded = fields["amount_awarded"]  # type: ignore[assignment]
                        existing.award_date = fields["award_date"]  # type: ignore[assignment]
                        existing.n_bids = fields["n_bids"]  # type: ignore[assignment]
                    continue

                contract = Contract(**fields)
                session.add(contract)
                total += 1

                # Batch flush every 1000 records
                if total % 1000 == 0:
                    await session.flush()
                    logger.info("ANAC: %d contracts upserted so far...", total)

            await session.flush()

            checkpoint = f"{year}-{month:02d}"
            await self.log_ingestion_end(
                session, log_entry, records=total, checkpoint=checkpoint,
            )
            await session.commit()
            logger.info("ANAC: ingestion complete — %d new contracts.", total)

        except Exception as exc:
            errors["exception"] = str(exc)
            await self.log_ingestion_end(
                session, log_entry, records=total, status="failed", errors=errors,
            )
            await session.commit()
            raise

        return total

    async def get_checkpoint(self, session: AsyncSession) -> str | None:
        """Get last ingested month (YYYY-MM format)."""
        return await self.get_last_checkpoint(session)
