"""Loads pipeline configuration from config/settings.yaml (or F1DATASET_CONFIG override)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "settings.yaml"


@dataclass(frozen=True)
class OpenF1Settings:
    base_url: str
    min_season: int
    request_timeout: int
    max_retries: int
    retry_backoff_seconds: int


@dataclass(frozen=True)
class FastF1Settings:
    min_season: int


@dataclass(frozen=True)
class Settings:
    season_start: int
    season_end: int
    raw_dir: Path
    processed_dir: Path
    fastf1_cache_dir: Path
    openf1: OpenF1Settings
    fastf1: FastF1Settings
    sessions_include: list[str]

    def ensure_dirs(self) -> None:
        for d in (self.raw_dir, self.processed_dir, self.fastf1_cache_dir):
            d.mkdir(parents=True, exist_ok=True)


def load_settings(config_path: Path | None = None) -> Settings:
    path = config_path or Path(os.environ.get("F1DATASET_CONFIG", DEFAULT_CONFIG_PATH))
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return Settings(
        season_start=raw["seasons"]["start"],
        season_end=raw["seasons"]["end"],
        raw_dir=REPO_ROOT / raw["paths"]["raw_dir"],
        processed_dir=REPO_ROOT / raw["paths"]["processed_dir"],
        fastf1_cache_dir=REPO_ROOT / raw["paths"]["fastf1_cache_dir"],
        openf1=OpenF1Settings(
            base_url=raw["openf1"]["base_url"],
            min_season=raw["openf1"]["min_season"],
            request_timeout=raw["openf1"]["request_timeout"],
            max_retries=raw["openf1"]["max_retries"],
            retry_backoff_seconds=raw["openf1"]["retry_backoff_seconds"],
        ),
        fastf1=FastF1Settings(min_season=raw["fastf1"]["min_season"]),
        sessions_include=list(raw["sessions"]["include"]),
    )
