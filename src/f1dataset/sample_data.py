"""Synthetic race-weekend generator.

Outbound network access to OpenF1/FastF1/Ergast is blocked in some
environments (sandboxes, offline dev), which means `pipeline.backfill_season`
can't always run. This module generates a physically-plausible fictional
race weekend -- directly in the *canonical* schema defined in
`schemas/tables.py` (i.e. the shape data is in *after* `processing.normalize`
would have run on real ingested data) -- so that every processing module and
the dashboard have real-shaped data to work with.

Everything here is fictional: track, teams, and drivers are invented so
fabricated results are never attributed to real people or events. Swap this
module out for `pipeline.backfill_season` + `processing.normalize` once you
have real ingested data; every downstream processing function consumes the
same canonical tables either way.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from f1dataset.processing.normalize import make_driver_id, make_session_id, make_team_id

SEASON = 2025
ROUND_NUMBER = 0
EVENT_NAME = "F1DatasetMaker Exhibition Grand Prix"
CIRCUIT = "Sable Point Circuit"
COUNTRY = "Fictionland"
TRACK_LENGTH_M = 5303.0
TOTAL_RACE_LAPS = 55

# (distance_m, target_speed_kph) control points tracing one lap; index 0 and
# the last entry share a speed so the profile loops cleanly at start/finish.
_SPEED_CONTROL_POINTS = [
    (0, 295), (250, 100), (400, 130), (750, 245), (820, 90), (1000, 160),
    (1450, 300), (1600, 95), (1750, 140), (2100, 210), (2200, 190), (2500, 260),
    (2650, 110), (2900, 180), (3200, 320), (3550, 85), (3700, 130), (4000, 230),
    (4300, 210), (4600, 150), (4750, 170), (5000, 250), (5150, 200), (TRACK_LENGTH_M, 295),
]
DRS_ZONES = [(1300.0, 1580.0), (3000.0, 3520.0)]
GEAR_SPEED_THRESHOLDS_KPH = [0, 60, 100, 140, 180, 220, 260, 300, 400]  # -> gears 1..8

TEAMS = [
    # (team_name, pace_factor, color)  pace_factor: multiplicative speed edge, 1.0 = baseline
    ("Solstice Racing", 1.014, "#E10600"),
    ("Vantage Grand Prix", 1.010, "#00A19C"),
    ("Meridian Motorsport", 1.006, "#1E5BC6"),
    ("Obsidian Racing", 1.002, "#7B2FF7"),
    ("Halcyon F1 Team", 0.999, "#FFD23F"),
    ("Ferrous Dynamics", 0.996, "#FF7A00"),
    ("Nimbus Racing", 0.992, "#B5B5C3"),
    ("Cobalt Grand Prix", 0.988, "#0057FF"),
    ("Ember Motorsport", 0.984, "#FF3D68"),
    ("Driftwood Racing", 0.978, "#4CAF50"),
]

_DRIVER_NAMES = [
    "Luca Marchetti", "Kai Reyes", "Anders Solberg", "Rafael Novak",
    "Tomiwa Okafor", "Mikael Lindqvist", "Diego Farrow", "Santiago Ibarra",
    "Jack Whitfield", "Chie Tanaka", "Pieter van Dijk", "Owen Faulkner",
    "Noah Kessler", "Felix Amaro", "Bruno Castellano", "Ilya Petrenko",
    "Marco Steiner", "Yusuf Demir", "Callum Whitaker", "Theo Marchand",
]
_DRIVER_NUMBERS = [1, 4, 5, 22, 11, 7, 14, 28, 9, 31, 16, 40, 6, 77, 10, 34, 20, 45, 3, 55]
_DRIVER_ABBREVIATIONS = [
    "MAR", "REY", "SOL", "NOV", "OKA", "LIN", "FAR", "IBA", "WHI", "TAN",
    "DIJ", "FAU", "KES", "AMA", "CAS", "PET", "STE", "DEM", "WTK", "MCH",
]

TIRE_COMPOUNDS = ("SOFT", "MEDIUM", "HARD")
TIRE_BASE_PACE = {"SOFT": 0.005, "MEDIUM": 0.0, "HARD": -0.003}  # speed fraction vs. MEDIUM
TIRE_DEG_RATE = {"SOFT": 0.0009, "MEDIUM": 0.0005, "HARD": 0.00025}  # speed fraction lost per lap of age
FUEL_EFFECT_PER_LAP = 0.00045  # speed fraction gained per lap as fuel burns off
SC_LAPS = set(range(19, 22))  # safety car period for the demo race
POINTS_TABLE = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]

TELEMETRY_DT_S = 0.5


def generate_race_weekend(seed: int = 42) -> dict[str, pd.DataFrame]:
    """Build one fictional race weekend (Qualifying + Race) with drivers,
    laps, telemetry, stints, weather, pit stops, and results -- all in the
    canonical schema from `schemas/tables.py`."""
    rng = np.random.default_rng(seed)

    teams_df = _build_teams()
    drivers_df = _build_drivers(teams_df)
    quali_session_id = make_session_id(SEASON, ROUND_NUMBER, "Q")
    race_session_id = make_session_id(SEASON, ROUND_NUMBER, "R")
    sessions_df = _build_sessions(quali_session_id, race_session_id)

    distance_grid, v_ref = _reference_speed_profile()

    driver_traits = _assign_driver_traits(drivers_df, teams_df, rng)
    strategies = _assign_strategies(drivers_df, rng)

    quali_laps, quali_telemetry = _simulate_qualifying(
        quali_session_id, drivers_df, driver_traits, distance_grid, v_ref, rng
    )
    race_laps, race_telemetry, stints_df, pit_stops_df = _simulate_race(
        race_session_id, drivers_df, driver_traits, strategies, distance_grid, v_ref, rng
    )

    laps_df = pd.concat([quali_laps, race_laps], ignore_index=True)
    telemetry_df = pd.concat([quali_telemetry, race_telemetry], ignore_index=True)
    weather_df = pd.concat(
        [
            _simulate_weather(quali_session_id, duration_s=20 * 60, rng=rng),
            _simulate_weather(race_session_id, duration_s=int(race_laps["lap_time_s"].sum()), rng=rng),
        ],
        ignore_index=True,
    )
    quali_results = _build_results(quali_session_id, quali_laps, is_race=False)
    grid_map = dict(zip(quali_results["driver_id"], quali_results["position"]))
    results_df = pd.concat(
        [
            quali_results,
            _build_results(race_session_id, race_laps, is_race=True, grid_map=grid_map),
        ],
        ignore_index=True,
    )

    return {
        "teams": teams_df,
        "drivers": drivers_df,
        "sessions": sessions_df,
        "laps": laps_df,
        "telemetry": telemetry_df,
        "stints": stints_df,
        "weather": weather_df,
        "pit_stops": pit_stops_df,
        "results": results_df,
    }


# -- Reference data ----------------------------------------------------------


def _build_teams() -> pd.DataFrame:
    rows = [
        {
            "team_id": make_team_id(SEASON, name),
            "team_name": name,
            "pace_factor": pace,
            "color": color,
        }
        for name, pace, color in TEAMS
    ]
    return pd.DataFrame(rows)


def _build_drivers(teams_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, (full_name, number, abbreviation) in enumerate(
        zip(_DRIVER_NAMES, _DRIVER_NUMBERS, _DRIVER_ABBREVIATIONS)
    ):
        team = teams_df.iloc[i // 2]
        rows.append(
            {
                "season": SEASON,
                "driver_id": make_driver_id(SEASON, number),
                "driver_number": number,
                "abbreviation": abbreviation,
                "full_name": full_name,
                "team_id": team["team_id"],
                "team_name": team["team_name"],
            }
        )
    return pd.DataFrame(rows)


def _build_sessions(quali_session_id: str, race_session_id: str) -> pd.DataFrame:
    start = pd.Timestamp("2025-05-04 13:00:00", tz="UTC")
    return pd.DataFrame(
        [
            {
                "session_id": quali_session_id,
                "season": SEASON,
                "round_number": ROUND_NUMBER,
                "event_name": EVENT_NAME,
                "session_name": "Q",
                "session_type": "qualifying",
                "date_start_utc": start,
                "date_end_utc": start + pd.Timedelta(minutes=18),
                "circuit": CIRCUIT,
                "country": COUNTRY,
            },
            {
                "session_id": race_session_id,
                "season": SEASON,
                "round_number": ROUND_NUMBER,
                "event_name": EVENT_NAME,
                "session_name": "R",
                "session_type": "race",
                "date_start_utc": start + pd.Timedelta(days=1),
                "date_end_utc": start + pd.Timedelta(days=1, hours=1, minutes=30),
                "circuit": CIRCUIT,
                "country": COUNTRY,
            },
        ]
    )


# -- Track model ---------------------------------------------------------------


def _reference_speed_profile(step_m: float = 2.0) -> tuple[np.ndarray, np.ndarray]:
    distance_grid = np.arange(0, TRACK_LENGTH_M, step_m)
    xs, ys = zip(*_SPEED_CONTROL_POINTS)
    raw = np.interp(distance_grid, xs, ys)
    window = 15
    kernel = np.ones(window) / window
    padded = np.pad(raw, window // 2, mode="wrap")
    smoothed = np.convolve(padded, kernel, mode="same")[window // 2 : window // 2 + len(raw)]
    return distance_grid, smoothed


def _is_in_drs_zone(distance_m: np.ndarray) -> np.ndarray:
    mask = np.zeros_like(distance_m, dtype=bool)
    for start, end in DRS_ZONES:
        mask |= (distance_m >= start) & (distance_m <= end)
    return mask


def _simulate_lap_telemetry(
    v_ref_kph: np.ndarray,
    distance_grid: np.ndarray,
    pace_scale: float,
    drs_enabled: bool,
    rng: np.random.Generator,
) -> tuple[float, pd.DataFrame]:
    """Simulate one lap's telemetry trace, returning (lap_time_s, telemetry_df_without_ids)."""
    speed_kph = v_ref_kph * pace_scale + rng.normal(0, 1.5, size=v_ref_kph.shape)
    speed_kph = np.clip(speed_kph, 40, None)
    speed_ms = speed_kph / 3.6

    dt = np.diff(distance_grid) / speed_ms[:-1]
    t_cum = np.concatenate([[0.0], np.cumsum(dt)])
    lap_time_s = float(t_cum[-1])

    t_uniform = np.arange(0, lap_time_s, TELEMETRY_DT_S)
    distance_at_t = np.interp(t_uniform, t_cum, distance_grid)
    speed_at_t = np.interp(t_uniform, t_cum, speed_kph)

    accel = np.gradient(speed_at_t / 3.6, TELEMETRY_DT_S)  # m/s^2
    throttle_pct = np.clip(accel / 4.0 * 100, 0, 100)
    throttle_pct = np.where(accel > 0.2, throttle_pct, np.where(accel < -0.3, 0.0, 15.0))
    brake = accel < -0.3

    thresholds = np.array(GEAR_SPEED_THRESHOLDS_KPH)
    gear = np.clip(np.digitize(speed_at_t, thresholds), 1, 8)
    lower = thresholds[gear - 1]
    upper = thresholds[gear]
    band = np.clip(upper - lower, 1, None)
    rpm = 4500 + np.clip((speed_at_t - lower) / band, 0, 1) * 8000 + rng.normal(0, 100, size=t_uniform.shape)

    in_drs_zone = _is_in_drs_zone(distance_at_t)
    drs = (in_drs_zone & drs_enabled).astype(int)

    telemetry = pd.DataFrame(
        {
            "time_s": t_uniform,
            "distance_m": distance_at_t,
            "speed_kph": speed_at_t,
            "throttle_pct": throttle_pct,
            "brake": brake,
            "gear": gear,
            "rpm": rpm.astype(int),
            "drs": drs,
        }
    )
    return lap_time_s, telemetry


