"""Pydantic response schemas for the API."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str


class HealthDetailedResponse(HealthResponse):
    checks: dict[str, object] = {}


class StatsOverview(BaseModel):
    """Aggregate counts for the dashboard homepage."""

    politicians: int
    contracts: int
    anomaly_flags: int
    high_risk_contracts: int
    tribunals: int
    laws: int
    promises: int
    court_stats: int


# ---------------------------------------------------------------------------
# Politicians
# ---------------------------------------------------------------------------


class PoliticianSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    current_party: str | None
    current_chamber: str | None
    region: str | None
    photo_url: str | None


class PoliticianDetail(PoliticianSummary):
    camera_uri: str | None
    senato_uri: str | None
    openpolis_id: int | None
    birth_date: date | None
    coherence_score: float | None = None
    promise_count: int = 0
    vote_count: int = 0


class VoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_date: date
    subject: str
    vote_value: str | None
    legislative_act_id: uuid.UUID | None


class PromiseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sentence: str
    topic: str | None
    specificity_score: float | None
    status: str
    confidence: float | None
    human_verified: bool


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------


class ContractSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    buyer_name: str
    supplier_name: str | None
    amount_awarded: Decimal | None
    amount_original: Decimal | None
    procedure_type: str | None
    award_date: date | None
    risk_score: float
    n_bids: int | None


class ContractDetail(ContractSummary):
    ocid: str | None
    buyer_cf: str | None
    buyer_region: str | None
    buyer_province: str | None
    supplier_cf: str | None
    cpv_code: str | None
    publication_date: date | None
    contract_duration_days: int | None
    source_url: str | None
    anomaly_flags: list["AnomalyFlagResponse"] = []


class AnomalyFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    flag_type: str
    severity: str | None
    details: dict | None
    ml_anomaly_score: float | None


# ---------------------------------------------------------------------------
# Courts
# ---------------------------------------------------------------------------


class TribunalSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: str | None
    region: str | None
    province: str | None
    lat: float | None
    lon: float | None


class CourtStatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: date
    case_category: str | None
    pending_cases: int | None
    new_cases: int | None
    resolved_cases: int | None
    avg_duration_days: float | None
    clearance_rate: float | None


class TribunalDetail(TribunalSummary):
    stats: list[CourtStatResponse] = []


class TribunalRanking(BaseModel):
    """Tribunal with a single metric for ranking."""

    name: str
    region: str | None
    province: str | None
    lat: float | None
    lon: float | None
    metric_value: float | None
    metric_name: str
    year: int | None


class NationalYearStats(BaseModel):
    """Aggregated national court statistics for a single year."""

    year: int
    total_incoming: int
    total_resolved: int
    total_pending: int
    clearance_rate: float | None
    avg_disposition_time: float | None


# ---------------------------------------------------------------------------
# Laws
# ---------------------------------------------------------------------------


class LawSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    act_type: str | None
    chamber: str | None
    status: str | None
    presentation_date: date | None


class LawDetail(LawSummary):
    full_text: str | None
    plain_translation: dict | None
    translated_at: datetime | None
    source_uri: str | None


class TranslationResponse(BaseModel):
    """Response for the translate endpoint."""
    law_id: uuid.UUID
    title: str
    translation: dict
    translated_at: datetime | None
    cached: bool


# ---------------------------------------------------------------------------
# Magistrates
# ---------------------------------------------------------------------------


class MagistrateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    role: str | None
    section: str | None
    tribunal_id: uuid.UUID | None
    photo_url: str | None


class MagistrateStatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: date
    pending_cases: int | None
    new_cases: int | None
    resolved_cases: int | None
    avg_duration_days: float | None
    clearance_rate: float | None
    tribunal_avg_duration: float | None


class MagistrateDetail(MagistrateSummary):
    birth_date: date | None
    csm_id: str | None
    in_office_since: date | None
    transfer_history: dict | None
    disciplinary_records: dict | None
    stats: list[MagistrateStatResponse] = []


# ---------------------------------------------------------------------------
# Institutional Figures
# ---------------------------------------------------------------------------


class InstitutionalFigureSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    role_type: str
    institution: str | None
    region: str | None
    in_office_since: date | None
    in_office_until: date | None
    linked_contracts_count: int


# ---------------------------------------------------------------------------
# Dossier (aggregated profile for any institutional figure)
# ---------------------------------------------------------------------------


class AssetTimelineEntry(BaseModel):
    year: int
    total_income: Decimal | None
    total_assets: Decimal | None


class DossierSection(BaseModel):
    """A section of the dossier with title and content."""
    title: str
    items: list[dict] = []
    summary: str | None = None


class PoliticianDossier(BaseModel):
    """Complete auto-generated dossier for a politician."""
    person_type: str = "politician"
    person_id: uuid.UUID
    full_name: str
    current_party: str | None
    current_chamber: str | None
    region: str | None
    birth_date: date | None
    photo_url: str | None

    # Aggregated scores
    coherence_score: float | None = None
    attendance_rate: float | None = None
    total_votes: int = 0
    total_promises: int = 0
    promises_kept: int = 0
    promises_broken: int = 0
    promises_pending: int = 0

    # Sections
    promises: list[PromiseResponse] = []
    recent_votes: list[VoteResponse] = []
    asset_timeline: list[AssetTimelineEntry] = []
    linked_contracts: list[ContractSummary] = []
    legislative_acts_sponsored: list[LawSummary] = []

    # Metadata
    generated_at: datetime
    data_sources: list[str] = []


class MagistrateDossier(BaseModel):
    """Complete auto-generated dossier for a magistrate."""
    person_type: str = "magistrate"
    person_id: uuid.UUID
    full_name: str
    role: str | None
    section: str | None
    tribunal_name: str | None = None
    tribunal_region: str | None = None
    birth_date: date | None
    photo_url: str | None
    in_office_since: date | None

    # Performance vs tribunal average
    avg_duration_days: float | None = None
    tribunal_avg_duration: float | None = None
    performance_delta_pct: float | None = None
    pending_cases: int | None = None
    clearance_rate: float | None = None

    # History
    transfer_history: dict | None = None
    disciplinary_records: dict | None = None
    stats_timeline: list[MagistrateStatResponse] = []

    # Metadata
    generated_at: datetime
    data_sources: list[str] = []


class InstitutionalDossier(BaseModel):
    """Complete auto-generated dossier for other institutional figures."""
    person_type: str = "institutional"
    person_id: uuid.UUID
    full_name: str
    role_type: str
    institution: str | None
    region: str | None
    in_office_since: date | None
    in_office_until: date | None

    # Connected data
    previous_roles: dict | None = None
    linked_contracts: list[ContractSummary] = []
    linked_contracts_count: int = 0

    # Metadata
    generated_at: datetime
    data_sources: list[str] = []


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchResult(BaseModel):
    entity_type: str  # politician, contract, law, tribunal
    entity_id: uuid.UUID
    title: str
    snippet: str | None = None
    score: float = 0.0


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class PaginatedResponse(BaseModel):
    items: list[object]
    total: int
    page: int
    per_page: int
