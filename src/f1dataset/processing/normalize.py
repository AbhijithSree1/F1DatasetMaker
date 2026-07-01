"""Canonical id helpers shared across ingestion sources.

OpenF1 and FastF1 identify sessions/drivers/teams differently (numeric
session_key vs. year+event+session-name, driver_number vs. three-letter
abbreviation, etc). Everything downstream joins on the ids built here so a
row's provenance (which API it came from) doesn't leak into the schema.
"""

from __future__ import annotations

import hashlib
import re

import pandas as pd

_SESSION_TYPES = {
    "FP1": "practice",
    "FP2": "practice",
    "FP3": "practice",
    "Q": "qualifying",
    "SPRINT": "sprint",
    "SPRINT SHOOTOUT": "sprint",
    "R": "race",
}


def make_session_id(season: int, round_number: int, session_name: str) -> str:
    return f"{season}_{round_number:02d}_{session_name.upper()}"


def make_driver_id(season: int, driver_number: int) -> str:
    return f"{season}_{driver_number}"


def make_team_id(season: int, team_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", team_name.lower()).strip("-")
    return f"{season}_{slug}"


def session_type(session_name: str) -> str:
    return _SESSION_TYPES.get(session_name.upper(), "other")


def build_sessions_table(fastf1_laps: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    """Canonical `sessions` rows from raw FastF1 laps (which carry Season/
    RoundNumber/SessionName, see `ingestion.fastf1_client.extract_laps`)
    joined with the event schedule for circuit/country metadata."""
    columns = [
        "session_id", "season", "round_number", "event_name", "session_name",
        "session_type", "date_start_utc", "date_end_utc", "circuit", "country",
    ]
    if fastf1_laps.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    keys = fastf1_laps[["Season", "RoundNumber", "SessionName"]].drop_duplicates()
    for _, key in keys.iterrows():
        season, round_number, session_name = int(key["Season"]), int(key["RoundNumber"]), key["SessionName"]
        event = schedule[schedule["RoundNumber"] == round_number] if not schedule.empty else pd.DataFrame()
        rows.append(
            {
                "session_id": make_session_id(season, round_number, session_name),
                "season": season,
                "round_number": round_number,
                "event_name": event["EventName"].iloc[0] if not event.empty else None,
                "session_name": session_name,
                "session_type": session_type(session_name),
                "date_start_utc": None,
                "date_end_utc": None,
                "circuit": event["Location"].iloc[0] if not event.empty else None,
                "country": event["Country"].iloc[0] if not event.empty else None,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_drivers_table(fastf1_results: pd.DataFrame) -> pd.DataFrame:
    """Canonical `drivers` rows from raw FastF1 results (which carry
    Season/DriverNumber/Abbreviation/FullName/TeamName, see
    `ingestion.fastf1_client.extract_results`)."""
    columns = ["season", "driver_id", "driver_number", "abbreviation", "full_name", "team_id", "team_name"]
    if fastf1_results.empty:
        return pd.DataFrame(columns=columns)

    dedup = fastf1_results.drop_duplicates(subset=["Season", "DriverNumber"])
    rows = []
    for _, r in dedup.iterrows():
        season, driver_number = int(r["Season"]), int(r["DriverNumber"])
        team_name = r.get("TeamName", "unknown")
        rows.append(
            {
                "season": season,
                "driver_id": make_driver_id(season, driver_number),
                "driver_number": driver_number,
                "abbreviation": r.get("Abbreviation"),
                "full_name": r.get("FullName", r.get("BroadcastName")),
                "team_id": make_team_id(season, team_name),
                "team_name": team_name,
            }
        )
    return pd.DataFrame(rows, columns=columns).drop_duplicates(subset=["driver_id"]).reset_index(drop=True)


# FastF1's TrackStatus is a string of status-code digits (concatenated if the
# status changed mid-lap, e.g. "12"); we key off the first one.
_TRACK_STATUS_CODES = {"1": "green", "2": "yellow", "4": "SC", "5": "red", "6": "VSC", "7": "green"}


def _map_track_status(code) -> str:
    text = str(code) if pd.notna(code) else ""
    return _TRACK_STATUS_CODES.get(text[:1], "unknown")


def _seconds(series: pd.Series) -> pd.Series:
    return series.dt.total_seconds() if hasattr(series, "dt") else series


def normalize_fastf1_laps(raw_laps: pd.DataFrame) -> pd.DataFrame:
    """Canonical `laps` rows from raw FastF1 laps
    (`ingestion.fastf1_client.extract_laps` output)."""
    columns = [
        "session_id", "driver_id", "lap_number", "lap_time_s", "sector1_s", "sector2_s",
        "sector3_s", "compound", "tyre_age_laps", "stint_number", "is_personal_best",
        "track_status", "deleted", "pit_out_lap", "pit_in_lap",
    ]
    if raw_laps.empty:
        return pd.DataFrame(columns=columns)

    df = raw_laps.copy()
    driver_number = df["DriverNumber"].astype(int)
    out = pd.DataFrame(
        {
            "session_id": [
                make_session_id(int(s), int(r), sn)
                for s, r, sn in zip(df["Season"], df["RoundNumber"], df["SessionName"])
            ],
            "driver_id": [make_driver_id(int(s), n) for s, n in zip(df["Season"], driver_number)],
            "lap_number": df["LapNumber"].astype(int),
            "lap_time_s": _seconds(df["LapTime"]),
            "sector1_s": _seconds(df["Sector1Time"]),
            "sector2_s": _seconds(df["Sector2Time"]),
            "sector3_s": _seconds(df["Sector3Time"]),
            "compound": df["Compound"],
            "tyre_age_laps": df["TyreLife"].fillna(0).astype(int),
            "stint_number": df["Stint"].fillna(1).astype(int),
            "is_personal_best": df["IsPersonalBest"].fillna(False),
            "track_status": df["TrackStatus"].map(_map_track_status),
            "deleted": df["Deleted"].fillna(False),
            "pit_out_lap": df["PitOutTime"].notna(),
            "pit_in_lap": df["PitInTime"].notna(),
        }
    )
    return out[columns]


def build_teams_table(fastf1_results: pd.DataFrame) -> pd.DataFrame:
    """Canonical `teams` rows from raw FastF1 results (TeamName + optional
    TeamColor). Falls back to a deterministic hash-based color if FastF1
    doesn't provide one."""
    columns = ["team_id", "team_name", "color"]
    if fastf1_results.empty or "TeamName" not in fastf1_results.columns:
        return pd.DataFrame(columns=columns)

    dedup = fastf1_results.drop_duplicates(subset=["Season", "TeamName"])
    rows = []
    for _, r in dedup.iterrows():
        season, team_name = int(r["Season"]), r["TeamName"]
        raw_color = r.get("TeamColor")
        if isinstance(raw_color, str) and raw_color:
            color = raw_color if raw_color.startswith("#") else f"#{raw_color}"
        else:
            color = f"#{hashlib.md5(team_name.encode()).hexdigest()[:6]}"
        rows.append({"team_id": make_team_id(season, team_name), "team_name": team_name, "color": color})
    return pd.DataFrame(rows, columns=columns).drop_duplicates(subset=["team_id"]).reset_index(drop=True)


def derive_stints_from_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Fallback `stints` table built from the laps table's own
    compound/stint_number columns, for seasons where OpenF1 stint data
    isn't available (pre-2023)."""
    columns = ["session_id", "driver_id", "stint_number", "compound", "tyre_age_at_start_laps", "lap_start", "lap_end"]
    if laps.empty:
        return pd.DataFrame(columns=columns)

    grouped = laps.groupby(["session_id", "driver_id", "stint_number"]).agg(
        compound=("compound", "first"),
        tyre_age_at_start_laps=("tyre_age_laps", "min"),
        lap_start=("lap_number", "min"),
        lap_end=("lap_number", "max"),
    ).reset_index()
    return grouped[columns]


def normalize_fastf1_telemetry(raw_telemetry: pd.DataFrame, drivers: pd.DataFrame) -> pd.DataFrame:
    """Canonical `telemetry` rows from raw FastF1 telemetry
    (`ingestion.fastf1_client.extract_telemetry` output). `drivers` must be
    the canonical drivers table (for season+abbreviation -> driver_id)."""
    columns = [
        "session_id", "driver_id", "lap_number", "time_s", "distance_m",
        "speed_kph", "throttle_pct", "brake", "gear", "rpm", "drs",
    ]
    if raw_telemetry.empty:
        return pd.DataFrame(columns=columns)

    abbrev_to_id = {(row.season, row.abbreviation): row.driver_id for row in drivers.itertuples()}
    df = raw_telemetry.copy()
    out = pd.DataFrame(
        {
            "session_id": [
                make_session_id(int(s), int(r), sn)
                for s, r, sn in zip(df["Season"], df["RoundNumber"], df["SessionName"])
            ],
            "driver_id": [abbrev_to_id.get((int(s), a)) for s, a in zip(df["Season"], df["Driver"])],
            "lap_number": df["LapNumber"].astype(int),
            "time_s": _seconds(df["Time"]),
            "distance_m": df["Distance"],
            "speed_kph": df["Speed"],
            "throttle_pct": df["Throttle"],
            "brake": df["Brake"].astype(bool),
            "gear": df["nGear"].astype(int),
            "rpm": df["RPM"],
            "drs": df["DRS"].isin([10, 12, 14]).astype(int),
        }
    )
    return out[columns]


def normalize_fastf1_weather(raw_weather: pd.DataFrame) -> pd.DataFrame:
    """Canonical `weather` rows from raw FastF1 weather
    (`ingestion.fastf1_client.extract_weather` output)."""
    columns = [
        "session_id", "time_s", "air_temp_c", "track_temp_c",
        "humidity_pct", "rainfall", "wind_speed_ms", "wind_direction_deg",
    ]
    if raw_weather.empty:
        return pd.DataFrame(columns=columns)

    df = raw_weather.copy()
    out = pd.DataFrame(
        {
            "session_id": [
                make_session_id(int(s), int(r), sn)
                for s, r, sn in zip(df["Season"], df["RoundNumber"], df["SessionName"])
            ],
            "time_s": _seconds(df["Time"]),
            "air_temp_c": df["AirTemp"],
            "track_temp_c": df["TrackTemp"],
            "humidity_pct": df["Humidity"],
            "rainfall": df["Rainfall"].fillna(False),
            "wind_speed_ms": df["WindSpeed"],
            "wind_direction_deg": df["WindDirection"],
        }
    )
    return out[columns]


def normalize_fastf1_results(raw_results: pd.DataFrame) -> pd.DataFrame:
    """Canonical `results` rows from raw FastF1 results
    (`ingestion.fastf1_client.extract_results` output)."""
    columns = ["session_id", "driver_id", "position", "grid_position", "status", "points", "total_time_s"]
    if raw_results.empty:
        return pd.DataFrame(columns=columns)

    df = raw_results.copy()
    driver_number = df["DriverNumber"].astype(int)
    grid = df["GridPosition"] if "GridPosition" in df.columns else df["Position"]
    out = pd.DataFrame(
        {
            "session_id": [
                make_session_id(int(s), int(r), sn)
                for s, r, sn in zip(df["Season"], df["RoundNumber"], df["SessionName"])
            ],
            "driver_id": [make_driver_id(int(s), n) for s, n in zip(df["Season"], driver_number)],
            "position": df["Position"].fillna(0).astype(int),
            "grid_position": grid.fillna(0).astype(int),
            "status": df.get("Status", pd.Series("Unknown", index=df.index)).fillna("Unknown"),
            "points": df.get("Points", pd.Series(0.0, index=df.index)).fillna(0.0).astype(float),
            "total_time_s": _seconds(df["Time"]) if "Time" in df.columns else None,
        }
    )
    return out[columns]


def normalize_openf1_stints(raw_stints: pd.DataFrame) -> pd.DataFrame:
    """Canonical `stints` rows from raw OpenF1 `/stints` data."""
    columns = ["session_id", "driver_id", "stint_number", "compound", "tyre_age_at_start_laps", "lap_start", "lap_end"]
    if raw_stints.empty:
        return pd.DataFrame(columns=columns)

    df = raw_stints.copy()
    out = pd.DataFrame(
        {
            "session_id": [
                make_session_id(int(s), int(r), sn)
                for s, r, sn in zip(df["Season"], df["RoundNumber"], df["SessionName"])
            ],
            "driver_id": [make_driver_id(int(s), int(n)) for s, n in zip(df["Season"], df["driver_number"])],
            "stint_number": df["stint_number"].astype(int),
            "compound": df["compound"],
            "tyre_age_at_start_laps": df["tyre_age_at_start"].fillna(0).astype(int),
            "lap_start": df["lap_start"].astype(int),
            "lap_end": df["lap_end"].astype(int),
        }
    )
    return out[columns]


def normalize_openf1_pit(raw_pit: pd.DataFrame) -> pd.DataFrame:
    """Canonical `pit_stops` rows from raw OpenF1 `/pit` data."""
    columns = ["session_id", "driver_id", "lap_number", "pit_duration_s"]
    if raw_pit.empty:
        return pd.DataFrame(columns=columns)

    df = raw_pit.copy()
    out = pd.DataFrame(
        {
            "session_id": [
                make_session_id(int(s), int(r), sn)
                for s, r, sn in zip(df["Season"], df["RoundNumber"], df["SessionName"])
            ],
            "driver_id": [make_driver_id(int(s), int(n)) for s, n in zip(df["Season"], df["driver_number"])],
            "lap_number": df["lap_number"].astype(int),
            "pit_duration_s": df["pit_duration"].astype(float),
        }
    )
    return out[columns]