# -- Driver/strategy assignment -------------------------------------------------


def _assign_driver_traits(
    drivers_df: pd.DataFrame, teams_df: pd.DataFrame, rng: np.random.Generator
) -> dict[str, dict]:
    team_pace = dict(zip(teams_df["team_id"], teams_df["pace_factor"]))
    traits = {}
    for _, drv in drivers_df.iterrows():
        traits[drv["driver_id"]] = {
            "team_pace": team_pace[drv["team_id"]],
            "skill": 1.0 + rng.normal(0, 0.003),
            "consistency_std": abs(rng.normal(0.0012, 0.0006)),
            "drs_usage_rate": rng.uniform(0.75, 0.98),
        }
    return traits


def _assign_strategies(drivers_df: pd.DataFrame, rng: np.random.Generator) -> dict[str, dict]:
    one_stop_plans = [("MEDIUM", "HARD"), ("SOFT", "HARD"), ("SOFT", "MEDIUM")]
    two_stop_plans = [("SOFT", "MEDIUM", "HARD"), ("SOFT", "SOFT", "MEDIUM"), ("MEDIUM", "MEDIUM", "HARD")]

    strategies = {}
    for driver_id in drivers_df["driver_id"]:
        if rng.random() < 0.4:
            compounds = one_stop_plans[rng.integers(0, len(one_stop_plans))]
            pit_laps = [int(TOTAL_RACE_LAPS * rng.uniform(0.35, 0.55))]
        else:
            compounds = two_stop_plans[rng.integers(0, len(two_stop_plans))]
            pit_laps = sorted(
                {
                    int(TOTAL_RACE_LAPS * rng.uniform(0.22, 0.35)),
                    int(TOTAL_RACE_LAPS * rng.uniform(0.6, 0.75)),
                }
            )
            if len(pit_laps) < 2:
                pit_laps.append(pit_laps[0] + 10)
        strategies[driver_id] = {"compounds": compounds, "pit_laps": pit_laps}
    return strategies


