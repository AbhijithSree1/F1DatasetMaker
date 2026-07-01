"""Lap/strategy feature table: one wide row per lap joining the canonical
`laps` table (which already carries tire compound/age/stint/track status)
with the weather sampled closest to when the lap started, and pit-stop
duration where applicable. This is the table to train lap-time or
pit-strategy prediction models on.
"""

from __future__ import annotations

import pandas as pd

_REQUIRED_LAP_COLUMNS = {
    "session_id", "driver_id", "lap_number", "lap_time_s", "sector1_s", "sector2_s",
    "sector3_s", "compound", "tyre_age_laps", "stint_number", "track_status",
    "pit_out_lap", "pit_in_lap",
}
_REQUIRED_WEATHER_COLUMNS = {"session_id", "time_s", "air_temp_c", "track_temp_c", "humidity_pct", "rainfall"}
_REQUIRED_PIT_COLUMNS = {"session_id", "driver_id", "lap_number", "pit_duration_s"}

OUTPUT_COLUMNS = [
    "session_id", "driver_id", "lap_number", "lap_start_time_s", "lap_time_s",
    "sector1_s", "sector2_s", "sector3_s", "compound", "tyre_age_laps",
    "stint_number", "track_status", "pit_out_lap", "pit_in_lap", "pit_duration_s",
    "air_temp_c", "track_temp_c", "humidity_pct", "rainfall",
]


def build_lap_strategy_table(laps: pd.DataFrame, weather: pd.DataFrame, pit_stops: pd.DataFrame) -> pd.DataFrame:
    missing = _REQUIRED_LAP_COLUMNS - set(laps.columns)
    if missing:
        raise ValueError(f"laps is missing required columns: {sorted(missing)}")
    missing = _REQUIRED_WEATHER_COLUMNS - set(weather.columns)
    if missing:
        raise ValueError(f"weather is missing required columns: {sorted(missing)}")
    missing = _REQUIRED_PIT_COLUMNS - set(pit_stops.columns)
    if missing:
        raise ValueError(f"pit_stops is missing required columns: {sorted(missing)}")

    if laps.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = laps.sort_values(["session_id", "driver_id", "lap_number"]).copy()
    # Reconstruct each lap's start time as the running sum of prior lap times.
    # Real laps have null lap_time_s (in/out/deleted laps); treat those as 0
    # duration for the clock so every row gets a non-null key -- merge_asof
    # rejects null keys. The real lap_time_s column (with its NaNs) is untouched.
    clock = df["lap_time_s"].fillna(0.0)
    df["lap_start_time_s"] = (
        clock.groupby([df["session_id"], df["driver_id"]]).cumsum() - clock
    ).astype(float)
    weather = weather.assign(time_s=weather["time_s"].astype(float))

    joined_parts = []
    for session_id, session_laps in df.groupby("session_id"):
        session_weather = weather[weather["session_id"] == session_id].sort_values("time_s")
        if session_weather.empty:
            joined_parts.append(session_laps.assign(**{col: None for col in session_weather.columns if col not in session_laps.columns}))
            continue
        joined_parts.append(
            pd.merge_asof(
                session_laps.sort_values("lap_start_time_s"),
                session_weather.drop(columns=["session_id"]),
                left_on="lap_start_time_s",
                right_on="time_s",
                direction="nearest",
            )
        )
    joined = pd.concat(joined_parts, ignore_index=True)

    joined = joined.merge(
        pit_stops[["session_id", "driver_id", "lap_number", "pit_duration_s"]],
        on=["session_id", "driver_id", "lap_number"],
        how="left",
    )

    return joined[OUTPUT_COLUMNS].sort_values(["session_id", "driver_id", "lap_number"]).reset_index(drop=True)
