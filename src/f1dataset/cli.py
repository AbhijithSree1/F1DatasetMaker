"""Command-line entrypoint: `f1dataset backfill|update|build-features|demo`."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import typer

from f1dataset import dashboard_export, features, pipeline, raw_loader, sample_data
from f1dataset.config import Settings, load_settings
from f1dataset.processing import normalize

app = typer.Typer(help="Build an ML-ready F1 dataset from OpenF1 and FastF1.")
logger = logging.getLogger(__name__)

DASHBOARD_DATA_DIR = Path(__file__).resolve().parents[2] / "dashboard" / "public" / "data"


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
    """Normalize raw ingested data (data/raw/) and build every processed feature table."""
    settings = load_settings()
    settings.ensure_dirs()

    raw = raw_loader.load_raw_tables(settings.raw_dir)
    if raw["laps"].empty:
        typer.echo(
            "No raw data found in data/raw. Run `f1dataset backfill` first "
            "(requires network access to FastF1/OpenF1), or run `f1dataset demo` "
            "to build the dataset + dashboard from a synthetic sample instead."
        )
        raise typer.Exit(code=1)

    drivers = normalize.build_drivers_table(raw["results"])
    tables = {
        "teams": normalize.build_teams_table(raw["results"]),
        "drivers": drivers,
        "sessions": normalize.build_sessions_table(raw["laps"], raw["schedule"]),
        "laps": normalize.normalize_fastf1_laps(raw["laps"]),
        "telemetry": normalize.normalize_fastf1_telemetry(raw["telemetry"], drivers),
        "weather": normalize.normalize_fastf1_weather(raw["weather"]),
        "results": normalize.normalize_fastf1_results(raw["results"]),
    }
    if not raw["openf1_stints"].empty:
        tables["stints"] = normalize.normalize_openf1_stints(raw["openf1_stints"])
    else:
        typer.echo("No OpenF1 stint data found (pre-2023 season or not ingested); deriving stints from laps.")
        tables["stints"] = normalize.derive_stints_from_laps(tables["laps"])

    if not raw["openf1_pit"].empty:
        tables["pit_stops"] = normalize.normalize_openf1_pit(raw["openf1_pit"])
    else:
        typer.echo("No OpenF1 pit data found; pit_stops will be empty (pit_duration_s isn't reconstructable from FastF1 alone).")
        tables["pit_stops"] = pd.DataFrame(columns=["session_id", "driver_id", "lap_number", "pit_duration_s"])

    _build_and_export(tables, settings, synthetic=False)


@app.command()
def demo() -> None:
    """Generate a synthetic race weekend and build the full processed dataset + dashboard data.

    Useful when you don't have network access to OpenF1/FastF1 yet, or just
    want to see the pipeline and dashboard working end-to-end immediately.
    """
    settings = load_settings()
    settings.ensure_dirs()
    typer.echo("Generating synthetic race weekend...")
    tables = sample_data.generate_race_weekend()
    _build_and_export(tables, settings, synthetic=True)


def _build_and_export(tables: dict[str, pd.DataFrame], settings: Settings, synthetic: bool) -> None:
    typer.echo("Building feature tables...")
    all_tables = features.build_all_features(tables)

    typer.echo("Running data quality checks...")
    quality_report = features.build_quality_report(all_tables)
    _print_quality_summary(quality_report)

    typer.echo(f"Writing processed tables to {settings.processed_dir}...")
    for name, df in all_tables.items():
        df.to_parquet(settings.processed_dir / f"{name}.parquet", index=False)
    for name, df in quality_report.items():
        df.to_parquet(settings.processed_dir / f"quality_{name}.parquet", index=False)

    typer.echo(f"Exporting dashboard data to {DASHBOARD_DATA_DIR}...")
    dashboard_export.export_dashboard_data(all_tables, quality_report, DASHBOARD_DATA_DIR, synthetic=synthetic)
    typer.echo("Done. Run the dashboard with: cd dashboard && npm install && npm run dev")


def _print_quality_summary(quality_report: dict[str, pd.DataFrame]) -> None:
    schema_report = quality_report["schema_report"]
    failed_schema = schema_report[schema_report["passed"] == False]  # noqa: E712
    sanity = quality_report["sanity_checks"]
    failed_sanity = sanity[sanity["passed"] == False]  # noqa: E712

    if failed_schema.empty and failed_sanity.empty:
        typer.echo("Data quality: all schema and sanity checks passed.")
        return

    if not failed_schema.empty:
        typer.echo(f"Data quality: {len(failed_schema)} table(s) failed schema conformance:")
        for _, row in failed_schema.iterrows():
            typer.echo(f"  - {row['table']}: missing columns {row['missing_columns']}")
    if not failed_sanity.empty:
        typer.echo(f"Data quality: {len(failed_sanity)} sanity check(s) failed:")
        for _, row in failed_sanity.iterrows():
            typer.echo(f"  - {row['check']} ({row['table']}): {row['detail']}")


if __name__ == "__main__":
    app()
