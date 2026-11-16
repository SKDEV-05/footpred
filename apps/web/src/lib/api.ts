import type {
  AnalysisHistoryItem,
  CompetitionSummary,
  Country,
  Fixture,
  FixtureDetail,
  MatchAnalysis,
  Page,
  StatisticsResponse,
  SyncStatus,
  TeamSummary,
  TodayResponse,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

function buildUrl(
  endpoint: string,
  params: Record<string, string | number> = {},
): string {
  const query = new URLSearchParams(
    Object.entries(params).map(([key, value]) => [key, String(value)]),
  ).toString();
  return `${API_BASE_URL}${endpoint}${query ? `?${query}` : ""}`;
}

async function errorMessage(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({}));
  // The API error envelope is { error: { code, message } }.
  return (
    body?.error?.message ||
    body?.message ||
    `API request failed with status ${response.status}`
  );
}

export async function apiFetch<T>(
  endpoint: string,
  params: Record<string, string | number> = {},
): Promise<T> {
  const response = await fetch(buildUrl(endpoint, params), {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }

  return response.json();
}

export async function apiPost<T>(
  endpoint: string,
  params: Record<string, string | number> = {},
): Promise<T> {
  const response = await fetch(buildUrl(endpoint, params), {
    method: "POST",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }

  return response.json();
}

export const footballApi = {
  getFixtures: (params: Record<string, string | number>) =>
    apiFetch<Page<Fixture>>("/fixtures", params),
  getTodayFixtures: () => apiFetch<TodayResponse>("/fixtures/today"),
  getMatchDetails: (id: number) => apiFetch<FixtureDetail>(`/fixtures/${id}`),
  getMatchStatistics: (id: number) =>
    apiFetch<StatisticsResponse>(`/fixtures/${id}/statistics`),
  getCompetitions: () =>
    apiFetch<Page<CompetitionSummary>>("/competitions", { page_size: 100 }),
  getCountries: () => apiFetch<Page<Country>>("/countries", { page_size: 100 }),
  searchTeams: (query: string) =>
    apiFetch<Page<TeamSummary>>("/teams", { q: query, page_size: 20 }),
  getSyncStatus: () => apiFetch<SyncStatus>("/sync/status"),
  analyzeMatch: (id: number, force = false) =>
    apiPost<MatchAnalysis>(
      `/analysis/matches/${id}`,
      force ? { force: "true" } : {},
    ),
  getAnalysis: (analysisId: number) =>
    apiFetch<MatchAnalysis>(`/analysis/${analysisId}`),
  getMatchAnalysisHistory: (id: number) =>
    apiFetch<AnalysisHistoryItem[]>(`/analysis/matches/${id}/history`),
};
