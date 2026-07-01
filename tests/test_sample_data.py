import pandas as pd
import pytest

from f1dataset import features
from f1dataset.processing.data_quality import build_data_quality_report
from f1dataset.sample_data import generate_race_weekend


@pytest.fixture(scope="module")
def race_weekend() -> dict[str, pd.DataFrame]:
    return generate_race_weekend(seed=7)


def test_generates_all_expected_tables(race_weekend):
    expected = {"teams", "drivers", "sessions", "laps", "telemetry", "stints", "weather", "pit_stops", "results"}
    assert expected == set(race_weekend.keys())
    for name, df in race_weekend.items():
        assert not df.empty, f"{name} should not be empty"


def test_two_sessions_present(race_weekend):
    session_types = set(race_weekend["sessions"]["session_type"])
    assert session_types == {"qualifying", "race"}


def test_reproducible_with_same_seed():
    a = generate_race_weekend(seed=123)
    b = generate_race_weekend(seed=123)
    pd.testing.assert_frame_equal(a["laps"], b["laps"])


def test_lap_times_are_plausible(race_weekend):
    laps = race_weekend["laps"]
    assert (laps["lap_time_s"] > 0).all()
    assert laps["lap_time_s"].max() < 300  # even SC/pit laps shouldn't blow past this


def test_telemetry_values_in_plausible_ranges(race_weekend):
    tel = race_weekend["telemetry"]
    assert tel["speed_kph"].between(0, 370).all()
    assert tel["throttle_pct"].between(0, 100).all()
    assert tel["gear"].between(1, 8).all()


def test_build_all_features_end_to_end(race_weekend):
    all_tables = features.build_all_features(race_weekend)
    for key in ["telemetry_summary", "driver_behavior", "lap_strategy", "tire_degradation"]:
        assert key in all_tables
        assert not all_tables[key].empty


def test_data_quality_report_passes_on_synthetic_data(race_weekend):
    all_tables = features.build_all_features(race_weekend)
    report = build_data_quality_report(all_tables)
    assert (report["schema_report"]["passed"] != False).all()  # noqa: E712
    assert (report["sanity_checks"]["passed"] != False).all()  # noqa: E712
