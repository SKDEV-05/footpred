"use client";

import { useCallback, useEffect, useState } from "react";
import { footballApi } from "@/lib/api";
import type {
  AnalysisClassCalibration,
  AnalysisHistoryItem,
  AnalysisStatus,
  MatchAnalysis,
} from "@/types";

interface MatchAnalysisPanelProps {
  matchId: number;
  kickoffUtc: string;
  status: string;
}

const ANALYSABLE_STATUSES = new Set(["scheduled", "timed"]);

const STATUS_STYLE: Record<
  AnalysisStatus,
  { label: string; className: string; description: string }
> = {
  READY: {
    label: "Ready",
    className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    description: "Probabilities were produced from verified historical results.",
  },
  INSUFFICIENT_DATA: {
    label: "Insufficient data",
    className: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    description:
      "The verified history is too small to estimate this match. No probabilities are shown.",
  },
  DATA_UNAVAILABLE: {
    label: "Data unavailable",
    className: "border-sky-500/30 bg-sky-500/10 text-sky-300",
    description:
      "This match cannot be analysed in its current state. No probabilities are shown.",
  },
  ANALYSIS_FAILED: {
    label: "Analysis failed",
    className: "border-red-500/30 bg-red-500/10 text-red-300",
    description:
      "The analysis did not complete and no numbers were produced. The failure is recorded rather than hidden.",
  },
};

function pct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function num(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "—";
  return value.toFixed(digits);
}

function count(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return String(value);
}

function label(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().replace(".000Z", "Z");
}

