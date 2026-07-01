"""Driver-behavior feature table: consistency, braking/throttle tendencies,
pace ranking, and teammate delta per (session, driver) -- built on top of
canonical laps and the vehicle-telemetry per-lap summary.
"""

from __future__ import annotations

import pandas as pd

from f1dataset.processing.vehicle_telemetry import LAP_SUMMARY_COLUMNS

_REQUIRED_LAP_COLUMNS = {
    "session_id", "driver_id", "lap_number", "lap_time_s", "deleted",
    "pit_out_lap", "pit_in_lap", "track_status",
}
_REQUIRED_TELEMETRY_SUMMARY_COLUMNS = set(LAP_SUMMARY_COLUMNS)
_REQUIRED_DRIVER_COLUMNS = {"driver_id", "team_id", "full_name"}

OUTPUT_COLUMNS = [
    "session_id", "driver_id", "full_name", "team_id",
    "clean_lap_count", "median_clean_lap_s", "consistency_std_s", "pace_rank",
    "teammate_delta_s", "avg_brake_events_per_lap", "avg_full_throttle_pct_of_lap",
    "avg_gear_shifts_per_lap", "avg_top_speed_kph",
]


def build_driver_behavior_table(
    laps: pd.DataFrame, telemetry_summary: pd.DataFrame, drivers: pd.DataFrame
) -> pd.DataFrame:
    missing = _REQUIRED_LAP_COLUMNS - set(laps.columns)
    if missing:
        raise ValueError(f"laps is missing required columns: {sorted(missing)}")
    missing = _REQUIRED_TELEMETRY_SUMMARY_COLUMNS - set(telemetry_summary.columns)
    if missing:
        raise ValueError(f"telemetry_summary is missing required columns: {sorted(missing)}")
    missing = _REQUIRED_DRIVER_COLUMNS - set(drivers.columns)
    if missing:
        raise ValueError(f"drivers is missing required columns: {sorted(missing)}")

    if laps.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    # Safety-car/VSC laps are excluded too: they reflect the caution-period
    # pace delta, not driving consistency, and would otherwise dominate the
    # std-dev of a driver who ran green-flag pace all race.
    clean = laps[
        (~laps["deleted"].astype(bool))
        & (~laps["pit_out_lap"].astype(bool))
        & (~laps["pit_in_lap"].astype(bool))
        & (laps["track_status"] == "green")
        & laps["lap_time_s"].notna()
    ]
    lap_stats = clean.groupby(["session_id", "driver_id"]).agg(
        clean_lap_count=("lap_time_s", "count"),
        median_clean_lap_s=("lap_time_s", "median"),
        consistency_std_s=("lap_time_s", "std"),
    ).reset_index()
    lap_stats["consistency_std_s"] = lap_stats["consistency_std_s"].fillna(0.0)

    tel_stats = telemetry_summary.groupby(["session_id", "driver_id"]).agg(
        avg_brake_events_per_lap=("brake_events", "mean"),
        avg_full_throttle_pct_of_lap=("full_throttle_pct_of_lap", "mean"),
        avg_gear_shifts_per_lap=("gear_shifts", "mean"),
        avg_top_speed_kph=("top_speed_kph", "mean"),
    ).reset_index()

    merged = lap_stats.merge(tel_stats, on=["session_id", "driver_id"], how="left")
    merged = merged.merge(drivers[["driver_id", "team_id", "full_name"]], on="driver_id", how="left")
    merged["pace_rank"] = merged.groupby("session_id")["median_clean_lap_s"].rank(method="min").astype(int)
    merged["teammate_delta_s"] = _teammate_delta(merged)

    return merged[OUTPUT_COLUMNS].reset_index(drop=True)


def _teammate_delta(df: pd.DataFrame) -> pd.Series:
    """For each row, lap time minus the mean lap time of same-team rows in
    the same session, excluding itself. Assumes (roughly) two drivers per
    team; with more than two, this compares against the rest of the team's
    average."""
    group_cols = ["session_id", "team_id"]
    team_sum = df.groupby(group_cols)["median_clean_lap_s"].transform("sum")
    team_count = df.groupby(group_cols)["median_clean_lap_s"].transform("count")
    others_mean = (team_sum - df["median_clean_lap_s"]) / (team_count - 1).where(team_count > 1)
    return df["median_clean_lap_s"] - others_mean
