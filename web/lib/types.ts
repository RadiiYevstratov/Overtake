/** Response shapes mirroring `overtake/routes/schemas.py`. */

export type Plan = "free" | "pro";
export type Variance = "seek" | "suppress" | "neutral";

export interface Manager {
  entry_id: number;
  player_name: string;
  team_name: string;
  rank: number | null;
  last_rank: number | null;
  total: number;
  event_total: number | null;
}

export interface Odds {
  entry_id: number;
  p_above: number;
  gap_now: number;
  gap_p10: number;
  gap_p50: number;
  gap_p90: number;
  catchable: boolean;
  points_per_gw_needed: number;
  variance: Variance;
}

export interface Provenance {
  n_sims: number;
  seed: number;
  model_version: string;
  projection_mae: number | null;
  projection_gameweeks: number;
  computed_at: string | null;
}

export interface Freshness {
  league_synced_at: string | null;
  simulation_computed_at: string | null;
  is_stale: boolean;
  fpl_api_ok: boolean;
}

export interface LeagueBoardRow {
  manager: Manager;
  is_you: boolean;
  p_win: number;
  expected_total: number;
  odds_vs_you: Odds | null;
}

export interface LeagueBoard {
  league: { id: number; name: string; size: number | null; type: string };
  gameweek: number;
  deadline_utc: string | null;
  rows: LeagueBoardRow[];
  you: number | null;
  catchable_count: number | null;
  total_rivals: number;
  freshness: Freshness;
  provenance: Provenance;
}

export interface Differential {
  player_id: number;
  name: string;
  team: string;
  position: string;
  price: number;
  ep_remaining: number;
}

export interface RivalProfile {
  archetype: string;
  label: string;
  blurb: string;
  hit_rate: number;
  transfers_per_gw: number;
  template_score: number;
  reactivity: number;
  bench_waste: number;
  gameweeks_observed: number;
  is_provisional: boolean;
}

export interface Move {
  key: string;
  label: string;
  kind: "captain" | "transfer";
  p_above_before: number;
  p_above_after: number;
  delta: number;
  cost: number;
  downside_p10: number;
}

export interface Dossier {
  league: { id: number; name: string };
  you: Manager;
  rival: Manager;
  gameweek: number;
  deadline_utc: string | null;
  odds: Odds;
  gameweeks_left: number;
  their_differentials: Differential[];
  your_differentials: Differential[];
  net_differential_swing: number;
  profile: RivalProfile;
  move: Move | null;
  narrative: Record<string, unknown> | null;
  locked: boolean;
  lock_reason: string | null;
  provenance: Provenance;
}

export interface Limits {
  leagues: number | null;
  dossiers_per_season: number | null;
  gaffer_messages_per_day: number | null;
  gaffer_messages_per_month: number | null;
  scenarios_per_gameweek: number | null;
  brief_regenerations_per_gameweek: number | null;
  deadline_brief: boolean;
  simulator: boolean;
  chip_planner: boolean;
  ask_the_gaffer: boolean;
}

export interface Me {
  user: {
    id: string;
    email: string;
    display_name: string | null;
    fpl_entry_id: number | null;
    age_band: string;
    marketing_opt_in: boolean;
    analytics_consent: boolean;
    created_at: string;
  };
  plan: {
    plan: Plan;
    label: string;
    status: string;
    is_pro: boolean;
    in_grace_period: boolean;
    cancel_at_period_end: boolean;
    current_period_end: string | null;
    season_pass_ends_at: string | null;
    source: string;
  };
  limits: Limits;
  usage: Record<string, number>;
  csrf_token: string | null;
}

export interface BriefContent {
  headline: string;
  primary_move: { summary: string; reasoning: string; cited_numbers: string[] };
  risk: string;
  do_nothing_case: string;
  confidence: "high" | "medium" | "low";
  generated_by?: string;
  note?: string;
}

