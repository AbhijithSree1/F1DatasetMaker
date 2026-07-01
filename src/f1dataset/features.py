"""Orchestrates the processing layer: takes canonical tables (whether from
real ingestion + normalization, or `sample_data.generate_race_weekend`) and
runs every feature-table builder plus the data quality report.
"""

from __future__ import annotations

import pandas as pd

from f1dataset.processing import data_quality, driver_behavior, lap_strategy, tire_degradation, vehicle_telemetry


def build_all_features(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """`tables` must contain canonical 'laps', 'telemetry', 'drivers',
    'weather', and 'pit_stops'. Returns `tables` plus every derived feature
    table, keyed by name."""
    telemetry_summary = vehicle_telemetry.build_vehicle_telemetry_table(tables["telemetry"])
    driver_behavior_table = driver_behavior.build_driver_behavior_table(
        tables["laps"], telemetry_summary, tables["drivers"]
    )
    lap_strategy_table = lap_strategy.build_lap_strategy_table(
        tables["laps"], tables["weather"], tables["pit_stops"]
    )
    tire_degradation_table = tire_degradation.build_tire_degradation_table(tables["laps"])

    return {
        **tables,
        "telemetry_summary": telemetry_summary,
        "driver_behavior": driver_behavior_table,
        "lap_strategy": lap_strategy_table,
        "tire_degradation": tire_degradation_table,
    }


def build_quality_report(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return data_quality.build_data_quality_report(tables)
