import pandas as pd
import pytest

from f1dataset.processing.tire_degradation import build_tire_degradation_table


def _laps(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "session_id": "2024_01_R",
        "driver_id": "2024_1",
        "stint_number": 1,
        "compound": "MEDIUM",
        "tyre_age_laps": 0,
        "deleted": False,
        "pit_out_lap": False,
        "pit_in_lap": False,
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def test_computes_delta_to_stint_best():
    laps = _laps(
        [
            {"lap_number": 1, "lap_time_s": 92.0},
            {"lap_number": 2, "lap_time_s": 90.0},
            {"lap_number": 3, "lap_time_s": 91.5},
        ]
    )

    out = build_tire_degradation_table(laps)

    assert list(out["stint_best_lap_s"]) == [90.0, 90.0, 90.0]
    assert out.loc[out["lap_number"] == 2, "delta_to_stint_best_s"].item() == 0.0
    assert out.loc[out["lap_number"] == 1, "delta_to_stint_best_s"].item() == pytest.approx(2.0)
    assert list(out["stint_lap_index"]) == [1, 2, 3]


def test_excludes_deleted_and_pit_laps():
    laps = _laps(
        [
            {"lap_number": 1, "lap_time_s": 90.0, "pit_out_lap": True},
            {"lap_number": 2, "lap_time_s": 200.0, "deleted": True},
            {"lap_number": 3, "lap_time_s": 91.0},
        ]
    )

    out = build_tire_degradation_table(laps)

    assert list(out["lap_number"]) == [3]


def test_separates_stints():
    laps = _laps(
        [
            {"lap_number": 1, "lap_time_s": 90.0, "stint_number": 1},
            {"lap_number": 2, "lap_time_s": 89.0, "stint_number": 1},
            {"lap_number": 3, "lap_time_s": 88.0, "stint_number": 2, "compound": "HARD"},
        ]
    )

    out = build_tire_degradation_table(laps)

    stint1_best = out.loc[out["stint_number"] == 1, "stint_best_lap_s"].unique()
    stint2_best = out.loc[out["stint_number"] == 2, "stint_best_lap_s"].unique()
    assert list(stint1_best) == [89.0]
    assert list(stint2_best) == [88.0]


def test_missing_required_column_raises():
    laps = _laps([{"lap_number": 1, "lap_time_s": 90.0}]).drop(columns=["compound"])

    with pytest.raises(ValueError, match="missing required columns"):
        build_tire_degradation_table(laps)
