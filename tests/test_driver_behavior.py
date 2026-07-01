import pandas as pd
import pytest

from f1dataset.processing.driver_behavior import build_driver_behavior_table

SESSION = "2024_01_R"


def _laps() -> pd.DataFrame:
    rows = []
    # driver A (team X): consistent, fast
    for lap, t in enumerate([90.0, 90.2, 89.8], start=1):
        rows.append({"session_id": SESSION, "driver_id": "A", "lap_number": lap, "lap_time_s": t, "deleted": False, "pit_out_lap": False, "pit_in_lap": False, "track_status": "green"})
    # driver B (team X): slower teammate
    for lap, t in enumerate([92.0, 92.5, 91.5], start=1):
        rows.append({"session_id": SESSION, "driver_id": "B", "lap_number": lap, "lap_time_s": t, "deleted": False, "pit_out_lap": False, "pit_in_lap": False, "track_status": "green"})
    # driver C (team Y): mid pace, one deleted lap excluded
    for lap, t in enumerate([91.0, 91.0, 200.0], start=1):
        rows.append({"session_id": SESSION, "driver_id": "C", "lap_number": lap, "lap_time_s": t, "deleted": lap == 3, "pit_out_lap": False, "pit_in_lap": False, "track_status": "green"})
    return pd.DataFrame(rows)


def _telemetry_summary() -> pd.DataFrame:
    rows = []
    for driver in ["A", "B", "C"]:
        for lap in [1, 2, 3]:
            rows.append(
                {
                    "session_id": SESSION, "driver_id": driver, "lap_number": lap,
                    "top_speed_kph": 300, "avg_speed_kph": 200, "avg_throttle_pct": 70,
                    "full_throttle_pct_of_lap": 60, "brake_events": 8, "max_rpm": 12000,
                    "gear_shifts": 20, "drs_activations": 2, "drs_usage_pct_of_lap": 15,
                }
            )
    return pd.DataFrame(rows)


def _drivers() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"driver_id": "A", "team_id": "X", "full_name": "Driver A"},
            {"driver_id": "B", "team_id": "X", "full_name": "Driver B"},
            {"driver_id": "C", "team_id": "Y", "full_name": "Driver C"},
        ]
    )


def test_pace_rank_orders_fastest_first():
    out = build_driver_behavior_table(_laps(), _telemetry_summary(), _drivers())
    ranked = out.set_index("driver_id")["pace_rank"]
    assert ranked["A"] < ranked["C"] < ranked["B"]


def test_teammate_delta_is_symmetric_within_team():
    out = build_driver_behavior_table(_laps(), _telemetry_summary(), _drivers()).set_index("driver_id")
    assert out.loc["A", "teammate_delta_s"] == pytest.approx(-(out.loc["B", "teammate_delta_s"]))
    assert out.loc["A", "teammate_delta_s"] < 0  # A is faster than teammate B


def test_driver_without_teammate_has_null_delta():
    out = build_driver_behavior_table(_laps(), _telemetry_summary(), _drivers()).set_index("driver_id")
    assert pd.isna(out.loc["C", "teammate_delta_s"])


def test_excludes_deleted_laps_from_consistency():
    out = build_driver_behavior_table(_laps(), _telemetry_summary(), _drivers()).set_index("driver_id")
    assert out.loc["C", "clean_lap_count"] == 2


def test_excludes_safety_car_laps_from_consistency():
    laps = _laps()
    laps.loc[(laps["driver_id"] == "A") & (laps["lap_number"] == 1), ["lap_time_s", "track_status"]] = [200.0, "SC"]
    out = build_driver_behavior_table(laps, _telemetry_summary(), _drivers()).set_index("driver_id")
    assert out.loc["A", "clean_lap_count"] == 2
    assert out.loc["A", "consistency_std_s"] < 1.0
