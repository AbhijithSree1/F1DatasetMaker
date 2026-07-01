export interface Team {
  team_id: string
  team_name: string
  color: string
  pace_factor?: number
}

export interface Driver {
  season: number
  driver_id: string
  driver_number: number
  abbreviation: string
  full_name: string
  team_id: string
  team_name: string
  color: string
}

export interface SessionInfo {
  session_id: string
  season: number
  round_number: number
  event_name: string
  session_name: string
  session_type: string
  circuit: string
  country: string
}

export interface Meta {
  generated_at: string
  synthetic: boolean
  event_name: string
  circuit: string
  country: string
  track: {
    length_m: number
    drs_zones: { start_m: number; end_m: number }[]
    speed_profile: { distance_m: number; speed_kph: number }[]
  }
  teams: Team[]
  drivers: Driver[]
  sessions: SessionInfo[]
}

export interface StandingRow {
  position: number
  driver_id: string
  full_name: string
  team_name: string
  color: string
  points: number
  total_time_s: number
  gap_to_leader_s: number
  grid_position: number
}

export interface FastestLap {
  driver_id: string
  full_name: string
  team_name: string
  color: string
  lap_number: number
  lap_time_s: number
}

export interface PositionByLap {
  lap_number: number
  driver_id: string
  position: number
  abbreviation: string
  team_id: string
}

export interface Overview {
  standings: StandingRow[]
  fastest_lap: FastestLap
  position_by_lap: PositionByLap[]
  total_laps: number
}

export interface LapTimeRow {
  driver_id: string
  full_name: string
  team_name: string
  color: string
  lap_number: number
  lap_time_s: number
  compound: string
  track_status: string
  pit_in_lap: boolean
  pit_out_lap: boolean
}

export interface Stint {
  session_id: string
  driver_id: string
  stint_number: number
  compound: string
  tyre_age_at_start_laps: number
  lap_start: number
  lap_end: number
  full_name: string
  team_name: string
  color: string
}

export interface PitStop {
  session_id: string
  driver_id: string
  lap_number: number
  pit_duration_s: number
  full_name: string
}

export interface Strategy {
  stints: Stint[]
  pit_stops: PitStop[]
}

export interface TelemetryPoint {
  distance_bin_m: number
  speed_kph: number
  throttle_pct: number
  brake: number
  gear: number
  rpm: number
  drs: number
}

export interface DriverLapTrace {
  lap_number: number
  lap_time_s: number
  compound: string
  trace: TelemetryPoint[]
}

export interface TelemetryData {
  session_id: string
  fastest_laps_by_driver: Record<string, DriverLapTrace>
}

export interface DriverBehaviorRow {
  session_id: string
  driver_id: string
  full_name: string
  team_id: string
  clean_lap_count: number
  median_clean_lap_s: number
  consistency_std_s: number
  pace_rank: number
  teammate_delta_s: number | null
  avg_brake_events_per_lap: number
  avg_full_throttle_pct_of_lap: number
  avg_gear_shifts_per_lap: number
  avg_top_speed_kph: number
}

export interface TireDegradationRow {
  session_id: string
  driver_id: string
  stint_number: number
  compound: string
  lap_number: number
  tyre_age_laps: number
  stint_lap_index: number
  lap_time_s: number
  stint_best_lap_s: number
  delta_to_stint_best_s: number
  full_name: string
  team_name: string
  color: string
}

export interface SchemaReportRow {
  table: string
  row_count: number
  missing_columns: string[]
  extra_columns: string[]
  null_rates: Record<string, number>
  passed: boolean | null
}

export interface SanityCheckRow {
  check: string
  table: string
  passed: boolean | null
  detail: string
}

export interface DataQuality {
  schema_report: SchemaReportRow[]
  sanity_checks: SanityCheckRow[]
}
