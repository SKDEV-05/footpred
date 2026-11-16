"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { footballApi } from "@/lib/api";
import type { FixtureDetail, StatisticsResponse } from "@/types";
import { formatKickoff } from "@/lib/dates";
import { TeamCrest } from "@/components/TeamCrest";
import { StatusBadge } from "@/components/StatusBadge";
import { MatchAnalysisPanel } from "@/components/MatchAnalysisPanel";

interface MatchDetailClientProps {
  matchId: string;
}

function metricLabel(metric: string): string {
  return metric
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}
export default function MatchDetailClient({ matchId }: MatchDetailClientProps) {
  const [fixture, setFixture] = useState<FixtureDetail | null>(null);
  const [statistics, setStatistics] = useState<StatisticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    footballApi
      .getMatchDetails(Number(matchId))
      .then(async (data) => {
        if (!active) return;
        setFixture(data);
        if (data.statistics_available) {
          const stats = await footballApi.getMatchStatistics(data.id);
          if (active) setStatistics(stats);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load match");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [matchId]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="animate-pulse space-y-8">
          <div className="h-8 bg-white/5 rounded w-1/4" />
          <div className="h-40 bg-white/5 rounded border border-white/10" />
          <div className="h-24 bg-white/5 rounded border border-white/10" />
        </div>
      </div>
    );
  }

  if (error || !fixture) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 text-center">
        <div className="text-red-400 mb-4">Match not found</div>
        <div className="text-zinc-400 text-sm mb-6">{error || "Unknown error"}</div>
        <Link href="/" className="text-green-500 hover:text-green-400 underline">
          Back to matches
        </Link>
      </div>
    );
  }

  const { date, time } = formatKickoff(fixture.kickoff_utc);
  const result = fixture.result;
  const hoursSinceSync =
    (Date.now() - new Date(fixture.last_synced_at).getTime()) / 3_600_000;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-zinc-400 hover:text-white mb-8 text-sm transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to Matches
      </Link>

      <div className="bg-[#0f0f11] rounded-2xl border border-white/10 p-6 sm:p-8 mb-8">
        <div className="flex items-center justify-center gap-2 mb-6 text-center">
          {fixture.competition.emblem_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={fixture.competition.emblem_url}
              alt=""
              width={22}
              height={22}
              className="object-contain"
            />
          )}
          <div>
            <div className="font-semibold text-white text-sm sm:text-base">
              {fixture.competition.name}
            </div>
            <div className="text-xs text-zinc-500">
              {fixture.competition.country?.name ?? "Country not supplied"}
              {fixture.matchday !== null ? ` · Matchday ${fixture.matchday}` : ""}
            </div>
          </div>
        </div>

        <div className="flex flex-col md:flex-row md:items-center gap-4 md:gap-6">
          <div className="text-center md:text-left md:w-28 shrink-0">
            <div className="text-xs font-bold text-green-500 uppercase tracking-widest mb-1 whitespace-nowrap">
              {date}
            </div>
            <div className="text-sm font-mono text-zinc-400 mb-2">{time}</div>
            <StatusBadge status={fixture.status} />
          </div>

          <div className="flex-1 min-w-0 grid grid-cols-[1fr_auto_auto_auto_1fr] items-center gap-2 sm:gap-3">
            <span className="font-bold text-base sm:text-xl text-white text-right leading-tight break-words">
              {fixture.home_team.name}
            </span>
            <TeamCrest team={fixture.home_team} size={40} />
            <div className="px-1 sm:px-2">
              {result && result.home_score !== null && result.away_score !== null ? (
                <div className="font-mono text-2xl sm:text-3xl font-bold text-white whitespace-nowrap">
                  {result.home_score} - {result.away_score}
                </div>
              ) : (
                <div className="text-white/50 text-sm">vs</div>
              )}
            </div>
            <TeamCrest team={fixture.away_team} size={40} />
            <span className="font-bold text-base sm:text-xl text-white leading-tight break-words">
              {fixture.away_team.name}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <section className="bg-[#0f0f11] rounded-2xl border border-white/10 p-6">
          <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-wider mb-4">
            Match Information
          </h3>
          <dl className="space-y-2 text-sm">
            <Row label="Season" value={fixture.season.label} />
            <Row label="Stage" value={fixture.stage ? metricLabel(fixture.stage) : "Not supplied"} />
            <Row label="Venue" value={fixture.venue_name ?? "Not supplied"} />
            <Row
              label="Attendance"
              value={
                fixture.attendance === null ? "Not supplied" : String(fixture.attendance)
              }
            />
            {result && (
              <>
                <Row
                  label="Half time"
                  value={
                    result.ht_home_score !== null && result.ht_away_score !== null
                      ? `${result.ht_home_score} - ${result.ht_away_score}`
                      : "Not supplied"
                  }
                />
                <Row
                  label="Winner"
                  value={result.winner ? metricLabel(result.winner) : "Not decided"}
                />
                <Row
                  label="Duration"
                  value={result.duration ? metricLabel(result.duration) : "Not supplied"}
                />
                <Row label="Result final" value={result.is_final ? "Yes" : "No"} />
              </>
            )}
          </dl>
          <div className="mt-4 pt-4 border-t border-white/5 text-xs text-zinc-600 space-y-1">
            <div>Last synchronised: {new Date(fixture.last_synced_at).toLocaleString()}</div>
            <div>
              Provider last updated:{" "}
              {fixture.provider_last_updated
                ? new Date(fixture.provider_last_updated).toLocaleString()
                : "Not supplied"}
            </div>
            {hoursSinceSync > 6 && (
              <div className="text-amber-400/90">
                This record has not been refreshed in the last 6 hours.
              </div>
            )}
          </div>
        </section>

        <section className="bg-[#0f0f11] rounded-2xl border border-white/10 p-6">
          <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-wider mb-4">
            Stored Statistics
          </h3>
          {!fixture.statistics_available ? (
            <p className="text-sm text-zinc-400">
              No statistics are stored for this match. Nothing is inferred or estimated.
            </p>
          ) : statistics && statistics.available ? (
            <StatisticsTable statistics={statistics} />
          ) : (
            <p className="text-sm text-zinc-400">Statistics are still loading.</p>
          )}
        </section>
      </div>

      <MatchAnalysisPanel
        matchId={fixture.id}
        kickoffUtc={fixture.kickoff_utc}
        status={fixture.status}
      />
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="text-zinc-200 text-right">{value}</dd>
    </div>
  );
}

function StatisticsTable({ statistics }: { statistics: StatisticsResponse }) {
  const metrics = Array.from(
    new Set(statistics.teams.flatMap((team) => Object.keys(team.metrics))),
  ).sort();

  if (metrics.length === 0) {
    return <p className="text-sm text-zinc-400">No metric values were stored.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-zinc-500 border-b border-white/10">
            <th className="py-2 font-medium">Metric</th>
            {statistics.teams.map((team) => (
              <th key={team.team_id} className="py-2 font-medium text-right">
                {team.team_name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => (
            <tr key={metric} className="border-b border-white/5">
              <td className="py-2 text-zinc-400">{metricLabel(metric)}</td>
              {statistics.teams.map((team) => (
                <td key={team.team_id} className="py-2 text-right font-mono text-zinc-200">
                  {metric in team.metrics ? team.metrics[metric] : "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