export interface Brief {
  gameweek: number;
  content: BriefContent;
  is_fallback: boolean;
  generated_at: string;
  simulation_id: string | null;
  provenance: Provenance;
  regenerations_used: number;
  regenerations_allowed: number;
}

export interface TrackedLeague {
  league_id: number;
  name: string;
  is_primary: boolean;
  tracked: boolean;
}

export interface SeasonMeta {
  season: string;
  current_gameweek: number | null;
  next_gameweek: number | null;
  next_deadline_utc: string | null;
  players_tracked: number;
  accuracy: {
    mae: number | null;
    rmse?: number;
    gameweeks: number;
    model_version: string;
    per_gameweek?: { gameweek: number; mae: number; n: number }[];
  };
  simulations: { n_sims: number; seed: number };
}

export interface SquadPlayer {
  player_id: number;
  name: string;
  team: string;
  position: string;
  price: number;
  is_starter: boolean;
  is_captain: boolean;
  is_vice_captain: boolean;
  projected_points: number;
  start_probability: number;
  status: string;
  news: string | null;
}

export interface Squad {
  entry_id: number;
  gameweek: number;
  is_locked: boolean;
  players: SquadPlayer[];
  bank: number | null;
  team_value: number | null;
}

export interface ScenarioResult {
  baseline: Record<string, number>;
  scenarios: {
    key: string;
    label: string;
    p_above: Record<string, number>;
    delta: Record<string, number>;
  }[];
  provenance: Provenance;
}

export interface PlayerPage {
  player: {
    id: number;
    slug: string;
    name: string;
    full_name: string;
    team: string | null;
    team_short: string | null;
    team_slug: string | null;
    position: string;
    price: number;
    status: string;
    news: string | null;
    selected_by_percent: number;
    total_points: number;
    minutes: number;
    is_set_piece_taker: boolean;
  };
  projection: {
    horizon: number[];
    per_gameweek: { gameweek: number; mu: number; p_start: number }[];
    expected_points_next_6: number;
    start_probability: number | null;
  };
  history: {
    gameweek: number;
    points: number;
    minutes: number;
    goals: number;
    assists: number;
    bonus: number;
  }[];
  fixtures: {
    gameweek: number | null;
    opponent: string | null;
    is_home: boolean;
    difficulty: number | null;
    kickoff_utc: string | null;
  }[];
  accuracy: SeasonMeta["accuracy"];
}

export interface GameweekPage {
  gameweek: {
    id: number;
    name: string;
    deadline_utc: string;
    is_current: boolean;
    is_finished: boolean;
    average_score: number | null;
  };
  fixtures: {
    home: string | null;
    away: string | null;
    kickoff_utc: string | null;
    home_difficulty: number | null;
    away_difficulty: number | null;
    finished: boolean;
    score: string | null;
  }[];
  top_projected: ProjectedPlayer[];
  differentials: ProjectedPlayer[];
  captain_picks: ProjectedPlayer[];
  accuracy: SeasonMeta["accuracy"];
}

export interface ComparedPlayer {
  slug: string;
  name: string;
  team: string | null;
  team_short: string | null;
  position: string;
  price: number;
  status: string;
  news: string | null;
  selected_by_percent: number;
  total_points: number;
  minutes: number;
  is_set_piece_taker: boolean;
  expected_points_next_6: number;
  start_probability: number | null;
  per_gameweek: { gameweek: number; mu: number }[];
}

export interface PlayerComparison {
  a: ComparedPlayer;
  b: ComparedPlayer;
  horizon: number[];
  points_delta: number;
  ownership_delta: number;
  verdict: "a" | "b" | "too_close";
  differential_pick: string;
  same_position: boolean;
  accuracy: SeasonMeta["accuracy"];
}

export interface ProjectedPlayer {
  slug: string;
  name: string;
  team_short: string | null;
  position: string;
  price: number;
  projected_points: number;
  selected_by_percent: number;
}
