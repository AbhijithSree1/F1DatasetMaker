"""Exports processed tables as compact JSON for the dashboard (dashboard/public/data/).

The dashboard is a static SPA with no backend: it fetches these JSON files
directly. Full-resolution telemetry never goes to the browser -- only
distance-binned traces for a curated set of laps.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from f1dataset.processing.vehicle_telemetry import build_distance_trace
from f1dataset.sample_data import CIRCUIT, COUNTRY, DRS_ZONES, EVENT_NAME, TRACK_LENGTH_M, _SPEED_CONTROL_POINTS


def _driver_lookup(drivers: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    return drivers.merge(teams[["team_id", "color"]], on="team_id", how="left")


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


def export_dashboard_data(tables: dict[str, pd.DataFrame], quality_report: dict[str, pd.DataFrame], out_dir: Path, synthetic: bool = True) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    driver_info = _driver_lookup(tables["drivers"], tables["teams"])

    _write(out_dir / "meta.json", _build_meta(tables, driver_info, synthetic))
    _write(out_dir / "overview.json", _build_overview(tables, driver_info))
    _write(out_dir / "lap_times.json", _build_lap_times(tables, driver_info))
    _write(out_dir / "strategy.json", _build_strategy(tables, driver_info))
    _write(out_dir / "telemetry.json", _build_telemetry(tables, driver_info))
    _write(out_dir / "driver_behavior.json", _build_driver_behavior(tables, driver_info))
    _write(out_dir / "tire_degradation.json", _build_tire_degradation(tables, driver_info))
    _write(out_dir / "data_quality.json", _build_data_quality(quality_report))


def _write(path: Path, payload) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, allow_nan=False)


def _race_session_id(tables: dict[str, pd.DataFrame]) -> str:
    sessions = tables["sessions"]
    return sessions.loc[sessions["session_type"] == "race", "session_id"].iloc[0]


def _quali_session_id(tables: dict[str, pd.DataFrame]) -> str | None:
    sessions = tables["sessions"]
    quali = sessions.loc[sessions["session_type"] == "qualifying", "session_id"]
    return quali.iloc[0] if not quali.empty else None


def _build_meta(tables: dict[str, pd.DataFrame], driver_info: pd.DataFrame, synthetic: bool) -> dict:
    # For real data, label the header from the actual race session; the
    # synthetic constants only apply to the demo weekend. Track geometry
    # (length/DRS/speed profile) below stays synthetic -- real circuit
    # geometry isn't in the dataset, so it's a placeholder for real runs.
    race = tables["sessions"].set_index("session_id").loc[_race_session_id(tables)]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "synthetic": synthetic,
        "event_name": EVENT_NAME if synthetic else (race.get("event_name") or race.get("circuit")),
        "circuit": CIRCUIT if synthetic else race.get("circuit"),
        "country": COUNTRY if synthetic else race.get("country"),
        "track": {
            "length_m": TRACK_LENGTH_M,
            "drs_zones": [{"start_m": s, "end_m": e} for s, e in DRS_ZONES],
            "speed_profile": [{"distance_m": d, "speed_kph": v} for d, v in _SPEED_CONTROL_POINTS],
        },
        "teams": _records(tables["teams"]),
        "drivers": _records(driver_info),
        "sessions": _records(tables["sessions"]),
    }


def _build_overview(tables: dict[str, pd.DataFrame], driver_info: pd.DataFrame) -> dict:
    race_id = _race_session_id(tables)
    results = tables["results"]
    race_results = results[results["session_id"] == race_id].merge(driver_info, on="driver_id", how="left")
    race_results = race_results.sort_values("position")
    leader_time = race_results["total_time_s"].iloc[0]
    race_results = race_results.assign(gap_to_leader_s=race_results["total_time_s"] - leader_time)

    laps = tables["laps"]
    race_laps = laps[laps["session_id"] == race_id]
    fastest = race_laps.loc[race_laps["lap_time_s"].idxmin()]
    fastest_driver = driver_info.set_index("driver_id").loc[fastest["driver_id"]]

    race_laps_sorted = race_laps.sort_values(["driver_id", "lap_number"])
    # Null lap times (in/out/deleted laps) would make cum_time_s NaN and break
    # the integer position rank below; treat them as 0 for the running clock.
    clock = race_laps_sorted["lap_time_s"].fillna(0.0)
    race_laps_sorted = race_laps_sorted.assign(
        cum_time_s=clock.groupby(race_laps_sorted["driver_id"]).cumsum()
    )
    race_laps_sorted["position"] = race_laps_sorted.groupby("lap_number")["cum_time_s"].rank(method="first").astype(int)
    position_by_lap = race_laps_sorted[["lap_number", "driver_id", "position"]].merge(
        driver_info[["driver_id", "abbreviation", "team_id"]], on="driver_id", how="left"
    )

    return {
        "standings": _records(
            race_results[
                ["position", "driver_id", "full_name", "team_name", "color", "points", "total_time_s", "gap_to_leader_s", "grid_position"]
            ]
        ),
        "fastest_lap": {
            "driver_id": fastest["driver_id"],
            "full_name": fastest_driver["full_name"],
            "team_name": fastest_driver["team_name"],
            "color": fastest_driver["color"],
            "lap_number": int(fastest["lap_number"]),
            "lap_time_s": float(fastest["lap_time_s"]),
        },
        "position_by_lap": _records(position_by_lap),
        "total_laps": int(race_laps["lap_number"].max()),
    }


def _build_lap_times(tables: dict[str, pd.DataFrame], driver_info: pd.DataFrame) -> list[dict]:
    race_id = _race_session_id(tables)
    laps = tables["laps"]
    race_laps = laps[laps["session_id"] == race_id]
    joined = race_laps.merge(driver_info[["driver_id", "full_name", "team_name", "color"]], on="driver_id", how="left")
    cols = [
        "driver_id", "full_name", "team_name", "color", "lap_number", "lap_time_s",
        "compound", "track_status", "pit_in_lap", "pit_out_lap",
    ]
    return _records(joined[cols])


def _build_strategy(tables: dict[str, pd.DataFrame], driver_info: pd.DataFrame) -> dict:
    race_id = _race_session_id(tables)
    stints = tables["stints"]
    stints = stints[stints["session_id"] == race_id].merge(
        driver_info[["driver_id", "full_name", "team_name", "color"]], on="driver_id", how="left"
    )
    pit_stops = tables["pit_stops"]
    pit_stops = pit_stops[pit_stops["session_id"] == race_id].merge(
        driver_info[["driver_id", "full_name"]], on="driver_id", how="left"
    )
    return {"stints": _records(stints), "pit_stops": _records(pit_stops)}


def _build_telemetry(tables: dict[str, pd.DataFrame], driver_info: pd.DataFrame) -> dict:
    race_id = _race_session_id(tables)
    laps = tables["laps"]
    race_laps = laps[laps["session_id"] == race_id]

    fastest_idx = race_laps.groupby("driver_id")["lap_time_s"].idxmin()
    fastest_laps = race_laps.loc[fastest_idx, ["driver_id", "lap_number", "lap_time_s", "compound"]]

    telemetry = tables["telemetry"]
    traces = {}
    for _, row in fastest_laps.iterrows():
        lap_tel = telemetry[
            (telemetry["session_id"] == race_id)
            & (telemetry["driver_id"] == row["driver_id"])
            & (telemetry["lap_number"] == row["lap_number"])
        ]
        binned = build_distance_trace(lap_tel, bin_size_m=20.0)
        traces[row["driver_id"]] = {
            "lap_number": int(row["lap_number"]),
            "lap_time_s": float(row["lap_time_s"]),
            "compound": row["compound"],
            "trace": _records(binned[["distance_bin_m", "speed_kph", "throttle_pct", "brake", "gear", "rpm", "drs"]]),
        }

    return {"session_id": race_id, "fastest_laps_by_driver": traces}


def _build_driver_behavior(tables: dict[str, pd.DataFrame], driver_info: pd.DataFrame) -> list[dict]:
    return _records(tables["driver_behavior"])


def _build_tire_degradation(tables: dict[str, pd.DataFrame], driver_info: pd.DataFrame) -> list[dict]:
    joined = tables["tire_degradation"].merge(
        driver_info[["driver_id", "full_name", "team_name", "color"]], on="driver_id", how="left"
    )
    return _records(joined)


def _build_data_quality(quality_report: dict[str, pd.DataFrame]) -> dict:
    return {name: _records(df) for name, df in quality_report.items()}