# -- Session simulation ----------------------------------------------------------


def _lap_pace_scale(compound: str, tyre_age_laps: int, lap_number: int, total_laps: int, track_status: str) -> float:
    tire_deg = TIRE_DEG_RATE[compound] * min(tyre_age_laps, 25)
    compound_base = TIRE_BASE_PACE[compound]
    fuel_effect = FUEL_EFFECT_PER_LAP * (total_laps - lap_number)
    sc_effect = -0.35 if track_status == "SC" else 0.0
    return 1.0 + compound_base - tire_deg + fuel_effect + sc_effect


def _simulate_qualifying(
    session_id: str,
    drivers_df: pd.DataFrame,
    driver_traits: dict[str, dict],
    distance_grid: np.ndarray,
    v_ref: np.ndarray,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lap_rows, telemetry_frames = [], []
    for _, drv in drivers_df.iterrows():
        driver_id = drv["driver_id"]
        traits = driver_traits[driver_id]
        pace_scale = traits["team_pace"] * traits["skill"] * (1 + TIRE_BASE_PACE["SOFT"])
        pace_scale *= 1 + rng.normal(0, traits["consistency_std"] * 0.6)
        drs_enabled = rng.random() < traits["drs_usage_rate"]

        lap_time_s, tel = _simulate_lap_telemetry(v_ref, distance_grid, pace_scale, drs_enabled, rng)
        tel["driver_id"] = driver_id
        tel["session_id"] = session_id
        tel["lap_number"] = 1
        telemetry_frames.append(tel)

        s1 = lap_time_s * 0.28 + rng.normal(0, 0.05)
        s2 = lap_time_s * 0.35 + rng.normal(0, 0.05)
        s3 = lap_time_s - s1 - s2
        lap_rows.append(
            {
                "session_id": session_id,
                "driver_id": driver_id,
                "lap_number": 1,
                "lap_time_s": lap_time_s,
                "sector1_s": s1,
                "sector2_s": s2,
                "sector3_s": s3,
                "compound": "SOFT",
                "tyre_age_laps": 0,
                "stint_number": 1,
                "is_personal_best": True,
                "track_status": "green",
                "deleted": False,
                "pit_out_lap": True,
                "pit_in_lap": True,
            }
        )
    return pd.DataFrame(lap_rows), pd.concat(telemetry_frames, ignore_index=True)


def _simulate_race(
    session_id: str,
    drivers_df: pd.DataFrame,
    driver_traits: dict[str, dict],
    strategies: dict[str, dict],
    distance_grid: np.ndarray,
    v_ref: np.ndarray,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    lap_rows, telemetry_frames, stint_rows, pit_rows = [], [], [], []

    for _, drv in drivers_df.iterrows():
        driver_id = drv["driver_id"]
        traits = driver_traits[driver_id]
        plan = strategies[driver_id]
        compounds, pit_laps = plan["compounds"], plan["pit_laps"]

        stint_bounds = [1] + [p + 1 for p in pit_laps] + [TOTAL_RACE_LAPS + 1]
        stint_of_lap: dict[int, tuple[int, str, int]] = {}
        for stint_idx, compound in enumerate(compounds, start=1):
            lap_start, lap_end = stint_bounds[stint_idx - 1], stint_bounds[stint_idx] - 1
            stint_rows.append(
                {
                    "session_id": session_id,
                    "driver_id": driver_id,
                    "stint_number": stint_idx,
                    "compound": compound,
                    "tyre_age_at_start_laps": 0,
                    "lap_start": lap_start,
                    "lap_end": lap_end,
                }
            )
            for lap_number in range(lap_start, lap_end + 1):
                stint_of_lap[lap_number] = (stint_idx, compound, lap_number - lap_start)

        for pit_lap in pit_laps:
            pit_rows.append(
                {
                    "session_id": session_id,
                    "driver_id": driver_id,
                    "lap_number": pit_lap,
                    "pit_duration_s": float(np.clip(rng.normal(23.5, 1.8), 18, 32)),
                }
            )
        pit_laps_set = set(pit_laps)

        best_lap_time = None
        for lap_number in range(1, TOTAL_RACE_LAPS + 1):
            stint_number, compound, tyre_age = stint_of_lap[lap_number]
            track_status = "SC" if lap_number in SC_LAPS else "green"

            pace_scale = _lap_pace_scale(compound, tyre_age, lap_number, TOTAL_RACE_LAPS, track_status)
            pace_scale *= traits["team_pace"] * traits["skill"]
            pace_scale *= 1 + rng.normal(0, traits["consistency_std"])
            drs_enabled = track_status == "green" and rng.random() < traits["drs_usage_rate"]

            lap_time_s, tel = _simulate_lap_telemetry(v_ref, distance_grid, pace_scale, drs_enabled, rng)
            is_pit_in = lap_number in pit_laps_set
            if is_pit_in:
                pit_duration = next(r["pit_duration_s"] for r in pit_rows if r["driver_id"] == driver_id and r["lap_number"] == lap_number)
                lap_time_s += pit_duration
            is_pit_out = tyre_age == 0 and lap_number > 1

            tel["driver_id"] = driver_id
            tel["session_id"] = session_id
            tel["lap_number"] = lap_number
            telemetry_frames.append(tel)

            best_lap_time = lap_time_s if best_lap_time is None else min(best_lap_time, lap_time_s)
            s1 = lap_time_s * 0.28 + rng.normal(0, 0.05)
            s2 = lap_time_s * 0.35 + rng.normal(0, 0.05)
            s3 = lap_time_s - s1 - s2
            lap_rows.append(
                {
                    "session_id": session_id,
                    "driver_id": driver_id,
                    "lap_number": lap_number,
                    "lap_time_s": lap_time_s,
                    "sector1_s": s1,
                    "sector2_s": s2,
                    "sector3_s": s3,
                    "compound": compound,
                    "tyre_age_laps": tyre_age,
                    "stint_number": stint_number,
                    "is_personal_best": lap_time_s == best_lap_time,
                    "track_status": track_status,
                    "deleted": False,
                    "pit_out_lap": is_pit_out,
                    "pit_in_lap": is_pit_in,
                }
            )

    return (
        pd.DataFrame(lap_rows),
        pd.concat(telemetry_frames, ignore_index=True),
        pd.DataFrame(stint_rows),
        pd.DataFrame(pit_rows),
    )


def _simulate_weather(session_id: str, duration_s: int, rng: np.random.Generator) -> pd.DataFrame:
    times = np.arange(0, max(duration_s, 60), 60)
    air_temp = 24 + np.cumsum(rng.normal(0, 0.15, size=times.shape))
    air_temp = np.clip(air_temp, 19, 30)
    track_temp = np.clip(air_temp * 1.4 + rng.normal(0, 0.5, size=times.shape), 26, 48)
    humidity = np.clip(45 + np.cumsum(rng.normal(0, 0.4, size=times.shape)), 25, 70)
    wind_speed = np.abs(rng.normal(3.0, 1.0, size=times.shape))
    wind_dir = rng.uniform(0, 360, size=times.shape)
    return pd.DataFrame(
        {
            "session_id": session_id,
            "time_s": times,
            "air_temp_c": air_temp,
            "track_temp_c": track_temp,
            "humidity_pct": humidity,
            "rainfall": False,
            "wind_speed_ms": wind_speed,
            "wind_direction_deg": wind_dir,
        }
    )


def _build_results(
    session_id: str, laps: pd.DataFrame, is_race: bool, grid_map: dict[str, int] | None = None
) -> pd.DataFrame:
    if is_race:
        totals = laps.groupby("driver_id")["lap_time_s"].sum().sort_values()
    else:
        totals = laps.groupby("driver_id")["lap_time_s"].min().sort_values()

    rows = []
    for position, (driver_id, total_time) in enumerate(totals.items(), start=1):
        rows.append(
            {
                "session_id": session_id,
                "driver_id": driver_id,
                "position": position,
                "grid_position": grid_map[driver_id] if grid_map else position,
                "status": "Finished",
                "points": POINTS_TABLE[position - 1] if is_race and position <= len(POINTS_TABLE) else 0,
                "total_time_s": float(total_time),
            }
        )
    return pd.DataFrame(rows)
