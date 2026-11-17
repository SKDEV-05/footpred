export interface Country {
  id: number;
  name: string;
  iso_code: string | null;
}

export interface TeamRef {
  id: number;
  name: string;
  crest_url: string | null;
}

export interface CompetitionRef {
  id: number;
  name: string;
  code: string | null;
  country: Country | null;
  emblem_url: string | null;
}

export interface SeasonRef {
  id: number;
  label: string;
}

export interface Score {
  home: number;
  away: number;
}

export interface Fixture {
  id: number;
  competition: CompetitionRef;
  season: SeasonRef;
  home_team: TeamRef;
  away_team: TeamRef;
  kickoff_utc: string;
  status: string;
  matchday: number | null;
  stage: string | null;
  venue_name: string | null;
  score: Score | null;
}

export interface FixtureDetail extends Fixture {
  attendance: number | null;
  last_synced_at: string;
  provider_last_updated: string | null;
  statistics_available: boolean;
  result: {
    home_score: number | null;
    away_score: number | null;
    ht_home_score: number | null;
    ht_away_score: number | null;
    winner: string | null;
    duration: string | null;
    is_final: boolean;
    resolved_at: string;
  } | null;
}

export interface CompetitionSummary {
  id: number;
  name: string;
  code: string | null;
  type: string;
  country: Country | null;
  emblem_url: string | null;
}

