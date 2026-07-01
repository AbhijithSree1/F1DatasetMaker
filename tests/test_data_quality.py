import pandas as pd

from f1dataset.processing.data_quality import build_data_quality_report, build_schema_report, run_sanity_checks


def _good_laps() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "session_id": "s1", "driver_id": "d1", "lap_number": 1, "lap_time_s": 90.0,
                "sector1_s": 30.0, "sector2_s": 30.0, "sector3_s": 30.0, "compound": "SOFT",
                "tyre_age_laps": 0, "stint_number": 1, "is_personal_best": True, "track_status": "green",
                "deleted": False, "pit_out_lap": False, "pit_in_lap": False,
            }
        ]
    )


def test_schema_report_flags_missing_columns():
    incomplete = _good_laps().drop(columns=["compound"])
    report = build_schema_report({"laps": incomplete})
    row = report[report["table"] == "laps"].iloc[0]
    assert bool(row["passed"]) is False
    assert "compound" in row["missing_columns"]


def test_schema_report_passes_for_complete_table():
    report = build_schema_report({"laps": _good_laps()})
    row = report[report["table"] == "laps"].iloc[0]
    assert bool(row["passed"]) is True
    assert row["missing_columns"] == []


def test_schema_report_handles_unregistered_table_name():
    report = build_schema_report({"not_a_real_table": pd.DataFrame({"x": [1]})})
    row = report[report["table"] == "not_a_real_table"].iloc[0]
    assert row["passed"] is None


def test_sanity_check_catches_negative_lap_time():
    bad = _good_laps().copy()
    bad.loc[0, "lap_time_s"] = -5.0
    checks = run_sanity_checks({"laps": bad})
    row = checks[checks["check"] == "lap_time_positive"].iloc[0]
    assert bool(row["passed"]) is False


def test_sanity_check_passes_for_good_data():
    checks = run_sanity_checks({"laps": _good_laps()})
    row = checks[checks["check"] == "lap_time_positive"].iloc[0]
    assert bool(row["passed"]) is True


def test_build_data_quality_report_returns_both_sections():
    report = build_data_quality_report({"laps": _good_laps()})
    assert set(report.keys()) == {"schema_report", "sanity_checks"}
