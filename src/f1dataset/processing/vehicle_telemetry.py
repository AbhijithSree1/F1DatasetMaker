"""Vehicle/telemetry feature tables: turns canonical `telemetry` samples into
per-lap car-performance summaries and compact distance-binned traces suitable
for plotting or overlaying multiple laps/drivers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_REQUIRED_COLUMNS = {
    "session_id", "driver_id", "lap_number", "time_s", "distance_m",
    "speed_kph", "throttle_pct", "brake", "gear", "rpm", "drs",
}

LAP_SUMMARY_COLUMNS = [
    "session_id", "driver_id", "lap_number", "top_speed_kph", "avg_speed_kph",
    "avg_throttle_pct", "full_throttle_pct_of_lap", "brake_events", "max_rpm",
    "gear_shifts", "drs_activations", "drs_usage_pct_of_lap",
]

TRACE_COLUMNS = [
    "session_id", "driver_id", "lap_number", "distance_bin_m",
    "speed_kph", "throttle_pct", "brake", "gear", "rpm", "drs",
]


def _check_columns(telemetry: pd.DataFrame) -> None:
    missing = _REQUIRED_COLUMNS - set(telemetry.columns)
    if missing:
        raise ValueError(f"telemetry is missing required columns: {sorted(missing)}")


def _lap_features(group: pd.DataFrame) -> pd.Series:
    group = group.sort_values("time_s")
    brake = group["brake"].astype(bool).to_numpy()
    gear = group["gear"].to_numpy()
    drs = group["drs"].to_numpy()

    brake_events = int(np.sum((~brake[:-1]) & brake[1:])) if len(brake) > 1 else 0
    gear_shifts = int(np.sum(np.diff(gear) != 0)) if len(gear) > 1 else 0
    drs_activations = int(np.sum((drs[:-1] == 0) & (drs[1:] == 1))) if len(drs) > 1 else 0

    return pd.Series(
        {
            "top_speed_kph": float(group["speed_kph"].max()),
            "avg_speed_kph": float(group["speed_kph"].mean()),
            "avg_throttle_pct": float(group["throttle_pct"].mean()),
            "full_throttle_pct_of_lap": float((group["throttle_pct"] >= 99).mean() * 100),
            "brake_events": brake_events,
            "max_rpm": int(group["rpm"].max()),
            "gear_shifts": gear_shifts,
            "drs_activations": drs_activations,
            "drs_usage_pct_of_lap": float(group["drs"].mean() * 100),
        }
    )


def build_vehicle_telemetry_table(telemetry: pd.DataFrame) -> pd.DataFrame:
    """One row per (session, driver, lap): top speed, throttle/brake/DRS/gear
    usage summary -- the feature table for vehicle-performance models."""
    _check_columns(telemetry)
    if telemetry.empty:
        return pd.DataFrame(columns=LAP_SUMMARY_COLUMNS)

    out = (
        telemetry.groupby(["session_id", "driver_id", "lap_number"], group_keys=True)
        .apply(_lap_features, include_groups=False)
        .reset_index()
    )
    return out[LAP_SUMMARY_COLUMNS]


def build_distance_trace(telemetry: pd.DataFrame, bin_size_m: float = 20.0) -> pd.DataFrame:
    """Bin telemetry by distance-into-lap for compact overlay comparisons
    (e.g. speed/throttle/brake traces for two drivers on the same lap)."""
    _check_columns(telemetry)
    if telemetry.empty:
        return pd.DataFrame(columns=TRACE_COLUMNS)

    df = telemetry.copy()
    df["distance_bin_m"] = (df["distance_m"] // bin_size_m * bin_size_m).astype(float)
    grouped = (
        df.groupby(["session_id", "driver_id", "lap_number", "distance_bin_m"])
        .agg(
            speed_kph=("speed_kph", "mean"),
            throttle_pct=("throttle_pct", "mean"),
            brake=("brake", "mean"),
            gear=("gear", "median"),
            rpm=("rpm", "mean"),
            drs=("drs", "max"),
        )
        .reset_index()
    )
    return grouped.sort_values(["session_id", "driver_id", "lap_number", "distance_bin_m"]).reset_index(drop=True)
