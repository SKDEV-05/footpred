"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ApiError, footballApi } from "@/lib/api";
import type {
  AnalysisClassCalibration,
  EvaluationModelMetrics,
  EvaluationReportBody,
  EvaluationRun,
  EvaluationRunSummary,
  EvaluationSeason,
} from "@/types";

const MODEL_ORDER = [
  "poisson",
  "dixon_coles",
  "elo",
  "uniform",
  "competition_frequency",
] as const;

const MODEL_LABELS: Record<string, string> = {
  poisson: "Poisson",
  dixon_coles: "Dixon-Coles",
  elo: "Elo (Davidson)",
  uniform: "Uniform 1/3",
  competition_frequency: "Competition frequency",
};

function num(value: number | null | undefined, digits = 4): string {
  if (value === null || value === undefined) return "—";
  return value.toFixed(digits);
}

function pct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}

function shortDigest(value: string | null | undefined): string {
  if (!value) return "—";
  return value.length > 16 ? `${value.slice(0, 16)}…` : value;
}

function modelLabel(key: string, models: EvaluationModelMetrics[]): string {
  const match = models.find((model) => model.key === key);
  return match?.label || MODEL_LABELS[key] || key;
}

function modelBrier(
  block: Record<string, EvaluationModelMetrics> | undefined,
  key: string,
): string {
  const value = block?.[key]?.brier_score;
  return num(value);
}

