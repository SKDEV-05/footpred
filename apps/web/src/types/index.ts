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

export interface AnalysisModelParameters {
  baseline_avg_home_goals: number;
  baseline_avg_away_goals: number;
  baseline_source: string;
  home_attack_strength: number;
  home_defence_strength: number;
  away_attack_strength: number;
  away_defence_strength: number;
  home_recent_weight: number;
  away_recent_weight: number;
  expected_goals_bounds: number[];
}

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
