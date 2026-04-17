// Server-side API fetch wrapper — all calls go through Next.js server to FastAPI backend
// IMPORTANT: this file runs ONLY on the server (RSC / route handlers)

import type {
  ContractDetail,
  ContractSummary,
  HealthResponse,
  LawDetail,
  LawSummary,
  MagistrateDossier,
  MagistrateDetail,
  MagistrateSummary,
  NationalYearStats,
  InstitutionalDossier,
  PoliticianDetail,
  PoliticianDossier,
  PoliticianSummary,
  PromiseResponse,
  SearchResult,
  TribunalDetail,
  TribunalRanking,
  TribunalSummary,
  VoteResponse,
} from "./types";

const API_URL = process.env.API_URL || "http://localhost:8000";
const PREFIX = "/api/v1";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(
  path: string,
  options?: { revalidate?: number },
): Promise<T> {
  const url = `${API_URL}${PREFIX}${path}`;
  const res = await fetch(url, {
    next: { revalidate: options?.revalidate ?? 300 },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `API ${res.status}: ${url}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export function fetchHealth() {
  return apiFetch<HealthResponse>("/health", { revalidate: 60 });
}

export interface StatsOverview {
  politicians: number;
  contracts: number;
  anomaly_flags: number;
  high_risk_contracts: number;
  tribunals: number;
  laws: number;
  promises: number;
  court_stats: number;
}

export function fetchStatsOverview() {
  return apiFetch<StatsOverview>("/stats/overview", { revalidate: 300 });
}

export interface AnomalyRuleCalibration {
  flag_type: string;
  total_flags: number;
  pct_of_contracts: number;
  severity_high: number;
  severity_medium: number;
  severity_low: number;
}

export interface AnomalyCalibrationResponse {
  total_contracts: number;
  flagged_contracts: number;
  flagged_pct: number;
  contracts_high_risk: number;
  contracts_medium_risk: number;
  rules: AnomalyRuleCalibration[];
  thresholds: Record<string, number | string>;
}

export function fetchAnomalyCalibration() {
  return apiFetch<AnomalyCalibrationResponse>(
    "/stats/anomaly-calibration",
    { revalidate: 300 },
  );
}

// ---------------------------------------------------------------------------
// Politicians
// ---------------------------------------------------------------------------

interface PoliticianParams {
  party?: string;
  chamber?: string;
  region?: string;
  q?: string;
  page?: number;
  per_page?: number;
}

export function fetchPoliticians(params: PoliticianParams = {}) {
  const sp = new URLSearchParams();
  if (params.party) sp.set("party", params.party);
  if (params.chamber) sp.set("chamber", params.chamber);
  if (params.region) sp.set("region", params.region);
  if (params.q) sp.set("q", params.q);
  if (params.page) sp.set("page", String(params.page));
  if (params.per_page) sp.set("per_page", String(params.per_page));
  const qs = sp.toString();
  return apiFetch<PoliticianSummary[]>(`/politicians${qs ? `?${qs}` : ""}`);
}

export function fetchPolitician(id: string) {
  return apiFetch<PoliticianDetail>(`/politicians/${id}`, { revalidate: 60 });
}

export function fetchPoliticianVotes(
  id: string,
  page = 1,
  per_page = 20,
) {
  return apiFetch<VoteResponse[]>(
    `/politicians/${id}/votes?page=${page}&per_page=${per_page}`,
  );
}

export function fetchPoliticianPromises(id: string, status?: string) {
  const qs = status ? `?status=${status}` : "";
  return apiFetch<PromiseResponse[]>(`/politicians/${id}/promises${qs}`);
}

// ---------------------------------------------------------------------------
// Contracts
// ---------------------------------------------------------------------------

interface ContractParams {
  region?: string;
  cpv?: string;
  amount_min?: number;
  amount_max?: number;
  risk_min?: number;
  page?: number;
  per_page?: number;
}

export function fetchContracts(params: ContractParams = {}) {
  const sp = new URLSearchParams();
  if (params.region) sp.set("region", params.region);
  if (params.cpv) sp.set("cpv", params.cpv);
  if (params.amount_min != null) sp.set("amount_min", String(params.amount_min));
  if (params.amount_max != null) sp.set("amount_max", String(params.amount_max));
  if (params.risk_min != null) sp.set("risk_min", String(params.risk_min));
  if (params.page) sp.set("page", String(params.page));
  if (params.per_page) sp.set("per_page", String(params.per_page));
  const qs = sp.toString();
  return apiFetch<ContractSummary[]>(`/contracts${qs ? `?${qs}` : ""}`);
}

export function fetchContractAnomalies(limit = 20) {
  return apiFetch<ContractSummary[]>(`/contracts/anomalies?limit=${limit}`);
}

export function fetchContract(id: string) {
  return apiFetch<ContractDetail>(`/contracts/${id}`, { revalidate: 60 });
}

// ---------------------------------------------------------------------------
// Courts
// ---------------------------------------------------------------------------

export function fetchCourts(region?: string) {
  const qs = region ? `?region=${region}` : "";
  return apiFetch<TribunalSummary[]>(`/courts${qs}`);
}

interface RankingParams {
  metric?: string;
  year?: number;
  category?: string;
  order?: "asc" | "desc";
  limit?: number;
}

export function fetchCourtRankings(params: RankingParams = {}) {
  const sp = new URLSearchParams();
  if (params.metric) sp.set("metric", params.metric);
  if (params.year) sp.set("year", String(params.year));
  if (params.category) sp.set("category", params.category);
  if (params.order) sp.set("order", params.order);
  if (params.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiFetch<TribunalRanking[]>(`/courts/rankings${qs ? `?${qs}` : ""}`);
}

export function fetchNationalStats(category?: string) {
  const qs = category ? `?category=${category}` : "";
  return apiFetch<NationalYearStats[]>(`/courts/stats/national${qs}`);
}

export function fetchCourt(id: string) {
  return apiFetch<TribunalDetail>(`/courts/${id}`, { revalidate: 60 });
}

// ---------------------------------------------------------------------------
// Laws
// ---------------------------------------------------------------------------

interface LawParams {
  chamber?: string;
  status?: string;
  page?: number;
  per_page?: number;
}

export function fetchLaws(params: LawParams = {}) {
  const sp = new URLSearchParams();
  if (params.chamber) sp.set("chamber", params.chamber);
  if (params.status) sp.set("status", params.status);
  if (params.page) sp.set("page", String(params.page));
  if (params.per_page) sp.set("per_page", String(params.per_page));
  const qs = sp.toString();
  return apiFetch<LawSummary[]>(`/laws${qs ? `?${qs}` : ""}`);
}

export function fetchLaw(id: string) {
  return apiFetch<LawDetail>(`/laws/${id}`, { revalidate: 60 });
}

// ---------------------------------------------------------------------------
// Magistrates
// ---------------------------------------------------------------------------

interface MagistrateParams {
  role?: string;
  tribunal_id?: string;
  q?: string;
  page?: number;
  per_page?: number;
}

export function fetchMagistrates(params: MagistrateParams = {}) {
  const sp = new URLSearchParams();
  if (params.role) sp.set("role", params.role);
  if (params.tribunal_id) sp.set("tribunal_id", params.tribunal_id);
  if (params.q) sp.set("q", params.q);
  if (params.page) sp.set("page", String(params.page));
  if (params.per_page) sp.set("per_page", String(params.per_page));
  const qs = sp.toString();
  return apiFetch<MagistrateSummary[]>(`/magistrates${qs ? `?${qs}` : ""}`);
}

export function fetchMagistrate(id: string) {
  return apiFetch<MagistrateDetail>(`/magistrates/${id}`, { revalidate: 60 });
}

// ---------------------------------------------------------------------------
// Dossier
// ---------------------------------------------------------------------------

export function fetchPoliticianDossier(id: string) {
  return apiFetch<PoliticianDossier>(`/dossier/politician/${id}`, {
    revalidate: 60,
  });
}

export function fetchMagistrateDossier(id: string) {
  return apiFetch<MagistrateDossier>(`/dossier/magistrate/${id}`, {
    revalidate: 60,
  });
}

export function fetchInstitutionalDossier(id: string) {
  return apiFetch<InstitutionalDossier>(`/dossier/institutional/${id}`, {
    revalidate: 60,
  });
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export function fetchSearch(q: string, type?: string, limit = 20) {
  const sp = new URLSearchParams({ q, limit: String(limit) });
  if (type) sp.set("type", type);
  return apiFetch<SearchResult[]>(`/search?${sp.toString()}`);
}
