# F1DatasetMaker

Automated pipeline that pulls Formula 1 timing and telemetry data from
[OpenF1](https://openf1.org) and [FastF1](https://docs.fastf1.dev), normalizes
it into a consistent schema, and builds curated, ML-ready datasets for
training vehicle, driver, strategy, and tire models.

See [`PLAN.md`](PLAN.md) for the full project roadmap.

## Why two data sources?

| Source | Coverage | Strength |
|---|---|---|
| **FastF1** | 2018 - present | Official timing data + telemetry, broadest historical range |
| **OpenF1** | 2023 - present | Higher-resolution live/near-real-time telemetry (car data, position, race control, team radio) |

The pipeline uses FastF1 as the historical backbone for every season and
layers in OpenF1 data wherever it's available (2023+) for extra signal.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Ingest raw data for a season range (writes to data/raw/, gitignored)
f1dataset backfill --start 2023 --end 2024

# Ingest only sessions from the current season not yet on disk
f1dataset update

# Run tests
pytest
```

Config lives in `config/settings.yaml` (season range, output paths, which
sessions to ingest, OpenF1/FastF1 settings). Override the path with the
`F1DATASET_CONFIG` env var if needed.

## Project layout

```
config/settings.yaml          pipeline configuration
src/f1dataset/
  config.py                   settings loader
  ingestion/
    openf1_client.py          OpenF1 REST API client
    fastf1_client.py          FastF1 wrapper (session load + extraction)
  processing/
    normalize.py              canonical id helpers (session/driver/team)
    tire_degradation.py       reference feature-table builder
  schemas/tables.py           canonical column definitions (data dictionary)
  pipeline.py                 backfill / update orchestration -> raw data lake
  cli.py                      `f1dataset` command-line entrypoint
data/raw/                     raw per-session dumps, partitioned by season/round/session (gitignored)
data/processed/                curated, ML-ready tables (tracked in git)
.github/workflows/update-dataset.yml   scheduled incremental updates
```

## Data dictionary

Canonical processed tables (see `src/f1dataset/schemas/tables.py` for exact
column-level docs):

- **sessions** - one row per practice/qualifying/sprint/race session
- **drivers** - driver/team reference data per season
- **laps** - lap time, sector times, tire compound/age, track status per lap
- **telemetry** - speed/throttle/brake/gear/RPM/DRS samples through each lap
- **stints** - tire stint boundaries and compound per driver per session
- **weather** - air/track temp, humidity, rainfall, wind, sampled through the session
- **pit_stops** - pit stop lap and stationary duration

Raw data lands under `data/raw/season=<Y>/round=<N>/session=<S>/` as one
Parquet file per source table (e.g. `fastf1_laps.parquet`,
`openf1_car_data.parquet`). Processing code reads these and writes the
normalized, joined tables above into `data/processed/`.

## Data source terms

OpenF1 and FastF1 are both free/open projects intended for personal and
research use; review their respective terms before any commercial or
redistribution use of the resulting dataset.
