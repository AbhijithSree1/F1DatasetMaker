import pandas as pd
import pytest

from f1dataset.processing.normalize import (
    build_drivers_table,
    build_sessions_table,
    build_teams_table,
    derive_stints_from_laps,
    make_driver_id,
    make_session_id,
    make_team_id,
    normalize_fastf1_laps,
    normalize_fastf1_results,
    normalize_fastf1_telemetry,
    normalize_fastf1_weather,
    normalize_openf1_pit,
    normalize_openf1_stints,
)


def test_make_session_id_pads_round_number():
    assert make_session_id(2024, 3, "r") == "2024_03_R"


def test_make_team_id_slugifies_name():
    assert make_team_id(2024, "Solstice Racing") == "2024_solstice-racing"


def test_make_driver_id():
    assert make_driver_id(2024, 44) == "2024_44"


def test_build_sessions_table_joins_schedule():
    laps = pd.DataFrame({"Season": [2024, 2024], "RoundNumber": [1, 1], "SessionName": ["R", "R"]})
    schedule = pd.DataFrame({"RoundNumber": [1], "EventName": ["Test GP"], "Location": ["Testville"], "Country": ["Testland"]})

    out = build_sessions_table(laps, schedule)

    assert len(out) == 1
    row = out.iloc[0]
    assert row["session_id"] == "2024_01_R"
    assert row["event_name"] == "Test GP"
    assert row["session_type"] == "race"
    assert row["circuit"] == "Testville"


def test_build_drivers_table_dedupes_by_number():
    results = pd.DataFrame(
        [
            {"Season": 2024, "DriverNumber": "44", "Abbreviation": "HAM", "FullName": "Test Driver", "TeamName": "Test Team"},
            {"Season": 2024, "DriverNumber": "44", "Abbreviation": "HAM", "FullName": "Test Driver", "TeamName": "Test Team"},
        ]
    )
    out = build_drivers_table(results)
    assert len(out) == 1
    assert out.iloc[0]["driver_id"] == "2024_44"
    assert out.iloc[0]["team_id"] == "2024_test-team"


def test_build_teams_table_prefers_provided_color():
    results = pd.DataFrame([{"Season": 2024, "TeamName": "Test Team", "TeamColor": "FF0000"}])
    out = build_teams_table(results)
    assert out.iloc[0]["color"] == "#FF0000"


def test_build_teams_table_falls_back_to_hash_color():
    results = pd.DataFrame([{"Season": 2024, "TeamName": "Test Team"}])
    out = build_teams_table(results)
    assert out.iloc[0]["color"].startswith("#") and len(out.iloc[0]["color"]) == 7


def test_normalize_fastf1_laps():
    raw = pd.DataFrame(
        [
            {
                "Season": 2024, "RoundNumber": 1, "SessionName": "R", "DriverNumber": "44",
                "LapNumber": 5, "LapTime": pd.Timedelta(seconds=91.234),
                "Sector1Time": pd.Timedelta(seconds=30), "Sector2Time": pd.Timedelta(seconds=30),
                "Sector3Time": pd.Timedelta(seconds=31.234), "Compound": "MEDIUM", "TyreLife": 8,
                "Stint": 2, "IsPersonalBest": False, "TrackStatus": "1", "Deleted": False,
                "PitOutTime": pd.NaT, "PitInTime": pd.NaT,
            }
        ]
    )
    out = normalize_fastf1_laps(raw)
    row = out.iloc[0]
    assert row["session_id"] == "2024_01_R"
    assert row["driver_id"] == "2024_44"
    assert row["lap_time_s"] == pytest.approx(91.234)
    assert row["track_status"] == "green"
    assert bool(row["pit_out_lap"]) is False and bool(row["pit_in_lap"]) is False


