"""Orchestrates ingestion: pulls each race weekend's sessions from FastF1
(and OpenF1 where available) and writes raw per-session Parquet files to
the data lake, partitioned by season/round/session.

This stage only fetches and lands raw data -- it does not normalize
schemas or build features. See src/f1dataset/processing/ for that.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from f1dataset.config import Settings
from f1dataset.ingestion import fastf1_client
from f1dataset.ingestion.openf1_client import OpenF1Client

logger = logging.getLogger(__name__)

# OpenF1's `session_name` values don't match FastF1's short identifiers, so we
# translate before filtering OpenF1's /sessions endpoint.
_OPENF1_SESSION_ALIASES = {
    "FP1": "PRACTICE 1",
    "FP2": "PRACTICE 2",
    "FP3": "PRACTICE 3",
    "Q": "QUALIFYING",
    "SPRINT": "SPRINT",
    "SPRINT SHOOTOUT": "SPRINT SHOOTOUT",
    "R": "RACE",
}


def backfill_season(season: int, settings: Settings) -> None:
    fastf1_client.enable_cache(settings.fastf1_cache_dir)
    openf1_client = OpenF1Client(settings.openf1) if season >= settings.openf1.min_season else None

    schedule = fastf1_client.get_event_schedule(season)
    _save_schedule(schedule, season, settings)
    for _, event in schedule.iterrows():
        _ingest_event(season, event, settings, openf1_client)


def _save_schedule(schedule: pd.DataFrame, season: int, settings: Settings) -> None:
    """Cache the event schedule alongside the raw data so `build-features`
    can reconstruct session metadata (circuit/country/event name) without
    needing network access again."""
    season_dir = settings.raw_dir / f"season={season}"
    season_dir.mkdir(parents=True, exist_ok=True)
    _save(schedule, season_dir / "schedule.parquet")


def update_latest(settings: Settings) -> None:
    """Ingest any sessions from the current season that have completed but
    aren't in the data lake yet. Intended to run on a schedule after each
    race weekend."""
    season = datetime.now(timezone.utc).year
    if season < settings.fastf1.min_season:
        logger.info("season %s predates fastf1 coverage (%s); nothing to do", season, settings.fastf1.min_season)
        return

    fastf1_client.enable_cache(settings.fastf1_cache_dir)
    openf1_client = OpenF1Client(settings.openf1) if season >= settings.openf1.min_season else None

    now = pd.Timestamp.now(tz="UTC")
    schedule = fastf1_client.get_event_schedule(season)
    _save_schedule(schedule, season, settings)
    for _, event in schedule.iterrows():
        event_date = event.get("EventDate")
        if pd.isna(event_date) or pd.Timestamp(event_date, tz="UTC") > now:
            continue  # weekend hasn't happened yet
        _ingest_event(season, event, settings, openf1_client, skip_if_present=True)


def _ingest_event(
    season: int,
    event: pd.Series,
    settings: Settings,
    openf1_client: OpenF1Client | None,
    skip_if_present: bool = False,
) -> None:
    round_number = int(event["RoundNumber"])
    location = event.get("Location")

    for session_name in settings.sessions_include:
        out_dir = (
            settings.raw_dir
            / f"season={season}"
            / f"round={round_number:02d}"
            / f"session={session_name}"
        )
        if skip_if_present and out_dir.exists():
            continue
        _ingest_session(season, round_number, session_name, out_dir, openf1_client, location)


def _ingest_session(
    season: int,
    round_number: int,
    session_name: str,
    out_dir: Path,
    openf1_client: OpenF1Client | None,
    location_hint: str | None,
) -> None:
    try:
        session = fastf1_client.load_session(season, round_number, session_name)
    except Exception as exc:
        logger.info(
            "skipping season=%s round=%s session=%s (not available yet or doesn't exist): %s",
            season, round_number, session_name, exc,
        )
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    _save(fastf1_client.extract_laps(session), out_dir / "fastf1_laps.parquet")
    _save(fastf1_client.extract_telemetry(session), out_dir / "fastf1_telemetry.parquet")
    _save(fastf1_client.extract_results(session), out_dir / "fastf1_results.parquet")
    _save(fastf1_client.extract_weather(session), out_dir / "fastf1_weather.parquet")

    if openf1_client is None:
        return

    session_key = _lookup_openf1_session_key(openf1_client, season, session_name, location_hint)
    if session_key is None:
        logger.info(
            "no OpenF1 session_key found for season=%s round=%s session=%s", season, round_number, session_name
        )
        return

    _save(openf1_client.get_laps(session_key), out_dir / "openf1_laps.parquet")
    _save(openf1_client.get_car_data(session_key), out_dir / "openf1_car_data.parquet")
    _save(openf1_client.get_stints(session_key), out_dir / "openf1_stints.parquet")
    _save(openf1_client.get_pit(session_key), out_dir / "openf1_pit.parquet")
    _save(openf1_client.get_weather(session_key), out_dir / "openf1_weather.parquet")
    _save(openf1_client.get_race_control(session_key), out_dir / "openf1_race_control.parquet")


def _lookup_openf1_session_key(
    client: OpenF1Client, season: int, session_name: str, location_hint: str | None
) -> int | None:
    sessions = client.get_sessions(year=season)
    if sessions.empty:
        return None

    alias = _OPENF1_SESSION_ALIASES.get(session_name.upper(), session_name.upper())
    candidates = sessions[sessions["session_name"].str.upper() == alias]

    if location_hint and "location" in candidates.columns:
        by_location = candidates[candidates["location"].str.lower() == str(location_hint).lower()]
        if not by_location.empty:
            candidates = by_location

    if candidates.empty:
        return None
    return int(candidates.iloc[0]["session_key"])


def _save(df: pd.DataFrame, path: Path) -> None:
    if df is None or df.empty:
        return
    df.to_parquet(path, index=False)
