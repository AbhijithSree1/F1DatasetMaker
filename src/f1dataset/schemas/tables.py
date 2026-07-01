"""Canonical column definitions for the processed dataset tables.

This is the single source of truth for what a "clean" table looks like once
OpenF1 and FastF1 data have been normalized into it. Processing code should
select/rename into these column sets rather than passing raw source columns
downstream, so consumers get a stable schema regardless of which upstream
source(s) produced a given row.

See PLAN.md / README.md for the full data dictionary with descriptions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: dict[str, str]  # column_name -> human-readable description


SESSIONS = TableSchema(
    name="sessions",
    columns={
        "session_id": "Canonical id: '{season}_{round_number}_{session_name}'",
        "season": "Championship year",
        "round_number": "Round number within the season",
        "event_name": "Grand Prix name, e.g. 'Bahrain Grand Prix'",
        "session_name": "FP1 / FP2 / FP3 / Q / Sprint / R",
        "session_type": "practice / qualifying / sprint / race",
        "date_start_utc": "Session start timestamp (UTC)",
        "date_end_utc": "Session end timestamp (UTC)",
        "circuit": "Circuit short name",
        "country": "Host country",
    },
)

DRIVERS = TableSchema(
    name="drivers",
    columns={
        "season": "Championship year",
        "driver_id": "Canonical id: '{season}_{driver_number}'",
        "driver_number": "Car number",
        "abbreviation": "Three-letter driver code, e.g. 'VER'",
        "full_name": "Driver full name",
        "team_id": "Canonical id: '{season}_{team_slug}'",
        "team_name": "Constructor name",
    },
)

LAPS = TableSchema(
    name="laps",
    columns={
        "session_id": "FK -> sessions.session_id",
        "driver_id": "FK -> drivers.driver_id",
        "lap_number": "Lap number within the session",
        "lap_time_s": "Total lap time in seconds",
        "sector1_s": "Sector 1 time in seconds",
        "sector2_s": "Sector 2 time in seconds",
        "sector3_s": "Sector 3 time in seconds",
        "compound": "Tire compound: SOFT / MEDIUM / HARD / INTERMEDIATE / WET",
        "tyre_age_laps": "Laps completed on the current tire set at the start of this lap",
        "stint_number": "Stint index within the session (1-based)",
        "is_personal_best": "Whether this was the driver's fastest lap so far in the session",
        "track_status": "Track status flag during the lap (green / yellow / SC / VSC / red)",
        "deleted": "Whether the lap time was deleted by race control (e.g. track limits)",
        "pit_out_lap": "True if this lap started with a pit exit",
        "pit_in_lap": "True if this lap ended with a pit entry",
    },
)

TELEMETRY = TableSchema(
    name="telemetry",
    columns={
        "session_id": "FK -> sessions.session_id",
        "driver_id": "FK -> drivers.driver_id",
        "lap_number": "Lap number this telemetry sample belongs to",
        "time_s": "Time elapsed since the start of the lap, in seconds",
        "distance_m": "Distance traveled since the start of the lap, in meters",
        "speed_kph": "Car speed in km/h",
        "throttle_pct": "Throttle pedal position, 0-100",
        "brake": "Brake applied (bool or 0-100 depending on source)",
        "gear": "Selected gear",
        "rpm": "Engine RPM",
        "drs": "DRS status code",
    },
)

STINTS = TableSchema(
    name="stints",
    columns={
        "session_id": "FK -> sessions.session_id",
        "driver_id": "FK -> drivers.driver_id",
        "stint_number": "Stint index within the session (1-based)",
        "compound": "Tire compound used for the stint",
        "tyre_age_at_start_laps": "Tire age (in laps) at the start of the stint",
        "lap_start": "First lap number of the stint",
        "lap_end": "Last lap number of the stint",
    },
)

WEATHER = TableSchema(
    name="weather",
    columns={
        "session_id": "FK -> sessions.session_id",
        "time_s": "Time elapsed since the start of the session, in seconds",
        "air_temp_c": "Air temperature, Celsius",
        "track_temp_c": "Track surface temperature, Celsius",
        "humidity_pct": "Relative humidity, 0-100",
        "rainfall": "Whether it was raining",
        "wind_speed_ms": "Wind speed, m/s",
        "wind_direction_deg": "Wind direction, degrees",
    },
)

PIT_STOPS = TableSchema(
    name="pit_stops",
    columns={
        "session_id": "FK -> sessions.session_id",
        "driver_id": "FK -> drivers.driver_id",
        "lap_number": "Lap number the pit stop occurred on",
        "pit_duration_s": "Time spent stationary in the pit box, seconds",
    },
)

RESULTS = TableSchema(
    name="results",
    columns={
        "session_id": "FK -> sessions.session_id",
        "driver_id": "FK -> drivers.driver_id",
        "position": "Classified finishing position (1 = first)",
        "grid_position": "Starting position (race) or session-relative rank (qualifying)",
        "status": "Finished / Retired / Disqualified / ...",
        "points": "Championship points scored in this session",
        "total_time_s": "Total race time (race) or best lap time (qualifying), seconds",
    },
)

ALL_TABLES = [SESSIONS, DRIVERS, LAPS, TELEMETRY, STINTS, WEATHER, PIT_STOPS, RESULTS]