def test_normalize_fastf1_laps_maps_safety_car_status():
    raw = pd.DataFrame(
        [
            {
                "Season": 2024, "RoundNumber": 1, "SessionName": "R", "DriverNumber": "1",
                "LapNumber": 1, "LapTime": pd.Timedelta(seconds=100), "Sector1Time": pd.Timedelta(seconds=33),
                "Sector2Time": pd.Timedelta(seconds=33), "Sector3Time": pd.Timedelta(seconds=34),
                "Compound": "HARD", "TyreLife": 1, "Stint": 1, "IsPersonalBest": False,
                "TrackStatus": "4", "Deleted": False, "PitOutTime": pd.Timedelta(seconds=0), "PitInTime": pd.NaT,
            }
        ]
    )
    out = normalize_fastf1_laps(raw)
    assert out.iloc[0]["track_status"] == "SC"
    assert bool(out.iloc[0]["pit_out_lap"]) is True


def test_normalize_fastf1_telemetry_maps_driver_via_abbreviation():
    drivers = pd.DataFrame([{"season": 2024, "driver_id": "2024_44", "abbreviation": "HAM"}])
    raw = pd.DataFrame(
        [
            {
                "Season": 2024, "RoundNumber": 1, "SessionName": "R", "Driver": "HAM", "LapNumber": 1,
                "Time": pd.Timedelta(seconds=1.5), "Distance": 50.0, "Speed": 200.0, "Throttle": 80.0,
                "Brake": False, "nGear": 4, "RPM": 10000, "DRS": 12,
            }
        ]
    )
    out = normalize_fastf1_telemetry(raw, drivers)
    row = out.iloc[0]
    assert row["driver_id"] == "2024_44"
    assert row["time_s"] == pytest.approx(1.5)
    assert row["drs"] == 1


def test_normalize_fastf1_weather():
    raw = pd.DataFrame(
        [
            {
                "Season": 2024, "RoundNumber": 1, "SessionName": "R", "Time": pd.Timedelta(seconds=60),
                "AirTemp": 25.0, "TrackTemp": 35.0, "Humidity": 50.0, "Rainfall": False,
                "WindSpeed": 2.0, "WindDirection": 180.0,
            }
        ]
    )
    out = normalize_fastf1_weather(raw)
    assert out.iloc[0]["session_id"] == "2024_01_R"
    assert out.iloc[0]["time_s"] == 60.0


def test_normalize_fastf1_results():
    raw = pd.DataFrame(
        [
            {
                "Season": 2024, "RoundNumber": 1, "SessionName": "R", "DriverNumber": "1",
                "Position": 1, "GridPosition": 2, "Status": "Finished", "Points": 25.0,
                "Time": pd.Timedelta(seconds=5400),
            }
        ]
    )
    out = normalize_fastf1_results(raw)
    row = out.iloc[0]
    assert row["driver_id"] == "2024_1"
    assert row["grid_position"] == 2
    assert row["total_time_s"] == 5400.0


def test_normalize_openf1_stints():
    raw = pd.DataFrame(
        [{"Season": 2024, "RoundNumber": 1, "SessionName": "R", "driver_number": 1, "stint_number": 1,
          "compound": "SOFT", "tyre_age_at_start": 0, "lap_start": 1, "lap_end": 15}]
    )
    out = normalize_openf1_stints(raw)
    assert out.iloc[0]["driver_id"] == "2024_1"
    assert out.iloc[0]["lap_end"] == 15


def test_normalize_openf1_pit():
    raw = pd.DataFrame(
        [{"Season": 2024, "RoundNumber": 1, "SessionName": "R", "driver_number": 1, "lap_number": 16, "pit_duration": 23.4}]
    )
    out = normalize_openf1_pit(raw)
    assert out.iloc[0]["pit_duration_s"] == pytest.approx(23.4)


def test_derive_stints_from_laps():
    laps = pd.DataFrame(
        [
            {"session_id": "s1", "driver_id": "d1", "stint_number": 1, "compound": "SOFT", "tyre_age_laps": 0, "lap_number": 1},
            {"session_id": "s1", "driver_id": "d1", "stint_number": 1, "compound": "SOFT", "tyre_age_laps": 1, "lap_number": 2},
            {"session_id": "s1", "driver_id": "d1", "stint_number": 2, "compound": "HARD", "tyre_age_laps": 0, "lap_number": 3},
        ]
    )
    out = derive_stints_from_laps(laps)
    assert len(out) == 2
    stint1 = out[out["stint_number"] == 1].iloc[0]
    assert stint1["lap_start"] == 1 and stint1["lap_end"] == 2
