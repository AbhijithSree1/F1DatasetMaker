import pandas as pd
import pytest

from f1dataset.processing.vehicle_telemetry import build_distance_trace, build_vehicle_telemetry_table


def _telemetry(rows: list[dict]) -> pd.DataFrame:
    defaults = {"session_id": "2024_01_R", "driver_id": "2024_1", "lap_number": 1}
    return pd.DataFrame([{**defaults, **row} for row in rows])


def test_lap_summary_computes_top_and_avg_speed():
    tel = _telemetry(
        [
            {"time_s": 0.0, "distance_m": 0, "speed_kph": 100, "throttle_pct": 50, "brake": False, "gear": 3, "rpm": 8000, "drs": 0},
            {"time_s": 0.5, "distance_m": 20, "speed_kph": 200, "throttle_pct": 100, "brake": False, "gear": 5, "rpm": 11000, "drs": 1},
            {"time_s": 1.0, "distance_m": 50, "speed_kph": 150, "throttle_pct": 0, "brake": True, "gear": 4, "rpm": 9000, "drs": 0},
        ]
    )

    out = build_vehicle_telemetry_table(tel)

    assert len(out) == 1
    row = out.iloc[0]
    assert row["top_speed_kph"] == 200
    assert row["avg_speed_kph"] == pytest.approx(150)
    assert row["brake_events"] == 1
    assert row["gear_shifts"] == 2
    assert row["drs_activations"] == 1


def test_missing_columns_raises():
    tel = _telemetry([{"time_s": 0.0, "distance_m": 0, "speed_kph": 100}])
    with pytest.raises(ValueError, match="missing required columns"):
        build_vehicle_telemetry_table(tel)


def test_empty_input_returns_empty_with_columns():
    tel = pd.DataFrame(
        columns=["session_id", "driver_id", "lap_number", "time_s", "distance_m", "speed_kph", "throttle_pct", "brake", "gear", "rpm", "drs"]
    )
    out = build_vehicle_telemetry_table(tel)
    assert out.empty
    assert "top_speed_kph" in out.columns


def test_distance_trace_bins_by_distance():
    tel = _telemetry(
        [
            {"time_s": 0.0, "distance_m": 5, "speed_kph": 100, "throttle_pct": 50, "brake": False, "gear": 3, "rpm": 8000, "drs": 0},
            {"time_s": 0.5, "distance_m": 15, "speed_kph": 120, "throttle_pct": 60, "brake": False, "gear": 3, "rpm": 8500, "drs": 0},
            {"time_s": 1.0, "distance_m": 35, "speed_kph": 200, "throttle_pct": 100, "brake": False, "gear": 5, "rpm": 11000, "drs": 1},
        ]
    )

    out = build_distance_trace(tel, bin_size_m=20.0)

    assert list(out["distance_bin_m"]) == [0.0, 20.0]
    assert out.loc[out["distance_bin_m"] == 0.0, "speed_kph"].item() == pytest.approx(110)