export default function EvaluationPage() {
  const [runs, setRuns] = useState<EvaluationRunSummary[]>([]);
  const [run, setRun] = useState<EvaluationRun | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [empty, setEmpty] = useState(false);

  const loadRuns = useCallback(async () => {
    const listing = await footballApi.listEvaluations();
    setRuns(listing);
    return listing;
  }, []);

  const loadRun = useCallback(async (id: number) => {
    const loaded = await footballApi.getEvaluation(id);
    setRun(loaded);
    setSelectedRunId(loaded.id);
  }, []);

  const bootstrap = useCallback(async () => {
    try {
      const listing = await loadRuns();
      if (listing.length === 0) {
        setEmpty(true);
        setRun(null);
        return;
      }
      const latest = await footballApi.getLatestEvaluation();
      setRun(latest);
      setSelectedRunId(latest.id);
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 404) {
        setEmpty(true);
        setRun(null);
      } else {
        setError(
          failure instanceof Error
            ? failure.message
            : "The evaluation could not be loaded.",
        );
      }
    } finally {
      setLoading(false);
    }
  }, [loadRuns]);

  useEffect(() => {
    // The loader only updates state after awaiting the API; the rule cannot see through
    // the callback, so it is suppressed here rather than restructuring a one-shot load.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void bootstrap();
  }, [bootstrap]);

  async function computeEvaluation() {
    setPending(true);
    setActionError(null);
    try {
      const generated = await footballApi.runEvaluation();
      setRun(generated);
      setSelectedRunId(generated.id);
      setEmpty(false);
      await loadRuns();
    } catch (failure) {
      setActionError(
        failure instanceof Error
          ? failure.message
          : "The evaluation could not be computed.",
      );
    } finally {
      setPending(false);
    }
  }

  async function selectRun(id: number) {
    if (id === selectedRunId) return;
    setActionError(null);
    try {
      await loadRun(id);
    } catch (failure) {
      setActionError(
        failure instanceof Error
          ? failure.message
          : "The selected run could not be loaded.",
      );
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">
            Model evaluation
          </h2>
          <p className="mt-1 max-w-3xl text-sm text-zinc-400 leading-relaxed">
            Chronological, out-of-sample evaluation of every model on the same stored
            match set. These are retrospective measurements, not live predictions and not
            a guarantee of future accuracy.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {runs.length > 1 && (
            <label className="flex items-center gap-2 text-xs text-zinc-400">
              <span>Stored run</span>
              <select
                value={selectedRunId ?? ""}
                onChange={(event) => void selectRun(Number(event.target.value))}
                className="rounded-lg border border-white/10 bg-[#0f0f11] px-2 py-1.5 text-xs text-zinc-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
              >
                {runs.map((item) => (
                  <option key={item.id} value={item.id}>
                    #{item.id} · {item.sample_size} matches · {shortDigest(item.dataset_digest)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <button
            type="button"
            onClick={() => void computeEvaluation()}
            disabled={pending}
            className="inline-flex items-center rounded-lg border border-white/15 px-3 py-1.5 text-sm text-zinc-200 transition-colors hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {pending
              ? "Evaluating corpus…"
              : empty
                ? "Compute evaluation"
                : "Re-run evaluation"}
          </button>
        </div>
      </div>

      {actionError && (
        <div
          role="alert"
          className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300"
        >
          {actionError}
        </div>
      )}

      {loading && (
        <div className="animate-pulse space-y-4" aria-busy="true" aria-live="polite">
          <div className="h-24 rounded-xl border border-white/10 bg-white/5" />
          <div className="h-64 rounded-xl border border-white/10 bg-white/5" />
          <div className="h-40 rounded-xl border border-white/10 bg-white/5" />
        </div>
      )}

      {!loading && error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-6 py-5" role="alert">
          <h3 className="font-semibold text-red-200">Evaluation unavailable</h3>
          <p className="mt-1 text-sm text-red-300">{error}</p>
          <button
            type="button"
            onClick={() => {
              setError(null);
              setLoading(true);
              void bootstrap();
            }}
            className="mt-4 inline-flex items-center rounded-lg border border-white/15 px-3 py-1.5 text-sm text-zinc-200 transition-colors hover:bg-white/5"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && empty && (
        <div className="rounded-xl border border-white/10 bg-[#0f0f11] px-6 py-8 text-center">
          <h3 className="text-lg font-semibold text-white">No stored evaluation</h3>
          <p className="mx-auto mt-2 max-w-xl text-sm text-zinc-400 leading-relaxed">
            The dashboard only displays persisted runs; it never computes numbers in the
            browser. Computing the evaluation replays the stored corpus chronologically
            and stores the result. It requires enough verified history for at least one
            competition.
          </p>
          <button
            type="button"
            onClick={() => void computeEvaluation()}
            disabled={pending}
            className="mt-5 inline-flex items-center rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {pending ? "Evaluating corpus…" : "Compute evaluation"}
          </button>
        </div>
      )}

      {!loading && !error && run && (
        <Report run={run} runs={runs} onSelectRun={selectRun} />
      )}
    </div>
  );
}

function Report({
  run,
  runs,
  onSelectRun,
}: {
  run: EvaluationRun;
  runs: EvaluationRunSummary[];
  onSelectRun: (id: number) => Promise<void>;
}) {
  const report = run.report;
  if (!report.evaluated) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-6 py-5">
        <h3 className="font-semibold text-amber-200">Evaluation abstained</h3>
        <p className="mt-1 text-sm text-amber-300">
          Reason: {report.reason ?? "not recorded"}. No metrics are displayed.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ProvenancePanel run={run} report={report} />
      <Overview report={report} />
      <ModelTable report={report} />
      <PairedTable report={report} />
      <PerOutcomeSection report={report} />
      <CalibrationSection report={report} />
      <CompetitionSection report={report} />
      <SeasonSection report={report} />
      <TimelineSection report={report} />
      <RunsTable runs={runs} selectedId={run.id} onSelectRun={onSelectRun} />
      <NotesPanel report={report} />
    </div>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-white/10 bg-[#0f0f11] p-5 sm:p-6">
      <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400">
        {title}
      </h3>
      {description && (
        <p className="mt-1 text-xs text-zinc-500 leading-relaxed">{description}</p>
      )}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function ProvenancePanel({
  run,
  report,
}: {
  run: EvaluationRun;
  report: EvaluationReportBody;
}) {
  const dataset = report.dataset;
  return (
    <Section
      title="Provenance and dataset identity"
      description="A stored run is identified by protocol version, evaluation version, and dataset digest. Re-running an unchanged corpus returns this same record."
    >
      <dl className="grid grid-cols-1 gap-x-8 gap-y-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Run" value={`#${run.id}`} />
        <Field label="Protocol" value={run.protocol_version} />
        <Field label="Evaluation version" value={run.evaluation_version} />
        <Field label="Provider" value={dataset?.provider_code ?? "not recorded"} />
        <Field label="Classification" value={dataset?.classification ?? "not recorded"} />
        <Field label="Generated" value={formatDate(run.generated_at)} />
        <Field
          label="Dataset digest"
          value={shortDigest(run.dataset_digest)}
          title={run.dataset_digest}
          mono
        />
        <Field label="Stored matches" value={String(dataset?.matches ?? "—")} />
        <Field
          label="Competitions"
          value={String(dataset?.competitions ?? "—")}
        />
        <Field
          label="Raw retrieval from"
          value={formatDate(dataset?.retrieval_from)}
        />
        <Field label="Observed to" value={formatDate(dataset?.observed_to)} />
        <Field
          label="Result horizon"
          value={`${report.settings?.result_horizon_hours ?? "—"} h`}
        />
      </dl>
      <p className="mt-4 rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3 text-xs leading-relaxed text-zinc-400">
        <span className="font-semibold text-zinc-300">Observation limitation: </span>
        stored results were backfilled in one retrieval window. A result&apos;s
        resolution time is local ingestion time, not a verified provider publication
        time, so the evaluation uses a kickoff + 3 hour eligibility horizon. This is a
        retrospective reconstruction, not a replay of what was known live at each
        historical moment.
      </p>
    </Section>
  );
}

function Field({
  label,
  value,
  title,
  mono = false,
}: {
  label: string;
  value: string;
  title?: string;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-zinc-500">{label}</dt>
      <dd
        className={`mt-0.5 text-zinc-200 ${mono ? "font-mono text-xs" : ""}`}
        title={title}
      >
        {value}
      </dd>
    </div>
  );
}

function Overview({ report }: { report: EvaluationReportBody }) {
  const cards = [
    { label: "Evaluated matches", value: String(report.sample_size) },
    {
      label: "Window",
      value:
        report.window
          ? `${formatDate(report.window.from)} → ${formatDate(report.window.to)}`
          : "—",
    },
    { label: "Models", value: String(report.models.length) },
    {
      label: "Prior-match minimum",
      value: String(report.settings?.min_prior_matches ?? "—"),
    },
    {
      label: "Test cap per competition",
      value: String(report.settings?.max_test_per_competition ?? "—"),
    },
    {
      label: "Bootstrap resamples",
      value: String(report.settings?.bootstrap_resamples ?? "—"),
    },
  ];

  return (
    <Section
      title="Overview"
      description="One chronological pass scores every model on exactly the same matches. Metrics are not re-sampled per model."
    >
      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-3"
          >
            <dt className="text-xs text-zinc-500">{card.label}</dt>
            <dd className="mt-1 text-sm font-semibold text-white">{card.value}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

function ModelTable({ report }: { report: EvaluationReportBody }) {
  const ordered = [...report.models].sort(
    (left, right) =>
      MODEL_ORDER.indexOf(left.key as (typeof MODEL_ORDER)[number]) -
      MODEL_ORDER.indexOf(right.key as (typeof MODEL_ORDER)[number]),
  );

  return (
    <Section
      title="Model comparison"
      description="Every model is scored on the identical match set. Lower Brier and log loss are better; skill is measured against the uniform baseline. Confidence intervals are percentile bootstraps with a fixed seed."
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-zinc-500">
              <th className="py-2 pr-3 font-medium">Model</th>
              <th className="py-2 px-3 font-medium">Role</th>
              <th className="py-2 px-3 text-right font-medium">Brier</th>
              <th className="py-2 px-3 text-right font-medium">95% CI</th>
              <th className="py-2 px-3 text-right font-medium">Log loss</th>
              <th className="py-2 px-3 text-right font-medium">Skill vs uniform</th>
              <th className="py-2 px-3 text-right font-medium">ECE</th>
              <th className="py-2 px-3 text-right font-medium">MCE</th>
              <th className="py-2 px-3 text-right font-medium">Top-pick</th>
              <th className="py-2 pl-3 text-right font-medium">n</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((model) => (
              <tr key={model.key} className="border-b border-white/5">
                <td className="py-2.5 pr-3">
                  <div className="font-medium text-zinc-100">
                    {model.label || MODEL_LABELS[model.key] || model.key}
                  </div>
                  <div className="text-xs text-zinc-500">{model.model_version}</div>
                </td>
                <td className="py-2.5 px-3 text-zinc-400">{model.role ?? "—"}</td>
                <td className="py-2.5 px-3 text-right font-mono text-zinc-100">
                  {num(model.brier_score)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-xs text-zinc-400">
                  {model.bootstrap?.brier_ci
                    ? `${num(model.bootstrap.brier_ci.lower)} – ${num(
                        model.bootstrap.brier_ci.upper,
                      )}`
                    : "—"}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-zinc-200">
                  {num(model.log_loss)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-zinc-200">
                  {num(model.brier_skill_score_vs_uniform)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-zinc-200">
                  {num(model.expected_calibration_error)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-zinc-400">
                  {num(model.maximum_calibration_error)}
                </td>
                <td className="py-2.5 px-3 text-right font-mono text-zinc-400">
                  {pct(model.top_pick_accuracy)}
                </td>
                <td className="py-2.5 pl-3 text-right font-mono text-zinc-500">
                  {model.sample_size}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-zinc-500 leading-relaxed">
        A lower point estimate does not by itself establish a better model. The confidence
        intervals overlap on this sample; read the paired differences below before drawing
        a conclusion.
      </p>
    </Section>
  );
}

function PairedTable({ report }: { report: EvaluationReportBody }) {
  if (report.comparisons.length === 0) {
    return (
      <Section title="Paired differences">
        <p className="text-sm text-zinc-400">
          No paired comparison was recorded for this run.
        </p>
      </Section>
    );
  }

  return (
    <Section
      title="Paired differences against Poisson"
      description="Positive means the baseline (Poisson) had the higher loss on the same matches. Intervals are paired bootstraps, so they describe the difference, not two independent samples."
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-zinc-500">
              <th className="py-2 pr-3 font-medium">Candidate</th>
              <th className="py-2 px-3 text-right font-medium">Brier difference</th>
              <th className="py-2 px-3 text-right font-medium">95% CI</th>
              <th className="py-2 px-3 text-right font-medium">Log-loss difference</th>
              <th className="py-2 px-3 text-right font-medium">95% CI</th>
              <th className="py-2 pl-3 font-medium">Reading</th>
            </tr>
          </thead>
          <tbody>
            {report.comparisons.map((item) => {
              const brier = item.brier_difference;
              const log = item.log_loss_difference;
              const crossesZero =
                brier?.lower != null &&
                brier?.upper != null &&
                brier.lower <= 0 &&
                brier.upper >= 0;
              return (
                <tr key={item.candidate} className="border-b border-white/5">
                  <td className="py-2.5 pr-3 text-zinc-100">
                    {modelLabel(item.candidate, report.models)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-zinc-200">
                    {num(brier?.mean)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-xs text-zinc-400">
                    {brier
                      ? `${num(brier.lower)} – ${num(brier.upper)}`
                      : "—"}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-zinc-200">
                    {num(log?.mean)}
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono text-xs text-zinc-400">
                    {log ? `${num(log.lower)} – ${num(log.upper)}` : "—"}
                  </td>
                  <td className="py-2.5 pl-3 text-xs text-zinc-400">
                    {brier
                      ? crossesZero
                        ? "Interval includes zero: no clear difference."
                        : brier.mean != null && brier.mean > 0
                          ? "Poisson has the higher loss on this sample."
                          : "Candidate has the higher loss on this sample."
                      : "Not evaluated."}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function PerOutcomeSection({ report }: { report: EvaluationReportBody }) {
  return (
    <Section
      title="Per-outcome metrics"
      description="Each outcome is scored as its own binary problem. This is where a systematic draw bias becomes visible instead of rhetorical."
    >
      <div className="space-y-3">
        {report.models.map((model) => (
          <details
            key={model.key}
            className="rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3"
          >
            <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
              {model.label || MODEL_LABELS[model.key] || model.key}
            </summary>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[520px] text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-left text-zinc-500">
                    <th className="py-1.5 pr-3 font-medium">Outcome</th>
                    <th className="py-1.5 px-2 text-right font-medium">Observed rate</th>
                    <th className="py-1.5 px-2 text-right font-medium">Mean probability</th>
                    <th className="py-1.5 px-2 text-right font-medium">Gap</th>
                    <th className="py-1.5 px-2 text-right font-medium">Brier</th>
                    <th className="py-1.5 pl-2 text-right font-medium">Log loss</th>
                    <th className="py-1.5 pl-2 text-right font-medium">n</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(model.per_outcome).map(([outcome, metrics]) => (
                    <tr key={outcome} className="border-b border-white/5">
                      <td className="py-1.5 pr-3 capitalize text-zinc-300">{outcome}</td>
                      <td className="py-1.5 px-2 text-right font-mono text-zinc-200">
                        {pct(metrics.observed_rate)}
                      </td>
                      <td className="py-1.5 px-2 text-right font-mono text-zinc-200">
                        {pct(metrics.mean_probability)}
                      </td>
                      <td
                        className={`py-1.5 px-2 text-right font-mono ${
                          metrics.calibration_gap != null &&
                          Math.abs(metrics.calibration_gap) >= 0.01
                            ? "text-amber-300"
                            : "text-zinc-400"
                        }`}
                      >
                        {metrics.calibration_gap != null && metrics.calibration_gap > 0
                          ? "+"
                          : ""}
                        {num(metrics.calibration_gap)}
                      </td>
                      <td className="py-1.5 px-2 text-right font-mono text-zinc-200">
                        {num(metrics.brier_score)}
                      </td>
                      <td className="py-1.5 pl-2 text-right font-mono text-zinc-400">
                        {num(metrics.log_loss)}
                      </td>
                      <td className="py-1.5 pl-2 text-right font-mono text-zinc-500">
                        {metrics.sample_size}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        ))}
      </div>
      <p className="mt-3 text-xs text-zinc-500">
        Gap = mean predicted probability minus observed rate. A positive gap means the
        outcome was over-predicted; a negative gap means it was under-predicted.
      </p>
    </Section>
  );
}

function CalibrationSection({ report }: { report: EvaluationReportBody }) {
  return (
    <Section
      title="Reliability by probability bin"
      description="Bins are fixed-width probability buckets. A well-calibrated model has a mean predicted probability close to the observed rate in every bin."
    >
      <div className="space-y-3">
        {report.models.map((model) => (
          <details
            key={model.key}
            className="rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3"
          >
            <summary className="cursor-pointer text-sm font-semibold text-zinc-200">
              {model.label || MODEL_LABELS[model.key] || model.key}
              <span className="ml-2 text-xs font-normal text-zinc-500">
                ECE {num(model.expected_calibration_error)}
              </span>
            </summary>
            <div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-3">
              {model.calibration.map((group) => (
                <CalibrationGroup key={group.class_label} group={group} />
              ))}
            </div>
          </details>
        ))}
      </div>
    </Section>
  );
}

function CalibrationGroup({ group }: { group: AnalysisClassCalibration }) {
  return (
    <div>
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
          {group.class_label}
        </span>
        <span className="text-xs text-zinc-500">
          MCE {num(group.maximum_calibration_error)} · n = {group.sample_size}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/10 text-left text-zinc-500">
              <th className="py-1.5 font-medium">Bin</th>
              <th className="py-1.5 text-right font-medium">n</th>
              <th className="py-1.5 text-right font-medium">Predicted</th>
              <th className="py-1.5 text-right font-medium">Observed</th>
            </tr>
          </thead>
          <tbody>
            {group.bins.map((bin) => (
              <tr key={`${bin.lower}-${bin.upper}`} className="border-b border-white/5">
                <td className="py-1.5 font-mono text-zinc-400">
                  {num(bin.lower, 2)}–{num(bin.upper, 2)}
                </td>
                <td className="py-1.5 text-right font-mono text-zinc-500">
                  {bin.sample_size}
                </td>
                <td className="py-1.5 text-right font-mono text-zinc-200">
                  {pct(bin.mean_probability)}
                </td>
                <td className="py-1.5 text-right font-mono text-zinc-200">
                  {pct(bin.observed_rate)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CompetitionSection({ report }: { report: EvaluationReportBody }) {
  return (
    <Section
      title="Per-competition performance"
      description="Competition identifiers are stored internal ids; the evaluation does not invent names. A competition below the history minimum is reported, never scored."
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-zinc-500">
              <th className="py-2 pr-3 font-medium">Competition</th>
              <th className="py-2 px-2 text-right font-medium">Matches</th>
              <th className="py-2 px-2 font-medium">Status</th>
              <th className="py-2 px-2 text-right font-medium">Skipped (history)</th>
              <th className="py-2 px-2 text-right font-medium">Skipped (abstain)</th>
              {MODEL_ORDER.map((key) => (
                <th key={key} className="py-2 px-2 text-right font-medium">
                  {MODEL_LABELS[key]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.competitions.map((competition) => (
              <tr key={competition.competition_id} className="border-b border-white/5">
                <td className="py-2 pr-3 text-zinc-200">
                  #{competition.competition_id}
                  {competition.fitted_parameters && (
                    <span className="block text-xs text-zinc-500">
                      rho {num(competition.fitted_parameters.rho, 3)} · Elo H{" "}
                      {num(competition.fitted_parameters.elo_home_advantage, 1)} · ν{" "}
                      {num(competition.fitted_parameters.elo_draw_nu, 2)}
                    </span>
                  )}
                </td>
                <td className="py-2 px-2 text-right font-mono text-zinc-300">
                  {competition.sample_size}
                </td>
                <td className="py-2 px-2 text-zinc-400">{competition.status}</td>
                <td className="py-2 px-2 text-right font-mono text-zinc-500">
                  {competition.diagnostics.skipped_history}
                </td>
                <td className="py-2 px-2 text-right font-mono text-zinc-500">
                  {competition.diagnostics.skipped_model_abstention}
                </td>
                {MODEL_ORDER.map((key) => (
                  <td
                    key={key}
                    className="py-2 px-2 text-right font-mono text-zinc-200"
                  >
                    {modelBrier(competition.models, key)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {report.insufficient_competitions.length > 0 && (
        <div className="mt-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
            Insufficient history
          </h4>
          <ul className="mt-2 space-y-1 text-sm text-zinc-400">
            {report.insufficient_competitions.map((item) => (
              <li key={item.competition_id}>
                #{item.competition_id}: {item.sample_size} matches, {item.required}{" "}
                required ({item.status}).
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="mt-3 text-xs text-zinc-500">
        Cells show Brier score per model. Small per-competition samples produce unstable
        estimates; the overall run is the primary measurement.
      </p>
    </Section>
  );
}

function SeasonSection({ report }: { report: EvaluationReportBody }) {
  return (
    <Section
      title="Per-season performance"
      description="Seasons are stored internal ids. Per-season blocks are descriptive and are not used to claim a trend."
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-zinc-500">
              <th className="py-2 pr-3 font-medium">Competition</th>
              <th className="py-2 px-2 font-medium">Season</th>
              <th className="py-2 px-2 text-right font-medium">Matches</th>
              {MODEL_ORDER.map((key) => (
                <th key={key} className="py-2 px-2 text-right font-medium">
                  {MODEL_LABELS[key]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.seasons.map((season: EvaluationSeason) => (
              <tr
                key={`${season.competition_id}-${season.season_id}`}
                className="border-b border-white/5"
              >
                <td className="py-2 pr-3 text-zinc-200">#{season.competition_id}</td>
                <td className="py-2 px-2 text-zinc-400">#{season.season_id}</td>
                <td className="py-2 px-2 text-right font-mono text-zinc-300">
                  {season.sample_size}
                </td>
                {MODEL_ORDER.map((key) => (
                  <td key={key} className="py-2 px-2 text-right font-mono text-zinc-200">
                    {modelBrier(season.models, key)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function TimelineSection({ report }: { report: EvaluationReportBody }) {
  return (
    <Section
      title="Chronological timeline"
      description="Consecutive match buckets in kickoff order. A bucket is a descriptive slice, not a forecast of future performance."
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-zinc-500">
              <th className="py-2 pr-3 font-medium">From</th>
              <th className="py-2 px-2 font-medium">To</th>
              <th className="py-2 px-2 text-right font-medium">Matches</th>
              {MODEL_ORDER.map((key) => (
                <th key={key} className="py-2 px-2 text-right font-medium">
                  {MODEL_LABELS[key]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.timeline.map((bucket) => (
              <tr key={`${bucket.from}-${bucket.to}`} className="border-b border-white/5">
                <td className="py-2 pr-3 text-xs text-zinc-400">
                  {formatDate(bucket.from)}
                </td>
                <td className="py-2 px-2 text-xs text-zinc-400">{formatDate(bucket.to)}</td>
                <td className="py-2 px-2 text-right font-mono text-zinc-300">
                  {bucket.sample_size}
                </td>
                {MODEL_ORDER.map((key) => (
                  <td key={key} className="py-2 px-2 text-right font-mono text-zinc-200">
                    {num(bucket.models[key]?.brier_score)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function RunsTable({
  runs,
  selectedId,
  onSelectRun,
}: {
  runs: EvaluationRunSummary[];
  selectedId: number;
  onSelectRun: (id: number) => Promise<void>;
}) {
  return (
    <Section
      title="Stored runs"
      description="Evaluation runs are append-only. A different dataset digest creates a new run rather than overwriting history."
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-zinc-500">
              <th className="py-2 pr-3 font-medium">Run</th>
              <th className="py-2 px-2 font-medium">Protocol</th>
              <th className="py-2 px-2 font-medium">Version</th>
              <th className="py-2 px-2 text-right font-medium">Matches</th>
              <th className="py-2 px-2 font-medium">Generated</th>
              <th className="py-2 pl-2 font-medium">Digest</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((item) => (
              <tr
                key={item.id}
                className={`border-b border-white/5 ${
                  item.id === selectedId ? "bg-white/[0.03]" : ""
                }`}
              >
                <td className="py-2 pr-3">
                  <button
                    type="button"
                    onClick={() => void onSelectRun(item.id)}
                    className="text-emerald-400 underline-offset-2 hover:underline"
                  >
                    #{item.id}
                  </button>
                </td>
                <td className="py-2 px-2 text-zinc-400">{item.protocol_version}</td>
                <td className="py-2 px-2 text-zinc-400">{item.evaluation_version}</td>
                <td className="py-2 px-2 text-right font-mono text-zinc-300">
                  {item.sample_size}
                </td>
                <td className="py-2 px-2 text-xs text-zinc-400">
                  {formatDate(item.generated_at)}
                </td>
                <td className="py-2 pl-2 font-mono text-xs text-zinc-500">
                  {shortDigest(item.dataset_digest)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function NotesPanel({ report }: { report: EvaluationReportBody }) {
  return (
    <Section title="Recorded notes">
      <ul className="list-disc space-y-1 pl-5 text-sm text-zinc-400">
        {report.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
        <li>
          Comparing model outputs is not an accuracy claim. Only the stored evaluation on
          an identical, chronological match set supports a measurement.
        </li>
        <li>
          No odds, betting market, or commercial product is implemented in this phase.{" "}
          <Link href="/" className="text-emerald-400 hover:underline">
            Back to matches
          </Link>
          .
        </li>
      </ul>
    </Section>
  );
}
