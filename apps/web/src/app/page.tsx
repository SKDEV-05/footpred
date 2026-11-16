"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { footballApi } from "@/lib/api";
import type { Fixture, SyncStatus, TeamSummary } from "@/types";
import {
  dateRangeForFilter,
  formatKickoff,
  TIME_FILTERS,
  type TimeFilter,
} from "@/lib/dates";
import { Button } from "@/components/ui/button";
import { TeamCrest } from "@/components/TeamCrest";
import { StatusBadge } from "@/components/StatusBadge";

const PAGE_SIZE = 100;

interface FilterOption {
  id: number;
  name: string;
}

/**
 * Merge option lists without inventing entries. Incoming items fill gaps left by a failed
 * reference request; an option that already exists is never overwritten.
 */
function mergeOptions(current: FilterOption[], incoming: FilterOption[]): FilterOption[] {
  const byId = new Map(current.map((item) => [item.id, item]));
  for (const item of incoming) {
    if (!byId.has(item.id)) byId.set(item.id, item);
  }
  return Array.from(byId.values()).sort((a, b) => a.name.localeCompare(b.name));
}

function formatTimestamp(value: string | null): string {
  if (!value) return "never";
  return new Date(value).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Dashboard() {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeFilter, setTimeFilter] = useState<TimeFilter>("30d");
  const [competitionFilter, setCompetitionFilter] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [teamInput, setTeamInput] = useState("");
  const [teamResults, setTeamResults] = useState<TeamSummary[]>([]);
  const [teamOpen, setTeamOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<TeamSummary | null>(null);
  const [competitionOptions, setCompetitionOptions] = useState<FilterOption[]>([]);
  const [countryOptions, setCountryOptions] = useState<FilterOption[]>([]);
  const [referenceLoading, setReferenceLoading] = useState(true);
  const [referenceError, setReferenceError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const requestId = useRef(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const loadReference = useCallback(async () => {
    setReferenceLoading(true);
    setReferenceError(null);

    // A transient API restart must not leave the filters permanently empty, so the
    // reference requests are retried once before an error is reported.
    for (let attempt = 0; attempt < 2; attempt += 1) {
      const [competitionResult, countryResult] = await Promise.allSettled([
        footballApi.getCompetitions(),
        footballApi.getCountries(),
      ]);
      if (!mounted.current) return;

      if (competitionResult.status === "fulfilled") {
        setCompetitionOptions((current) =>
          mergeOptions(current, competitionResult.value.items),
        );
      }
      if (countryResult.status === "fulfilled") {
        setCountryOptions((current) => mergeOptions(current, countryResult.value.items));
      }
      if (
        competitionResult.status === "fulfilled" ||
        countryResult.status === "fulfilled"
      ) {
        setReferenceLoading(false);
        return;
      }
      if (attempt === 0) {
        await new Promise((resolve) => setTimeout(resolve, 1200));
        if (!mounted.current) return;
      }
    }

    setReferenceError("Filter options could not be loaded from the API.");
    setReferenceLoading(false);
  }, []);

  useEffect(() => {
    void loadReference();
  }, [loadReference]);

  const loadSyncStatus = useCallback(async () => {
    try {
      const status = await footballApi.getSyncStatus();
      if (mounted.current) setSyncStatus(status);
    } catch {
      // Freshness is advisory; a failure here must not hide fixtures. The badge
      // stays in its explicit "unknown" state until a retry succeeds.
    }
  }, []);

  useEffect(() => {
    void loadSyncStatus();
  }, [loadSyncStatus]);

  useEffect(() => {
    const timeout = setTimeout(() => setSearchTerm(searchInput.trim()), 350);
    return () => clearTimeout(timeout);
  }, [searchInput]);

  useEffect(() => {
    if (selectedTeam) return;
    const query = teamInput.trim();
    if (query.length < 2) {
      setTeamResults([]);
      return;
    }
    let active = true;
    const timeout = setTimeout(() => {
      footballApi
        .searchTeams(query)
        .then((result) => {
          if (!active) return;
          setTeamResults(result.items);
          setTeamOpen(true);
        })
        .catch(() => {
          if (active) setTeamResults([]);
        });
    }, 300);
    return () => {
      active = false;
      clearTimeout(timeout);
    };
  }, [teamInput, selectedTeam]);

  const fetchFixtures = useCallback(
    async (targetPage: number) => {
      const id = ++requestId.current;
      if (targetPage === 1) {
        setLoading(true);
      } else {
        setLoadingMore(true);
      }
      setError(null);

      try {
        const range = dateRangeForFilter(timeFilter);
        const params: Record<string, string | number> = {
          page_size: PAGE_SIZE,
          page: targetPage,
          date_from: range.date_from,
          date_to: range.date_to,
        };
        if (competitionFilter) params.competition_id = competitionFilter;
        if (countryFilter) params.country_id = countryFilter;
        if (selectedTeam) params.team_id = selectedTeam.id;
        if (searchTerm) params.q = searchTerm;

        const response = await footballApi.getFixtures(params);
        if (id !== requestId.current) return;

        setTotal(response.total);
        setPage(response.page);
        setFixtures((current) =>
          targetPage === 1 ? response.items : [...current, ...response.items],
        );

        // Stored fixtures are also a legitimate source of filter options: if the
        // reference endpoints were unavailable, the values below still come from the
        // provider payloads rather than from a hard-coded list.
        setCompetitionOptions((current) =>
          mergeOptions(
            current,
            response.items.map((item) => ({
              id: item.competition.id,
              name: item.competition.name,
            })),
          ),
        );
        setCountryOptions((current) =>
          mergeOptions(
            current,
            response.items.flatMap((item) =>
              item.competition.country
                ? [{ id: item.competition.country.id, name: item.competition.country.name }]
                : [],
            ),
          ),
        );
      } catch (err) {
        if (id !== requestId.current) return;
        setError(err instanceof Error ? err.message : "Failed to load fixtures");
        if (targetPage === 1) {
          setFixtures([]);
          setTotal(0);
        }
      } finally {
        if (id === requestId.current) {
          setLoading(false);
          setLoadingMore(false);
        }
      }
    },
    [
      competitionFilter,
      countryFilter,
      searchTerm,
      selectedTeam,
      timeFilter,
    ],
  );

  useEffect(() => {
    void fetchFixtures(1);
  }, [fetchFixtures]);

  const resetFilters = () => {
    setTimeFilter("30d");
    setCompetitionFilter("");
    setCountryFilter("");
    setSearchInput("");
    setSearchTerm("");
    setSelectedTeam(null);
    setTeamInput("");
    setTeamResults([]);
    setTeamOpen(false);
  };

  const hasActiveFilters = Boolean(
    competitionFilter || countryFilter || selectedTeam || searchTerm,
  );

  const fixturesForJob = useMemo(
    () => syncStatus?.per_job_type.find((job) => job.job_type === "fixtures"),
    [syncStatus],
  );
  // A failed freshness request is not evidence of fresh data. Until the status is
  // known the badge must stay neutral instead of falling through to the healthy state.
  const freshnessUnknown = syncStatus === null;
  const isStale = syncStatus?.data_is_stale === true;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white mb-2">Fixtures</h2>
          <p className="text-zinc-400">
            Stored fixtures sourced from football-data.org. Times shown in your local
            timezone.
          </p>
        </div>
        <div className="flex flex-col items-start md:items-end gap-1">
          <div
            className={`flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-full border ${
              isStale
                ? "text-amber-300 bg-amber-500/10 border-amber-500/30"
                : "text-zinc-500 bg-white/5 border-white/10"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                freshnessUnknown
                  ? "bg-zinc-500"
                  : isStale
                    ? "bg-amber-400"
                    : "bg-green-500"
              }`}
            />
            {freshnessUnknown
              ? "Freshness unknown"
              : isStale
                ? "Data may be stale"
                : "Local data"}{" "}
            · provider: football-data.org
          </div>
          <span className="text-[11px] text-zinc-600">
            {freshnessUnknown
              ? "Sync status unavailable: fixture freshness has not been verified."
              : `Last successful sync: ${formatTimestamp(
                  syncStatus.last_successful_sync_at,
                )}${
                  fixturesForJob?.last_completed_at
                    ? ` · fixtures refreshed: ${formatTimestamp(
                        fixturesForJob.last_completed_at,
                      )}${
                        fixturesForJob.last_completed_status &&
                        fixturesForJob.last_completed_status !== "success"
                          ? ` (${fixturesForJob.last_completed_status})`
                          : ""
                      }`
                    : ""
                }`}
          </span>
        </div>
      </div>

      {syncStatus?.data_is_stale && (
        <div
          role="status"
          className="mb-6 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200"
        >
          The stored data has not been refreshed recently. Fixtures below are the last
          values written by a successful sync, not a live feed.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-[#0f0f11] rounded-xl border border-white/10 p-5 space-y-6">
            <div>
              <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3 block">
                Time Window
              </label>
              <div className="grid grid-cols-2 gap-2">
                {TIME_FILTERS.map(({ key, label }) => (
                  <Button
                    key={key}
                    variant={timeFilter === key ? "primary" : "ghost"}
                    size="sm"
                    onClick={() => setTimeFilter(key)}
                    className="justify-start"
                  >
                    {label}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <label
                htmlFor="match-search"
                className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3 block"
              >
                Search
              </label>
              <input
                id="match-search"
                type="search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Team or competition name"
                className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-green-500/50"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3 block">
                Filter By
              </label>
              <div className="space-y-3">
                {selectedTeam ? (
                  <div className="flex items-center justify-between gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-2">
                    <span className="text-sm text-white truncate">{selectedTeam.name}</span>
                    <button
                      type="button"
                      aria-label="Clear team filter"
                      onClick={() => {
                        setSelectedTeam(null);
                        setTeamInput("");
                        setTeamResults([]);
                      }}
                      className="text-zinc-500 hover:text-white text-lg leading-none"
                    >
                      ×
                    </button>
                  </div>
                ) : (
                  <div className="relative">
                    <input
                      type="text"
                      value={teamInput}
                      aria-label="Filter by team"
                      placeholder="Any team (type 2+ letters)"
                      onChange={(event) => setTeamInput(event.target.value)}
                      onFocus={() => setTeamOpen(teamResults.length > 0)}
                      onKeyDown={(event) => {
                        if (event.key === "Escape") setTeamOpen(false);
                      }}
                      className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-2 focus:ring-green-500/50"
                    />
                    {teamOpen && teamResults.length > 0 && (
                      <ul
                        role="listbox"
                        aria-label="Team results"
                        className="absolute z-20 mt-1 w-full max-h-64 overflow-y-auto rounded-md border border-white/10 bg-[#151517] shadow-xl"
                      >
                        {teamResults.map((team) => (
                          <li key={team.id}>
                            <button
                              type="button"
                              role="option"
                              aria-selected={false}
                              onMouseDown={(event) => event.preventDefault()}
                              onClick={() => {
                                setSelectedTeam(team);
                                setTeamOpen(false);
                              }}
                              className="w-full text-left px-3 py-2 text-sm text-zinc-200 hover:bg-white/10"
                            >
                              {team.name}
                              {team.country ? (
                                <span className="block text-[11px] text-zinc-500">
                                  {team.country.name}
                                </span>
                              ) : null}
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                <select
                  aria-label="Filter by country"
                  value={countryFilter}
                  disabled={referenceLoading}
                  onChange={(event) => setCountryFilter(event.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-green-500/50 disabled:opacity-50"
                >
                  <option value="">
                    {referenceLoading ? "Loading countries…" : "All Countries"}
                  </option>
                  {countryOptions.map((country) => (
                    <option key={country.id} value={country.id}>
                      {country.name}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Filter by competition"
                  value={competitionFilter}
                  disabled={referenceLoading}
                  onChange={(event) => setCompetitionFilter(event.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-green-500/50 disabled:opacity-50"
                >
                  <option value="">
                    {referenceLoading ? "Loading competitions…" : "All Competitions"}
                  </option>
                  {competitionOptions.map((competition) => (
                    <option key={competition.id} value={competition.id}>
                      {competition.name}
                    </option>
                  ))}
                </select>

                {referenceError ? (
                  <div className="text-xs text-amber-400/90 space-y-2">
                    <p>{referenceError}</p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        void loadReference();
                        void loadSyncStatus();
                      }}
                    >
                      Retry filters
                    </Button>
                  </div>
                ) : (
                  <p className="text-[11px] leading-relaxed text-zinc-600">
                    Only competitions included in the provider plan and present in stored
                    data are listed.
                    {competitionOptions.length > 0
                      ? ` ${competitionOptions.length} competitions available.`
                      : ""}
                  </p>
                )}

                {hasActiveFilters && (
                  <Button variant="ghost" size="sm" onClick={resetFilters}>
                    Clear all filters
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3">
          {loading ? (
            <div className="space-y-3">
              {[...Array(6)].map((_, index) => (
                <div
                  key={index}
                  className="h-20 bg-white/5 rounded-xl border border-white/10 animate-pulse"
                />
              ))}
            </div>
          ) : error ? (
            <div className="bg-[#0f0f11] rounded-xl border border-red-500/20 py-16 text-center">
              <h3 className="text-lg font-semibold text-white mb-2">
                Could not load fixtures
              </h3>
              <p className="text-zinc-400 text-sm mb-6 max-w-md mx-auto">{error}</p>
              <Button
                onClick={() => {
                  void loadSyncStatus();
                  void fetchFixtures(1);
                }}
                variant="outline"
              >
                Retry
              </Button>
            </div>
          ) : fixtures.length === 0 ? (
            <div className="bg-[#0f0f11] rounded-xl border border-white/10 py-20 text-center px-6">
              <div className="text-zinc-300 mb-2">
                {hasActiveFilters
                  ? "No stored fixtures match these filters."
                  : "No stored fixtures in this window."}
              </div>
              <div className="text-zinc-500 text-sm mb-6 max-w-lg mx-auto">
                {hasActiveFilters
                  ? "Reset the filters, or widen the time window. Only matches returned by the provider and saved by a sync can appear."
                  : "The database only shows matches returned by the provider and saved by a sync. Competitions outside the current provider plan are never returned, so they cannot appear here."}
              </div>
              <Button variant="ghost" size="sm" onClick={resetFilters}>
                {hasActiveFilters ? "Clear filters" : "Reset filters"}
              </Button>
            </div>
          ) : (
            <>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 mb-3 text-xs text-zinc-500">
                <span>
                  Showing {fixtures.length} of {total} fixtures
                  {selectedTeam ? ` · ${selectedTeam.name}` : ""}
                  {searchTerm ? ` · matching “${searchTerm}”` : ""}
                </span>
                <span>UTC calendar days · local kickoff times</span>
              </div>
              <div className="grid grid-cols-1 gap-3">
                {fixtures.map((fixture) => (
                  <MatchCard key={fixture.id} fixture={fixture} />
                ))}
              </div>
              {fixtures.length < total && (
                <div className="mt-4 text-center">
                  <Button
                    variant="outline"
                    onClick={() => void fetchFixtures(page + 1)}
                    disabled={loadingMore}
                  >
                    {loadingMore ? "Loading…" : `Load more (${total - fixtures.length} left)`}
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function MatchCard({ fixture }: { fixture: Fixture }) {
  const { date, time } = formatKickoff(fixture.kickoff_utc);

  return (
    <Link
      href={`/matches/${fixture.id}`}
      className="group block p-4 bg-[#0f0f11] rounded-xl border border-white/10 hover:border-green-500/30 hover:bg-white/[0.02] transition-colors"
    >
      {/* Below md the card stacks: kickoff and status first, then the teams, then the
          competition. A single row would squeeze both team names to a few characters. */}
      <div className="flex items-center justify-between gap-3 mb-3 md:hidden">
        <div className="flex items-baseline gap-2">
          <span className="text-[10px] font-bold text-green-500 uppercase tracking-widest whitespace-nowrap">
            {date}
          </span>
          <span className="text-xs font-mono text-zinc-400">{time}</span>
        </div>
        <StatusBadge status={fixture.status} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[auto_1fr_auto] items-center gap-3 sm:gap-4">
        <div className="hidden md:flex flex-col items-center w-24 text-center border-r border-white/10 pr-4">
          <div className="text-[10px] font-bold text-green-500 uppercase tracking-widest mb-1 whitespace-nowrap">
            {date}
          </div>
          <div className="text-sm font-mono text-zinc-300">{time}</div>
          <div className="mt-1.5">
            <StatusBadge status={fixture.status} />
          </div>
        </div>

        <div className="min-w-0">
          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 sm:gap-4">
            <div className="flex items-center justify-end gap-2 min-w-0">
              <span className="truncate font-medium text-white group-hover:text-green-400 transition-colors text-sm sm:text-base">
                {fixture.home_team.name}
              </span>
              <TeamCrest team={fixture.home_team} />
            </div>

            <div className="flex flex-col items-center gap-1">
              {fixture.score ? (
                <div className="font-mono text-base sm:text-lg font-bold text-white whitespace-nowrap">
                  {fixture.score.home} - {fixture.score.away}
                </div>
              ) : (
                <div className="text-white/50 text-xs sm:text-sm">vs</div>
              )}
            </div>

            <div className="flex items-center gap-2 min-w-0">
              <TeamCrest team={fixture.away_team} />
              <span className="truncate font-medium text-white group-hover:text-green-400 transition-colors text-sm sm:text-base">
                {fixture.away_team.name}
              </span>
            </div>
          </div>

          <div className="md:hidden mt-2 text-[11px] text-zinc-500 truncate">
            {fixture.competition.name}
            {fixture.competition.country ? ` · ${fixture.competition.country.name}` : ""}
          </div>
        </div>

        <div className="hidden md:flex items-center gap-2 text-right min-w-[150px] justify-end">
          {fixture.competition.emblem_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={fixture.competition.emblem_url}
              alt=""
              width={20}
              height={20}
              loading="lazy"
              className="object-contain"
            />
          )}
          <div className="min-w-0">
            <div className="text-xs font-medium text-zinc-400 truncate">
              {fixture.competition.name}
            </div>
            <div className="text-[10px] text-zinc-600 uppercase">
              {fixture.competition.country?.name ?? ""}
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
