"""Canonical id helpers shared across ingestion sources.

OpenF1 and FastF1 identify sessions/drivers/teams differently (numeric
session_key vs. year+event+session-name, driver_number vs. three-letter
abbreviation, etc). Everything downstream joins on the ids built here so a
row's provenance (which API it came from) doesn't leak into the schema.
"""

from __future__ import annotations

import re


def make_session_id(season: int, round_number: int, session_name: str) -> str:
    return f"{season}_{round_number:02d}_{session_name.upper()}"


def make_driver_id(season: int, driver_number: int) -> str:
    return f"{season}_{driver_number}"


def make_team_id(season: int, team_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", team_name.lower()).strip("-")
    return f"{season}_{slug}"