export function MatchAnalysisPanel({
  matchId,
  kickoffUtc,
  status,
}: MatchAnalysisPanelProps) {
  const [analysis, setAnalysis] = useState<MatchAnalysis | null>(null);
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [mountedAt, setMountedAt] = useState<number | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      const items = await footballApi.getMatchAnalysisHistory(matchId);
      setHistory(items);
      setHistoryError(null);
    } catch (historyFailure) {
      setHistoryError(
        historyFailure instanceof Error
          ? historyFailure.message
          : "Prior analyses could not be loaded.",
      );
    }
  }, [matchId]);

  useEffect(() => {
    setMountedAt(Date.now());
    void loadHistory();
  }, [loadHistory]);

  const kickoffPassed =
    mountedAt !== null && new Date(kickoffUtc).getTime() <= mountedAt;
  const startable = ANALYSABLE_STATUSES.has(status) && !kickoffPassed;

  async function runAnalysis(force = false) {
    setPending(true);
    setError(null);
    try {
      const report = await footballApi.analyzeMatch(matchId, force);
      setAnalysis(report);
      await loadHistory();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "The analysis request failed.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="mt-8 bg-[#0f0f11] rounded-2xl border border-white/10 p-6">
      <div className="flex flex-wrap items-center gap-3 mb-1">
        <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-wider">
          Match Analysis
        </h3>
        {analysis && <StatusPill status={analysis.status} />}
      </div>
      <p className="text-xs text-zinc-500 mb-5">
        Transparent independent-Poisson estimates from stored results completed before
        kickoff. Every report states its sample, data window, and out-of-sample error.
      </p>

      {!analysis && !pending && !error && (
        <div className="space-y-4">
          <p className="text-sm text-zinc-400 leading-relaxed">
            The model estimates 1X2 probabilities and expected goals from verified
            historical results. It does not use live match statistics, lineups, or
            injuries, and it abstains when the verified sample is below the documented
            threshold.
          </p>
          {startable ? (
            <button
              type="button"
              onClick={() => void runAnalysis()}
              className="inline-flex items-center rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
            >
              Analyze match
            </button>
          ) : (
            <p className="text-sm text-amber-300/90">
              {kickoffPassed
                ? "Kickoff has passed. A pre-match report cannot be generated, because it would be evaluated after the fact."
                : `Analysis is limited to scheduled fixtures. This match is currently “${label(status)}”.`}
            </p>
          )}
        </div>
      )}

      {pending && (
        <p className="text-sm text-zinc-300" role="status" aria-live="polite">
          Running the analysis from stored results…
        </p>
      )}

      {error && (
        <div className="space-y-3" role="alert">
          <p className="text-sm text-red-300">Analysis request failed: {error}</p>
          <button
            type="button"
            onClick={() => void runAnalysis()}
            className="inline-flex items-center rounded-lg border border-white/15 px-3 py-1.5 text-sm text-zinc-200 transition-colors hover:bg-white/5"
          >
            Retry
          </button>
        </div>
      )}

      {analysis && !pending && (
        <div className="space-y-8">
          {analysis.status === "READY" ? (
            <ReadyReport analysis={analysis} onRegenerate={() => void runAnalysis(true)} />
          ) : (
            <AbstentionReport analysis={analysis} onRetry={() => void runAnalysis(true)} />
          )}
        </div>
      )}

      <HistoryTable history={history} error={historyError} />
    </section>
  );
}

function StatusPill({ status }: { status: AnalysisStatus }) {
  const style = STATUS_STYLE[status];
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.className}`}
    >
      {style.label}
    </span>
  );
}

function AbstentionReport({
  analysis,
  onRetry,
}: {
  analysis: MatchAnalysis;
  onRetry: () => void;
}) {
  const style = STATUS_STYLE[analysis.status];
  const limitations = analysis.data_quality.limitations;
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3">
        <div className="font-semibold text-white mb-1">{style.label}</div>
        <p className="text-sm text-zinc-400 leading-relaxed">{style.description}</p>
        {analysis.error_message && (
          <p className="mt-2 text-sm text-zinc-300">{analysis.error_message}</p>
        )}
      </div>

      {limitations.length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">
            Recorded limitations
          </h4>
          <ul className="flex flex-wrap gap-2">
            {limitations.map((item) => (
              <li
                key={item}
                className="rounded border border-white/10 bg-white/[0.02] px-2 py-0.5 text-xs text-zinc-400"
              >
                {label(item)}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-wrap gap-3 text-xs text-zinc-500">
        <span>Analysis as of {formatTimestamp(analysis.analysis_as_of)}</span>
        <span>
          Provider: {analysis.data_quality.provider_code ?? "not recorded"}
        </span>
      </div>

      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center rounded-lg border border-white/15 px-3 py-1.5 text-sm text-zinc-200 transition-colors hover:bg-white/5"
      >
        Re-run analysis
      </button>
    </div>
  );
}

function ReadyReport({
  analysis,
  onRegenerate,
}: {
  analysis: MatchAnalysis;
  onRegenerate: () => void;
}) {
  const model = analysis.statistical_model;
  const quality = analysis.data_quality;
  const history = analysis.historical_context;
  if (!model) return null;

  const home = analysis.match_overview.home_team.name;
  const away = analysis.match_overview.away_team.name;
  const homeProbability = model.home_win_probability ?? 0;
  const drawProbability = model.draw_probability ?? 0;
  const awayProbability = model.away_win_probability ?? 0;

  return (
    <>
      <div>
        <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
          <h4 className="text-sm font-bold text-white">1X2 probabilities</h4>
          <span className="text-xs text-zinc-500">
            {model.model_version} · {model.feature_version ?? "feature version not recorded"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <ProbabilityCard label={home} value={model.home_win_probability} />
          <ProbabilityCard label="Draw" value={model.draw_probability} />
          <ProbabilityCard label={away} value={model.away_win_probability} />
        </div>

        <div
          className="mt-3 flex h-3 w-full overflow-hidden rounded"
          role="img"
          aria-label={`${home} win ${pct(model.home_win_probability)}, draw ${pct(
            model.draw_probability,
          )}, ${away} win ${pct(model.away_win_probability)}`}
        >
          <div
            className="bg-emerald-500"
            style={{ width: `${homeProbability * 100}%` }}
            title={`${home}: ${pct(model.home_win_probability)}`}
          />
          <div
            className="bg-zinc-500"
            style={{ width: `${drawProbability * 100}%` }}
            title={`Draw: ${pct(model.draw_probability)}`}
          />
          <div
            className="bg-sky-500"
            style={{ width: `${awayProbability * 100}%` }}
            title={`${away}: ${pct(model.away_win_probability)}`}
          />
        </div>
        <p className="mt-2 text-xs text-zinc-500">
          Probabilities sum to 100%. They are estimates, not guarantees.
        </p>

        <div className="mt-5 grid grid-cols-2 gap-3">
          <StatCard label={`${home} expected goals`} value={num(model.expected_home_goals)} />
          <StatCard label={`${away} expected goals`} value={num(model.expected_away_goals)} />
        </div>
      </div>

      <MarketTable model={model} />

      {model.scoreline_probabilities.length > 0 && (
        <div>
          <h4 className="text-sm font-bold text-white mb-3">Most likely scorelines</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-zinc-500">
                  <th className="py-2 font-medium">Scoreline</th>
                  <th className="py-2 text-right font-medium">Probability</th>
                </tr>
              </thead>
              <tbody>
                {model.scoreline_probabilities.map((item) => (
                  <tr
                    key={`${item.home_goals}-${item.away_goals}`}
                    className="border-b border-white/5"
                  >
                    <td className="py-2 font-mono text-zinc-200">
                      {item.home_goals} - {item.away_goals}
                    </td>
                    <td className="py-2 text-right font-mono text-zinc-200">
                      {pct(item.probability)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-zinc-500">
            Only the highest-probability exact scorelines are shown. They are not a
            prediction of the final score.
          </p>
        </div>
      )}

      {history && <HistoricalRecords history={history} home={home} away={away} />}

      {analysis.explanation && (
        <div>
          <h4 className="text-sm font-bold text-white mb-3">Why these numbers</h4>
          <div className="space-y-3 text-sm text-zinc-400 leading-relaxed">
            <p>{analysis.explanation.model_rationale}</p>
            {Object.entries(analysis.explanation.expected_goals_breakdown).map(
              ([side, text]) => (
                <p key={side}>
                  <span className="text-zinc-300">{label(side)}: </span>
                  {text}
                </p>
              ),
            )}
            <p>{analysis.explanation.form_impact}</p>
            <p>{analysis.explanation.h2h_impact}</p>
          </div>
        </div>
      )}

      {model.model_parameters && (
        <details className="rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3">
          <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
            Model parameters
          </summary>
          <dl className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2 text-sm">
            <ParameterRow
              label="Baseline home goals"
              value={num(model.model_parameters.baseline_avg_home_goals, 3)}
            />
            <ParameterRow
              label="Baseline away goals"
              value={num(model.model_parameters.baseline_avg_away_goals, 3)}
            />
            <ParameterRow
              label="Baseline source"
              value={label(model.model_parameters.baseline_source)}
            />
            <ParameterRow
              label="Home attack / defence"
              value={`${num(model.model_parameters.home_attack_strength, 3)} / ${num(
                model.model_parameters.home_defence_strength,
                3,
              )}`}
            />
            <ParameterRow
              label="Away attack / defence"
              value={`${num(model.model_parameters.away_attack_strength, 3)} / ${num(
                model.model_parameters.away_defence_strength,
                3,
              )}`}
            />
            <ParameterRow
              label="Recent-form weight (home / away)"
              value={`${num(model.model_parameters.home_recent_weight, 2)} / ${num(
                model.model_parameters.away_recent_weight,
                2,
              )}`}
            />
            <ParameterRow
              label="Expected-goals bounds"
              value={model.model_parameters.expected_goals_bounds.join(" – ")}
            />
          </dl>
        </details>
      )}

      <EvaluationBlock analysis={analysis} />

      <DataQualityBlock analysis={analysis} />

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4">
        <span className="text-xs text-zinc-500">
          Analysis #{analysis.id} · generated {formatTimestamp(analysis.generated_at)} ·
          as of {formatTimestamp(analysis.analysis_as_of)}
        </span>
        <button
          type="button"
          onClick={onRegenerate}
          className="inline-flex items-center rounded-lg border border-white/15 px-3 py-1.5 text-sm text-zinc-200 transition-colors hover:bg-white/5"
        >
          Regenerate
        </button>
      </div>
    </>
  );
}

function ProbabilityCard({
  label: cardLabel,
  value,
}: {
  label: string;
  value: number | null;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-3">
      <div className="text-xs text-zinc-500 truncate" title={cardLabel}>
        {cardLabel}
      </div>
      <div className="mt-1 font-mono text-xl font-semibold text-white">{pct(value)}</div>
    </div>
  );
}

function StatCard({ label: cardLabel, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-3">
      <div className="text-xs text-zinc-500">{cardLabel}</div>
      <div className="mt-1 font-mono text-xl font-semibold text-white">{value}</div>
    </div>
  );
}

function ParameterRow({ label: rowLabel, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className="text-zinc-500">{rowLabel}</dt>
      <dd className="font-mono text-zinc-200 text-right">{value}</dd>
    </div>
  );
}

function MarketTable({
  model,
}: {
  model: NonNullable<MatchAnalysis["statistical_model"]>;
}) {
  const rows = [
    {
      name: "Both teams to score",
      probability: model.btts_probability,
      complement: model.btts_probability === null ? null : 1 - model.btts_probability,
      complementLabel: "No",
    },
    {
      name: "Over 1.5 goals",
      probability: model.over_1_5_probability,
      complement: model.under_1_5_probability,
      complementLabel: "Under 1.5",
    },
    {
      name: "Over 2.5 goals",
      probability: model.over_2_5_probability,
      complement: model.under_2_5_probability,
      complementLabel: "Under 2.5",
    },
    {
      name: "Over 3.5 goals",
      probability: model.over_3_5_probability,
      complement: model.under_3_5_probability,
      complementLabel: "Under 3.5",
    },
  ];

  return (
    <div>
      <h4 className="text-sm font-bold text-white mb-3">Secondary markets</h4>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-zinc-500">
              <th className="py-2 font-medium">Market</th>
              <th className="py-2 text-right font-medium">Yes / over</th>
              <th className="py-2 text-right font-medium">No / under</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.name} className="border-b border-white/5">
                <td className="py-2 text-zinc-300">{row.name}</td>
                <td className="py-2 text-right font-mono text-zinc-200">
                  {pct(row.probability)}
                </td>
                <td className="py-2 text-right font-mono text-zinc-400">
                  <span className="mr-2 text-xs text-zinc-600">{row.complementLabel}</span>
                  {pct(row.complement)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HistoricalRecords({
  history,
  home,
  away,
}: {
  history: NonNullable<MatchAnalysis["historical_context"]>;
  home: string;
  away: string;
}) {
  const h2h = history.head_to_head;
  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
        <h4 className="text-sm font-bold text-white">Verified historical record</h4>
        <span className="text-xs text-zinc-500">
          Competition baseline:{" "}
          {history.baseline_source === "competition"
            ? "competition results"
            : history.baseline_source === "all_competitions"
              ? "all stored competitions"
              : "explicit prior (sample too small)"}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-zinc-500">
              <th className="py-2 font-medium">Metric</th>
              <th className="py-2 text-right font-medium">{home}</th>
              <th className="py-2 text-right font-medium">{away}</th>
            </tr>
          </thead>
          <tbody>
            <RecordRow
              name="Matches played"
              left={count(history.home_team.sample_size)}
              right={count(history.away_team.sample_size)}
            />
            <RecordRow
              name="W - D - L"
              left={`${history.home_team.overall.wins} - ${history.home_team.overall.draws} - ${history.home_team.overall.losses}`}
              right={`${history.away_team.overall.wins} - ${history.away_team.overall.draws} - ${history.away_team.overall.losses}`}
            />
            <RecordRow
              name="Goals for / against per match"
              left={`${num(history.home_team.overall.goals_for_avg)} / ${num(
                history.home_team.overall.goals_against_avg,
              )}`}
              right={`${num(history.away_team.overall.goals_for_avg)} / ${num(
                history.away_team.overall.goals_against_avg,
              )}`}
            />
            <RecordRow
              name="Venue record (home / away)"
              left={`${history.home_team.venue_specific.wins} - ${history.home_team.venue_specific.draws} - ${history.home_team.venue_specific.losses}`}
              right={`${history.away_team.venue_specific.wins} - ${history.away_team.venue_specific.draws} - ${history.away_team.venue_specific.losses}`}
            />
            <RecordRow
              name="Clean sheets / failed to score"
              left={`${history.home_team.overall.clean_sheets} / ${history.home_team.overall.failed_to_score}`}
              right={`${history.away_team.overall.clean_sheets} / ${history.away_team.overall.failed_to_score}`}
            />
            <RecordRow
              name="Recent form"
              left={history.home_team.recent_form || "—"}
              right={history.away_team.recent_form || "—"}
            />
            <RecordRow
              name="Recent goals for / against"
              left={`${num(history.home_team.recent_goals_for_avg)} / ${num(
                history.home_team.recent_goals_against_avg,
              )}`}
              right={`${num(history.away_team.recent_goals_for_avg)} / ${num(
                history.away_team.recent_goals_against_avg,
              )}`}
            />
          </tbody>
        </table>
      </div>

      <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3 text-sm text-zinc-400">
        <span className="text-zinc-300">Head to head: </span>
        {h2h.meetings_count} prior{" "}
        {h2h.meetings_count === 1 ? "meeting" : "meetings"} — {home} {h2h.home_wins} wins,{" "}
        {h2h.draws} draws, {away} {h2h.away_wins} wins
        {h2h.limited_sample ? " (limited sample; not used to fit the model)" : ""}.
        <span className="block mt-1 text-xs text-zinc-500">
          Competition sample: {history.competition_matches_analyzed} matches,{" "}
          {num(history.competition_avg_home_goals, 3)} home /{" "}
          {num(history.competition_avg_away_goals, 3)} away goals per match.
        </span>
      </div>
    </div>
  );
}

function RecordRow({
  name,
  left,
  right,
}: {
  name: string;
  left: string;
  right: string;
}) {
  return (
    <tr className="border-b border-white/5">
      <td className="py-2 text-zinc-400">{name}</td>
      <td className="py-2 text-right font-mono text-zinc-200">{left}</td>
      <td className="py-2 text-right font-mono text-zinc-200">{right}</td>
    </tr>
  );
}

function EvaluationBlock({ analysis }: { analysis: MatchAnalysis }) {
  const evaluation = analysis.evaluation;
  return (
    <div>
      <h4 className="text-sm font-bold text-white mb-3">Out-of-sample evaluation</h4>
      {!evaluation || !evaluation.evaluated ? (
        <p className="text-sm text-zinc-400 leading-relaxed">
          {evaluation?.reason
            ? `No backtest metrics are reported: ${label(evaluation.reason)}.`
            : "No backtest was recorded for this analysis."}{" "}
          The platform does not state an accuracy figure without an out-of-sample
          evaluation.
        </p>
      ) : (
        <>
          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <StatCard label="Brier score" value={num(evaluation.brier_score, 4)} />
            <StatCard label="Log loss" value={num(evaluation.log_loss, 4)} />
            <StatCard
              label="Brier skill vs uniform"
              value={num(evaluation.brier_skill_score, 4)}
            />
            <StatCard
              label="Uniform Brier"
              value={num(evaluation.uniform_brier_score, 4)}
            />
            <StatCard
              label="Uniform log loss"
              value={num(evaluation.uniform_log_loss, 4)}
            />
            <StatCard
              label="Calibration error (ECE)"
              value={num(evaluation.expected_calibration_error, 4)}
            />
          </dl>
          <p className="mt-3 text-xs text-zinc-500">
            {count(evaluation.sample_size)} out-of-sample matches,{" "}
            {formatTimestamp(evaluation.test_period_from)} →{" "}
            {formatTimestamp(evaluation.test_period_to)}. Evaluation:{" "}
            {label(evaluation.evaluation_type ?? "not recorded")}. Lower Brier and log
            loss are better; a positive skill score beats a uniform 1/3 baseline.
          </p>

          {evaluation.calibration.length > 0 && (
            <CalibrationTable calibration={evaluation.calibration} />
          )}
        </>
      )}
    </div>
  );
}

function CalibrationTable({
  calibration,
}: {
  calibration: AnalysisClassCalibration[];
}) {
  return (
    <details className="mt-3 rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3">
      <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
        Calibration by probability bin
      </summary>
      <div className="mt-3 space-y-4">
        {calibration.map((group) => (
          <div key={group.class_label}>
            <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
                {label(group.class_label)}
              </span>
              <span className="text-xs text-zinc-500">
                ECE {num(group.expected_calibration_error, 4)} · MCE{" "}
                {num(group.maximum_calibration_error, 4)} · n = {group.sample_size}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-left text-zinc-500">
                    <th className="py-1.5 font-medium">Bin</th>
                    <th className="py-1.5 text-right font-medium">n</th>
                    <th className="py-1.5 text-right font-medium">Mean predicted</th>
                    <th className="py-1.5 text-right font-medium">Observed</th>
                  </tr>
                </thead>
                <tbody>
                  {group.bins.map((bin) => (
                    <tr
                      key={`${group.class_label}-${bin.lower}-${bin.upper}`}
                      className="border-b border-white/5"
                    >
                      <td className="py-1.5 font-mono text-zinc-300">
                        {bin.lower.toFixed(1)} – {bin.upper.toFixed(1)}
                      </td>
                      <td className="py-1.5 text-right font-mono text-zinc-300">
                        {bin.sample_size}
                      </td>
                      <td className="py-1.5 text-right font-mono text-zinc-300">
                        {pct(bin.mean_probability)}
                      </td>
                      <td className="py-1.5 text-right font-mono text-zinc-300">
                        {pct(bin.observed_rate)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </details>
  );
}

function DataQualityBlock({ analysis }: { analysis: MatchAnalysis }) {
  const quality = analysis.data_quality;
  return (
    <div>
      <h4 className="text-sm font-bold text-white mb-3">Data quality and provenance</h4>
      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2 text-sm">
        <ParameterRow label="Classification" value={label(quality.data_classification)} />
        <ParameterRow label="Provider" value={quality.provider_code ?? "—"} />
        <ParameterRow
          label="Historical matches"
          value={count(quality.historical_matches)}
        />
        <ParameterRow
          label="Competition matches"
          value={count(quality.competition_matches)}
        />
        <ParameterRow
          label="Extra time / shootout excluded"
          value={count(quality.excluded_extra_time_or_shootout)}
        />
        <ParameterRow
          label="Sample (home / away / H2H)"
          value={`${count(quality.home_sample_size)} / ${count(
            quality.away_sample_size,
          )} / ${count(quality.h2h_sample_size)}`}
        />
        <ParameterRow
          label="Earliest kickoff used"
          value={formatTimestamp(quality.earliest_kickoff)}
        />
        <ParameterRow
          label="Latest kickoff used"
          value={formatTimestamp(quality.latest_kickoff)}
        />
        <ParameterRow
          label="Payload first fetched → checkpoint"
          value={`${formatTimestamp(quality.retrieval_from)} → ${formatTimestamp(
            quality.retrieval_to,
          )}`}
        />
        <ParameterRow label="Dataset" value={quality.dataset_id ?? "—"} />
      </dl>

      <p className="mt-3 break-all font-mono text-[11px] text-zinc-600">
        dataset digest: {quality.dataset_digest ?? "—"}
      </p>

      <div className="mt-4 space-y-3 text-sm text-zinc-400">
        <p>{quality.statistics_note}</p>
        {quality.data_freshness_note && <p>{quality.data_freshness_note}</p>}
        {quality.missing_features.length > 0 && (
          <p>
            <span className="text-zinc-300">Missing features: </span>
            {quality.missing_features.map(label).join(", ")}.
          </p>
        )}
      </div>

      {quality.limitations.length > 0 && (
        <div className="mt-3">
          <div className="text-xs font-bold text-zinc-500 uppercase tracking-wider mb-2">
            Limitations
          </div>
          <ul className="flex flex-wrap gap-2">
            {quality.limitations.map((item) => (
              <li
                key={item}
                className="rounded border border-white/10 bg-white/[0.02] px-2 py-0.5 text-xs text-zinc-400"
              >
                {label(item)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function HistoryTable({
  history,
  error,
}: {
  history: AnalysisHistoryItem[];
  error: string | null;
}) {
  return (
    <div className="mt-8 border-t border-white/10 pt-6">
      <h4 className="text-sm font-bold text-zinc-400 uppercase tracking-wider mb-3">
        Prior analyses
      </h4>
      {error ? (
        <p className="text-xs text-zinc-500">{error}</p>
      ) : history.length === 0 ? (
        <p className="text-xs text-zinc-500">No prior reports for this match.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-left text-zinc-500">
                <th className="py-2 font-medium">Report</th>
                <th className="py-2 font-medium">Generated</th>
                <th className="py-2 font-medium">Status</th>
                <th className="py-2 font-medium">Model</th>
                <th className="py-2 text-right font-medium">Home</th>
                <th className="py-2 text-right font-medium">Draw</th>
                <th className="py-2 text-right font-medium">Away</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.id} className="border-b border-white/5">
                  <td className="py-2 font-mono text-zinc-300">#{item.id}</td>
                  <td className="py-2 text-zinc-400">
                    {formatTimestamp(item.generated_at)}
                  </td>
                  <td className="py-2 text-zinc-400">{label(item.status)}</td>
                  <td className="py-2 font-mono text-xs text-zinc-500">
                    {item.model_version}
                  </td>
                  <td className="py-2 text-right font-mono text-zinc-300">
                    {pct(item.home_win_probability)}
                  </td>
                  <td className="py-2 text-right font-mono text-zinc-300">
                    {pct(item.draw_probability)}
                  </td>
                  <td className="py-2 text-right font-mono text-zinc-300">
                    {pct(item.away_win_probability)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