export interface TodayResponse {
  date: string;
  timezone: string;
  date_from_utc: string;
  date_to_utc: string;
  items: Fixture[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface TeamStatistics {
  team_id: number;
  team_name: string;
  metrics: Record<string, number>;
}

export interface StatisticsResponse {
  match_id: number;
  available: boolean;
  teams: TeamStatistics[];
}

export interface TeamSummary {
  id: number;
  name: string;
  short_name: string | null;
  tla: string | null;
  country: Country | null;
  crest_url: string | null;
}

export interface JobFreshness {
  job_type: string;
  last_success_at: string | null;
  last_completed_at: string | null;
  last_completed_status: string | null;
  records_stored: number | null;
}

export interface SyncStatus {
  last_successful_sync_at: string | null;
  last_run_at: string | null;
  last_run_status: string | null;
  stale_running_count: number;
  per_job_type: JobFreshness[];
  data_is_stale: boolean;
}

export type AnalysisStatus =
  | "READY"
  | "INSUFFICIENT_DATA"
  | "DATA_UNAVAILABLE"
  | "ANALYSIS_FAILED";

export interface AnalysisTeamRecord {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  win_rate: number | null;
  goals_for: number;
  goals_against: number;
  goals_for_avg: number | null;
  goals_against_avg: number | null;
  clean_sheets: number;
  failed_to_score: number;
}

export interface AnalysisTeamContext {
  overall: AnalysisTeamRecord;
  venue_specific: AnalysisTeamRecord;
  recent_form: string;
  recent_matches: number;
  recent_goals_for_avg: number | null;
  recent_goals_against_avg: number | null;
  sample_size: number;
}

export interface AnalysisHeadToHead {
  meetings_count: number;
  home_wins: number;
  draws: number;
  away_wins: number;
  home_goals: number;
  away_goals: number;
  limited_sample: boolean;
}

export interface AnalysisHistoricalContext {
  home_team: AnalysisTeamContext;
  away_team: AnalysisTeamContext;
  head_to_head: AnalysisHeadToHead;
  competition_matches_analyzed: number;
  competition_avg_home_goals: number;
  competition_avg_away_goals: number;
  home_advantage_ratio: number | null;
  baseline_source: string;
  baseline_sample_sufficient: boolean;
}

/**
 * Model parameters differ by model: Poisson reports rates and strengths, Elo reports
 * ratings and its fitted mapping. The mapping is intentionally open so neither model is
 * forced to invent fields it does not have.
 */
export type AnalysisModelParameters = Record<string, unknown>;

export interface AnalysisScoreline {
  home_goals: number;
  away_goals: number;
  probability: number;
}

export interface AnalysisStatisticalModel {
  model_id: string;
  model_version: string;
  feature_version: string | null;
  expected_home_goals: number | null;
  expected_away_goals: number | null;
  home_win_probability: number | null;
  draw_probability: number | null;
  away_win_probability: number | null;
  btts_probability: number | null;
  over_1_5_probability: number | null;
  under_1_5_probability: number | null;
  over_2_5_probability: number | null;
  under_2_5_probability: number | null;
  over_3_5_probability: number | null;
  under_3_5_probability: number | null;
  scoreline_probabilities: AnalysisScoreline[];
  model_parameters: AnalysisModelParameters | null;
}

export type AnalysisModelKey = "poisson" | "dixon_coles" | "elo";

export interface ModelComparisonItem {
  key: AnalysisModelKey;
  model_id: string;
  model_version: string;
  status: AnalysisStatus;
  home_win_probability: number | null;
  draw_probability: number | null;
  away_win_probability: number | null;
  expected_home_goals: number | null;
  expected_away_goals: number | null;
  reason: string | null;
  analysis_id: number | null;
  limitations: string[];
}

export interface ModelComparison {
  match_id: number;
  analysis_as_of: string;
  dataset_id: string | null;
  dataset_digest: string | null;
  models: ModelComparisonItem[];
  notes: string[];
}

export interface AnalysisCalibrationBin {
  lower: number;
  upper: number;
  sample_size: number;
  mean_probability: number | null;
  observed_rate: number | null;
}

export interface AnalysisClassCalibration {
  class_label: string;
  sample_size: number;
  expected_calibration_error: number | null;
  maximum_calibration_error: number | null;
  bins: AnalysisCalibrationBin[];
}

export interface AnalysisEvaluation {
  evaluated: boolean;
  reason: string | null;
  sample_size: number | null;
  brier_score: number | null;
  log_loss: number | null;
  uniform_brier_score: number | null;
  uniform_log_loss: number | null;
  brier_skill_score: number | null;
  expected_calibration_error: number | null;
  maximum_calibration_error: number | null;
  calibration: AnalysisClassCalibration[];
  class_labels: string[];
  model_id: string | null;
  model_version: string | null;
  feature_version: string | null;
  evaluation_version: string | null;
  dataset_id: string | null;
  dataset_digest: string | null;
  evaluation_type: string | null;
  test_period_from: string | null;
  test_period_to: string | null;
}

export interface AnalysisDataQuality {
  data_classification: string;
  dataset_id: string | null;
  dataset_digest: string | null;
  provider_code: string | null;
  historical_matches: number | null;
  competition_matches: number | null;
  excluded_extra_time_or_shootout: number | null;
  earliest_kickoff: string | null;
  latest_kickoff: string | null;
  retrieval_from: string | null;
  retrieval_to: string | null;
  home_sample_size: number | null;
  away_sample_size: number | null;
  h2h_sample_size: number | null;
  statistics_available: boolean;
  statistics_note: string;
  missing_features: string[];
  limitations: string[];
  data_freshness_note: string | null;
}

export interface AnalysisExplanation {
  model_rationale: string;
  expected_goals_breakdown: Record<string, string>;
  form_impact: string;
  h2h_impact: string;
}

export interface MatchAnalysis {
  id: number;
  match_id: number;
  status: AnalysisStatus;
  generated_at: string;
  analysis_as_of: string;
  match_overview: {
    match_id: number;
    competition: CompetitionRef;
    season: SeasonRef;
    home_team: TeamRef;
    away_team: TeamRef;
    kickoff_utc: string;
  };
  historical_context: AnalysisHistoricalContext | null;
  statistical_model: AnalysisStatisticalModel | null;
  data_quality: AnalysisDataQuality;
  explanation: AnalysisExplanation | null;
  evaluation: AnalysisEvaluation | null;
  error_message: string | null;
}

export interface AnalysisHistoryItem {
  id: number;
  match_id: number;
  status: AnalysisStatus;
  model_version: string;
  generated_at: string;
  home_win_probability: number | null;
  draw_probability: number | null;
  away_win_probability: number | null;
}


// --------------------------------------------------------------- evaluation API

export interface EvaluationSettings {
  min_prior_matches: number;
  max_test_per_competition: number;
  result_horizon_hours: number;
  bootstrap_resamples: number;
  bootstrap_seed: number;
  calibration_bins: number;
  timeline_bucket_size: number;
}

export interface EvaluationDataset {
  dataset_id: string | null;
  dataset_digest: string | null;
  classification: string | null;
  matches: number | null;
  competitions: number | null;
  provider_code: string | null;
  retrieval_from: string | null;
  observed_to: string | null;
}

export interface EvaluationBootstrap {
  resamples: number;
  seed: number;
  brier_ci: Record<string, number> | null;
  log_loss_ci: Record<string, number> | null;
}

export interface EvaluationOutcomeMetrics {
  sample_size: number;
  observed_rate: number | null;
  mean_probability: number | null;
  calibration_gap: number | null;
  brier_score: number | null;
  log_loss: number | null;
}

export interface EvaluationModelMetrics {
  key: string;
  model_id: string | null;
  model_version: string | null;
  label: string | null;
  role: string | null;
  evaluated: boolean;
  reason: string | null;
  sample_size: number;
  brier_score: number | null;
  log_loss: number | null;
  brier_skill_score_vs_uniform: number | null;
  expected_calibration_error: number | null;
  maximum_calibration_error: number | null;
  calibration: AnalysisClassCalibration[];
  mean_probabilities: Record<string, number>;
  observed_frequencies: Record<string, number>;
  per_outcome: Record<string, EvaluationOutcomeMetrics>;
  top_pick_accuracy: number | null;
  bootstrap: EvaluationBootstrap | null;
}

export interface EvaluationPairedComparison {
  reference: string;
  candidate: string;
  evaluated: boolean;
  reason: string | null;
  sample_size: number | null;
  brier_difference: {
    mean: number | null;
    lower: number | null;
    upper: number | null;
    interpretation: string | null;
  } | null;
  log_loss_difference: {
    mean: number | null;
    lower: number | null;
    upper: number | null;
    interpretation: string | null;
  } | null;
}

export interface EvaluationCompetition {
  competition_id: string;
  sample_size: number;
  status: string;
  diagnostics: {
    evaluated: number;
    skipped_model_abstention: number;
    skipped_history: number;
  };
  fitted_parameters: {
    rho: number | null;
    rho_status: string | null;
    rho_matches: number | null;
    elo_home_advantage: number | null;
    elo_draw_nu: number | null;
    elo_status: string | null;
    training_matches: number | null;
  } | null;
  models: Record<string, EvaluationModelMetrics>;
}

export interface EvaluationSeason {
  competition_id: string;
  season_id: string;
  sample_size: number;
  models: Record<string, EvaluationModelMetrics>;
}

export interface EvaluationTimelineBucket {
  from: string;
  to: string;
  sample_size: number;
  models: Record<string, { brier_score: number | null; sample_size: number } | null>;
}

export interface EvaluationReportBody {
  evaluated: boolean;
  reason: string | null;
  protocol_version: string;
  evaluation_version: string;
  settings: EvaluationSettings | null;
  dataset: EvaluationDataset | null;
  window: { from: string; to: string } | null;
  sample_size: number;
  models: EvaluationModelMetrics[];
  comparisons: EvaluationPairedComparison[];
  competitions: EvaluationCompetition[];
  seasons: EvaluationSeason[];
  timeline: EvaluationTimelineBucket[];
  insufficient_competitions: {
    competition_id: string;
    status: string;
    sample_size: number;
    required: number;
  }[];
  notes: string[];
}

export interface EvaluationRun {
  id: number;
  protocol_version: string;
  evaluation_version: string;
  dataset_id: string | null;
  dataset_digest: string;
  provider_code: string | null;
  sample_size: number;
  window_from: string | null;
  window_to: string | null;
  generated_at: string;
  report: EvaluationReportBody;
}

export interface EvaluationRunSummary {
  id: number;
  protocol_version: string;
  evaluation_version: string;
  dataset_id: string | null;
  dataset_digest: string;
  sample_size: number;
  window_from: string | null;
  window_to: string | null;
  generated_at: string;
  model_keys: string[];
}
