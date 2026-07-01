import pandas as pd
import pytest

from f1dataset.processing.lap_strategy import build_lap_strategy_table

SESSION = "2024_01_R"


def _laps() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "session_id": SESSION, "driver_id": "A", "lap_number": 1, "lap_time_s": 90.0,
                "sector1_s": 30, "sector2_s": 30, "sector3_s": 30, "compound": "SOFT",
                "tyre_age_laps": 0, "stint_number": 1, "track_status": "green",
                "pit_out_lap": False, "pit_in_lap": False,
            },
            {
                "session_id": SESSION, "driver_id": "A", "lap_number": 2, "lap_time_s": 110.0,
                "sector1_s": 35, "sector2_s": 35, "sector3_s": 40, "compound": "SOFT",
                "tyre_age_laps": 1, "stint_number": 1, "track_status": "green",
                "pit_out_lap": False, "pit_in_lap": True,
            },
        ]
    )


def _weather() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"session_id": SESSION, "time_s": 0, "air_temp_c": 24.0, "track_temp_c": 34.0, "humidity_pct": 45, "rainfall": False},
            {"session_id": SESSION, "time_s": 200, "air_temp_c": 26.0, "track_temp_c": 36.0, "humidity_pct": 46, "rainfall": False},
        ]
    )


def _pit_stops() -> pd.DataFrame:
    return pd.DataFrame([{"session_id": SESSION, "driver_id": "A", "lap_number": 2, "pit_duration_s": 23.5}])


def test_joins_nearest_weather_by_lap_start_time():
    out = build_lap_strategy_table(_laps(), _weather(), _pit_stops())
    lap1 = out[out["lap_number"] == 1].iloc[0]
    lap2 = out[out["lap_number"] == 2].iloc[0]
    assert lap1["lap_start_time_s"] == 0.0
    assert lap1["air_temp_c"] == 24.0  # closer to weather sample at t=0
    assert lap2["lap_start_time_s"] == 90.0
    assert lap2["air_temp_c"] == 24.0  # still closer to t=0 than t=200


def test_pit_duration_only_on_pit_lap():
    out = build_lap_strategy_table(_laps(), _weather(), _pit_stops())
    assert pd.isna(out[out["lap_number"] == 1]["pit_duration_s"].item())
    assert out[out["lap_number"] == 2]["pit_duration_s"].item() == pytest.approx(23.5)


def test_missing_columns_raises():
    bad_laps = _laps().drop(columns=["compound"])
    with pytest.raises(ValueError, match="missing required columns"):
        build_lap_strategy_table(bad_laps, _weather(), _pit_stops())
