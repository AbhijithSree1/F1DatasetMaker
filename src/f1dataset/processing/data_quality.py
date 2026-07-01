"""Data quality checks: schema conformance against `schemas/tables.py` plus
a handful of sanity-range checks, so pipeline consumers (and the dashboard)
can see at a glance whether a build of the dataset is trustworthy.
"""

from __future__ import annotations

from typing import Callable

import pandas as pd

from f1dataset.schemas.tables import ALL_TABLES, TableSchema

SCHEMA_REPORT_COLUMNS = ["table", "row_count", "missing_columns", "extra_columns", "null_rates", "passed"]
SANITY_CHECK_COLUMNS = ["check", "table", "passed", "detail"]


def validate_table(df: pd.DataFrame, schema: TableSchema) -> dict:
    expected = set(schema.columns)
    actual = set(df.columns)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    present = expected & actual
    null_rates = {col: float(df[col].isna().mean()) for col in present} if not df.empty else {col: None for col in present}
    return {
        "table": schema.name,
        "row_count": int(len(df)),
        "missing_columns": missing,
        "extra_columns": extra,
        "null_rates": null_rates,
        "passed": len(missing) == 0,
    }


def build_schema_report(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Checks each named table against its canonical schema in `schemas/tables.py`."""
    schema_by_name = {t.name: t for t in ALL_TABLES}
    rows = []
    for name, df in tables.items():
        schema = schema_by_name.get(name)
        if schema is None:
            rows.append(
                {"table": name, "row_count": len(df), "missing_columns": [], "extra_columns": list(df.columns),
                 "null_rates": {}, "passed": None}
            )
            continue
        rows.append(validate_table(df, schema))
    return pd.DataFrame(rows, columns=SCHEMA_REPORT_COLUMNS)


def _check_positive(df: pd.DataFrame, column: str) -> tuple[bool, str]:
    bad = int((df[column] <= 0).sum())
    return bad == 0, f"{bad} row(s) with non-positive {column}"


def _check_range(df: pd.DataFrame, column: str, low: float, high: float) -> tuple[bool, str]:
    bad = int(((df[column] < low) | (df[column] > high)).sum())
    return bad == 0, f"{bad} row(s) with {column} outside [{low}, {high}]"


def _check_sector_sum(df: pd.DataFrame, tolerance_s: float = 1.0) -> tuple[bool, str]:
    sector_sum = df["sector1_s"] + df["sector2_s"] + df["sector3_s"]
    bad = int((sector_sum - df["lap_time_s"]).abs().gt(tolerance_s).sum())
    return bad == 0, f"{bad} lap(s) where sectors don't sum to lap_time_s within {tolerance_s}s"


def _check_unique_positions(df: pd.DataFrame) -> tuple[bool, str]:
    dupes = int(df.groupby("session_id")["position"].apply(lambda s: s.duplicated().sum()).sum())
    return dupes == 0, f"{dupes} duplicate finishing position(s) within a session"


_CHECKS: list[tuple[str, str, Callable[[pd.DataFrame], tuple[bool, str]]]] = [
    ("lap_time_positive", "laps", lambda df: _check_positive(df, "lap_time_s")),
    ("sectors_sum_to_lap_time", "laps", _check_sector_sum),
    ("speed_in_range", "telemetry", lambda df: _check_range(df, "speed_kph", 0, 400)),
    ("throttle_in_range", "telemetry", lambda df: _check_range(df, "throttle_pct", 0, 100)),
    ("air_temp_in_range", "weather", lambda df: _check_range(df, "air_temp_c", -10, 60)),
    ("unique_finishing_positions", "results", _check_unique_positions),
]


def run_sanity_checks(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, table_key, check_fn in _CHECKS:
        df = tables.get(table_key)
        if df is None or df.empty:
            rows.append({"check": name, "table": table_key, "passed": None, "detail": "table missing or empty"})
            continue
        passed, detail = check_fn(df)
        rows.append({"check": name, "table": table_key, "passed": passed, "detail": detail})
    return pd.DataFrame(rows, columns=SANITY_CHECK_COLUMNS)


def build_data_quality_report(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "schema_report": build_schema_report(tables),
        "sanity_checks": run_sanity_checks(tables),
    }
