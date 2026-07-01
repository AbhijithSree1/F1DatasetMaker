"""Reference processing module: turns canonical `laps` rows into a tire
degradation feature table (one row per clean racing lap, with lap time
delta relative to that stint's best lap).

This is the pattern the rest of the processing layer (vehicle telemetry,
driver-behavior, and strategy feature modules) should follow: take a
canonical table as input, return a canonical, documented output table.
"""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
    "session_id",
    "driver_id",
    "stint_number",
    "compound",
    "lap_number",
    "tyre_age_laps",
    "lap_time_s",
    "deleted",
    "pit_out_lap",
    "pit_in_lap",
}


def build_tire_degradation_table(laps: pd.DataFrame) -> pd.DataFrame:
    """Compute per-lap tire degradation features from canonical lap data.

    Filters out deleted laps and in/out laps (which aren't representative of
    green-flag pace), then for every (session, driver, stint) computes the
    stint's best clean lap time and each lap's delta to it.
    """
    missing = REQUIRED_COLUMNS - set(laps.columns)
    if missing:
        raise ValueError(f"laps is missing required columns: {sorted(missing)}")

    clean = laps[
        (~laps["deleted"].astype(bool))
        & (~laps["pit_out_lap"].astype(bool))
        & (~laps["pit_in_lap"].astype(bool))
        & laps["lap_time_s"].notna()
    ].copy()

    group_cols = ["session_id", "driver_id", "stint_number"]
    clean["stint_best_lap_s"] = clean.groupby(group_cols)["lap_time_s"].transform("min")
    clean["delta_to_stint_best_s"] = clean["lap_time_s"] - clean["stint_best_lap_s"]
    clean["stint_lap_index"] = clean.groupby(group_cols).cumcount() + 1

    return clean[
        [
            "session_id",
            "driver_id",
            "stint_number",
            "compound",
            "lap_number",
            "tyre_age_laps",
            "stint_lap_index",
            "lap_time_s",
            "stint_best_lap_s",
            "delta_to_stint_best_s",
        ]
    ].reset_index(drop=True)
