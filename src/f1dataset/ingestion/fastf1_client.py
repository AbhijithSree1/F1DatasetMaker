"""Wrapper around the FastF1 library (https://docs.fastf1.dev).

FastF1 pulls official F1 timing data and gives us season coverage back to
2018 (plus lap-by-lap car telemetry, which OpenF1 does not have before
2023). We use it as the historical backbone and OpenF1 as the
high-resolution source for recent seasons.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fastf1
import pandas as pd

logger = logging.getLogger(__name__)


def enable_cache(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))


def get_event_schedule(year: int) -> pd.DataFrame:
    """All race weekends (and their session names) for a season."""
    return fastf1.get_event_schedule(year, include_testing=False)


def load_session(
    year: int,
    gp: int | str,
    identifier: str,
    *,
    laps: bool = True,
    telemetry: bool = True,
    weather: bool = True,
    messages: bool = True,
) -> fastf1.core.Session:
    """Load one session (e.g. year=2023, gp=5, identifier='R').

    Raises whatever fastf1 raises (e.g. if the session doesn't exist or
    hasn't happened yet) -- callers decide whether to skip or retry.
    """
    session = fastf1.get_session(year, gp, identifier)
    session.load(laps=laps, telemetry=telemetry, weather=weather, messages=messages)
    return session


def extract_laps(session: fastf1.core.Session) -> pd.DataFrame:
    """Lap-level timing: lap time, sector times, tire compound/age, pit flags."""
    laps = session.laps.copy()
    laps["Season"] = session.event.year
    laps["RoundNumber"] = session.event.RoundNumber
    laps["SessionName"] = session.name
    return pd.DataFrame(laps)


def extract_telemetry(session: fastf1.core.Session) -> pd.DataFrame:
    """Per-lap car telemetry (speed, throttle, brake, gear, RPM, DRS) for every driver."""
    frames = []
    for _, lap in session.laps.iterlaps():
        try:
            tel = lap.get_car_data().add_distance()
        except Exception:
            logger.warning(
                "No telemetry for driver=%s lap=%s in %s %s",
                lap.get("Driver"), lap.get("LapNumber"), session.event.year, session.name,
            )
            continue
        tel = tel.copy()
        tel["Driver"] = lap["Driver"]
        tel["LapNumber"] = lap["LapNumber"]
        tel["Season"] = session.event.year
        tel["RoundNumber"] = session.event.RoundNumber
        tel["SessionName"] = session.name
        frames.append(tel)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def extract_results(session: fastf1.core.Session) -> pd.DataFrame:
    """Session classification: finishing position, grid, status, points."""
    results = session.results.copy()
    results["Season"] = session.event.year
    results["RoundNumber"] = session.event.RoundNumber
    results["SessionName"] = session.name
    return pd.DataFrame(results)


def extract_weather(session: fastf1.core.Session) -> pd.DataFrame:
    weather = session.weather_data.copy()
    weather["Season"] = session.event.year
    weather["RoundNumber"] = session.event.RoundNumber
    weather["SessionName"] = session.name
    return pd.DataFrame(weather)
