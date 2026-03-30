// TypeScript interfaces mirroring backend Pydantic schemas (schemas.py)

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  version: string;
}

// ---------------------------------------------------------------------------
// Politicians
// ---------------------------------------------------------------------------

export interface PoliticianSummary {
  id: string;
  full_name: string;
  current_party: string | null;
  current_chamber: string | null;
  region: string | null;
  photo_url: string | null;
}

export interface PoliticianDetail extends PoliticianSummary {
  camera_uri: string | null;
  senato_uri: string | null;
  openpolis_id: number | null;
  birth_date: string | null;
  coherence_score: number | null;
  promise_count: number;
  vote_count: number;
}

export interface VoteResponse {
  id: string;
  session_date: string;
  subject: string;
  vote_value: string | null;
  legislative_act_id: string | null;
}

export interface PromiseResponse {
  id: string;
  sentence: string;
  topic: string | null;
  specificity_score: number | null;
  status: string; // "pending" | "kept" | "broken" | "ambiguous"
  confidence: number | null;
  human_verified: boolean;
}

// ---------------------------------------------------------------------------
// Contracts
// ---------------------------------------------------------------------------

export interface ContractSummary {
  id: string;
  buyer_name: string;
  supplier_name: string | null;
  amount_awarded: number | null;
  procedure_type: string | null;
  award_date: string | null;
  risk_score: number;
  n_bids: number | null;
}

export interface AnomalyFlagResponse {
  flag_type: string;
  severity: string | null;
  details: Record<string, unknown> | null;
  ml_anomaly_score: number | null;
}

export interface ContractDetail extends ContractSummary {
  ocid: string | null;
  buyer_cf: string | null;
  buyer_region: string | null;
  buyer_province: string | null;
  supplier_cf: string | null;
  cpv_code: string | null;
  amount_original: number | null;
  publication_date: string | null;
  contract_duration_days: number | null;
  source_url: string | null;
  anomaly_flags: AnomalyFlagResponse[];
}

// ---------------------------------------------------------------------------
// Courts
// ---------------------------------------------------------------------------

export interface TribunalSummary {
  id: string;
  name: string;
  type: string | null;
  region: string | null;
  province: string | null;
  lat: number | null;
  lon: number | null;
}

export interface CourtStatResponse {
  period: string;
  case_category: string | null;
  pending_cases: number | null;
  new_cases: number | null;
  resolved_cases: number | null;
  avg_duration_days: number | null;
  clearance_rate: number | null;
}

export interface TribunalDetail extends TribunalSummary {
  stats: CourtStatResponse[];
}

export interface TribunalRanking {
  name: string;
  region: string | null;
  province: string | null;
  lat: number | null;
  lon: number | null;
  metric_value: number | null;
  metric_name: string;
  year: number | null;
}

export interface NationalYearStats {
  year: number;
  total_incoming: number;
  total_resolved: number;
  total_pending: number;
  clearance_rate: number | null;
  avg_disposition_time: number | null;
}

// ---------------------------------------------------------------------------
// Laws
// ---------------------------------------------------------------------------

export interface LawSummary {
  id: string;
  title: string;
  act_type: string | null;
  chamber: string | null;
  status: string | null;
  presentation_date: string | null;
}

export interface LawDetail extends LawSummary {
  full_text: string | null;
  plain_translation: Record<string, unknown> | null;
  translated_at: string | null;
  source_uri: string | null;
}

// ---------------------------------------------------------------------------
// Magistrates
// ---------------------------------------------------------------------------

export interface MagistrateSummary {
  id: string;
  full_name: string;
  role: string | null;
  section: string | null;
  tribunal_id: string | null;
  photo_url: string | null;
}

export interface MagistrateStatResponse {
  period: string;
  pending_cases: number | null;
  new_cases: number | null;
  resolved_cases: number | null;
  avg_duration_days: number | null;
  clearance_rate: number | null;
  tribunal_avg_duration: number | null;
}

export interface MagistrateDetail extends MagistrateSummary {
  birth_date: string | null;
  csm_id: string | null;
  in_office_since: string | null;
  transfer_history: Record<string, unknown> | null;
  disciplinary_records: Record<string, unknown> | null;
  stats: MagistrateStatResponse[];
}

// ---------------------------------------------------------------------------
// Dossier
// ---------------------------------------------------------------------------

export interface AssetTimelineEntry {
  year: number;
  total_income: number | null;
  total_assets: number | null;
}

export interface PoliticianDossier {
  person_type: "politician";
  person_id: string;
  full_name: string;
  current_party: string | null;
  current_chamber: string | null;
  region: string | null;
  birth_date: string | null;
  photo_url: string | null;
  coherence_score: number | null;
  attendance_rate: number | null;
  total_votes: number;
  total_promises: number;
  promises_kept: number;
  promises_broken: number;
  promises_pending: number;
  promises: PromiseResponse[];
  recent_votes: VoteResponse[];
  asset_timeline: AssetTimelineEntry[];
  linked_contracts: ContractSummary[];
  legislative_acts_sponsored: LawSummary[];
  generated_at: string;
  data_sources: string[];
}

export interface MagistrateDossier {
  person_type: "magistrate";
  person_id: string;
  full_name: string;
  role: string | null;
  section: string | null;
  tribunal_name: string | null;
  tribunal_region: string | null;
  birth_date: string | null;
  photo_url: string | null;
  in_office_since: string | null;
  avg_duration_days: number | null;
  tribunal_avg_duration: number | null;
  performance_delta_pct: number | null;
  pending_cases: number | null;
  clearance_rate: number | null;
  transfer_history: Record<string, unknown> | null;
  disciplinary_records: Record<string, unknown> | null;
  stats_timeline: MagistrateStatResponse[];
  generated_at: string;
  data_sources: string[];
}

export interface InstitutionalDossier {
  person_type: "institutional";
  person_id: string;
  full_name: string;
  role_type: string;
  institution: string | null;
  region: string | null;
  in_office_since: string | null;
  in_office_until: string | null;
  previous_roles: Record<string, unknown> | null;
  linked_contracts: ContractSummary[];
  linked_contracts_count: number;
  generated_at: string;
  data_sources: string[];
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export interface SearchResult {
  entity_type: string;
  entity_id: string;
  title: string;
  snippet: string | null;
  score: number;
}
