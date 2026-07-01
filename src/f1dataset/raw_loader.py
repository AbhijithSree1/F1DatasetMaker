"""Reads back the raw Parquet files `pipeline.backfill_season`/`update_latest`
wrote to `data/raw/season=/round=/session=/`, concatenated across every
ingested session, ready for `processing.normalize`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

_FASTF1_FILES = {
    "laps": "fastf1_laps.parquet",
    "telemetry": "fastf1_telemetry.parquet",
    "results": "fastf1_results.parquet",
    "weather": "fastf1_weather.parquet",
}
_OPENF1_FILES = {
    "openf1_stints": "openf1_stints.parquet",
    "openf1_pit": "openf1_pit.parquet",
}
_SESSION_DIR_RE = re.compile(r"season=(\d+)/round=(\d+)/session=([^/]+)$")


def load_raw_tables(raw_dir: Path) -> dict[str, pd.DataFrame]:
    """Concatenates every session's raw Parquet files by table name, plus
    the per-season cached event schedules under a 'schedule' key.

    Every row gets Season/RoundNumber/SessionName columns derived from its
    directory path (authoritative regardless of what the source API called
    things), so `processing.normalize` doesn't need per-source special-casing.
    """
    frames: dict[str, list[pd.DataFrame]] = {name: [] for name in {**_FASTF1_FILES, **_OPENF1_FILES}}
    frames["schedule"] = []

    for schedule_path in sorted(raw_dir.glob("season=*/schedule.parquet")):
        frames["schedule"].append(pd.read_parquet(schedule_path))

    session_dirs = sorted(raw_dir.glob("season=*/round=*/session=*"))
    for session_dir in session_dirs:
        match = _SESSION_DIR_RE.search(session_dir.as_posix())
        if not match:
            continue
        season, round_number, session_name = int(match[1]), int(match[2]), match[3]

        for name, filename in {**_FASTF1_FILES, **_OPENF1_FILES}.items():
            path = session_dir / filename
            if not path.exists():
                continue
            df = pd.read_parquet(path)
            df["Season"] = season
            df["RoundNumber"] = round_number
            df["SessionName"] = session_name
            frames[name].append(df)

    return {name: (pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()) for name, parts in frames.items()}
