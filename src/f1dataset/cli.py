"""Command-line entrypoint: `f1dataset backfill|update|build-features`."""

from __future__ import annotations

import logging

import typer

from f1dataset import pipeline
from f1dataset.config import load_settings

app = typer.Typer(help="Build an ML-ready F1 dataset from OpenF1 and FastF1.")


@app.callback()
def _configure_logging(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@app.command()
def backfill(
    start: int = typer.Option(None, help="First season to ingest (defaults to config seasons.start)."),
    end: int = typer.Option(None, help="Last season to ingest, inclusive (defaults to config seasons.end)."),
) -> None:
    """Ingest raw session data for every season in [start, end]."""
    settings = load_settings()
    settings.ensure_dirs()
    start = start or settings.season_start
    end = end or settings.season_end
    for season in range(start, end + 1):
        typer.echo(f"Backfilling season {season}...")
        pipeline.backfill_season(season, settings)


@app.command()
def update() -> None:
    """Ingest any completed sessions from the current season not yet in the data lake."""
    settings = load_settings()
    settings.ensure_dirs()
    pipeline.update_latest(settings)


@app.command("build-features")
def build_features() -> None:
    """Build processed feature tables (currently: tire degradation) from raw laps."""
    typer.echo(
        "Feature-table generation from the raw data lake is on the roadmap - see PLAN.md Phase 3. "
        "Use f1dataset.processing.tire_degradation.build_tire_degradation_table directly for now."
    )


if __name__ == "__main__":
    app()
