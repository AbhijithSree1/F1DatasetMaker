# F1DatasetMaker

Automated pipeline that pulls Formula 1 timing and telemetry data from
[OpenF1](https://openf1.org) and [FastF1](https://docs.fastf1.dev), normalizes
it into a consistent schema, builds curated ML-ready feature tables for
vehicle, driver, strategy, and tire models, and ships with an interactive
dashboard for exploring the result.

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

# No network access to OpenF1/FastF1 yet? Generate a synthetic race weekend,
# build every feature table, and populate the dashboard in one shot:
f1dataset demo

# With network access, ingest real data instead:
f1dataset backfill --start 2023 --end 2024   # -> data/raw/
f1dataset build-features                      # -> data/processed/ + dashboard data
f1dataset update                              # incremental: only new completed sessions

# Run tests
pytest
```

Config lives in `config/settings.yaml` (season range, output paths, which
sessions to ingest, OpenF1/FastF1 settings). Override the path with the
`F1DATASET_CONFIG` env var if needed.

## Dashboard

```bash
cd dashboard
npm install
npm run dev
```

A dark, F1-themed React dashboard (Vite + TypeScript + Tailwind + Recharts)
that reads the JSON exported by `f1dataset demo` / `build-features` from
`dashboard/public/data/`. No backend required. Pages:

- **Overview** - standings, podium, fastest lap, position-by-lap chart
- **Lap Times & Strategy** - lap time evolution with Safety Car shading, tire stint Gantt chart, pit stops
- **Telemetry** - speed/throttle/brake/gear traces for any two drivers' fastest laps, overlaid by distance, plus a time-delta trace
- **Driver Behavior** - consistency, pace-vs-consistency, teammate delta
- **Tire Degradation** - lap-time delta vs. tire age, faceted by compound
- **Data Quality** - live schema-conformance and sanity-check report

If `meta.json` reports `synthetic: true`, the banner in the header says so -
the dashboard never silently passes off generated data as real.

## Project layout

```
config/settings.yaml          pipeline configuration
src/f1dataset/
  config.py                   settings loader
  sample_data.py               synthetic race-weekend generator (offline dev/demo)
  raw_loader.py                reads back raw Parquet from data/raw/ for build-features
  features.py                  orchestrates every processing module + quality report
  dashboard_export.py          writes dashboard/public/data/*.json
  ingestion/
    openf1_client.py          OpenF1 REST API client
    fastf1_client.py          FastF1 wrapper (session load + extraction)
  processing/
    normalize.py               raw-source -> canonical table normalization
    vehicle_telemetry.py       per-lap telemetry summary + distance-binned traces
    driver_behavior.py         consistency, teammate delta, pace ranking
    lap_strategy.py            laps joined with weather/pit/tire context
    tire_degradation.py        lap-time delta vs. tire age
    data_quality.py            schema conformance + sanity checks
  schemas/tables.py            canonical column definitions (data dictionary)
  pipeline.py                  backfill / update orchestration -> raw data lake
  cli.py                       `f1dataset` command-line entrypoint
data/raw/                     raw per-session dumps, partitioned by season/round/session (gitignored)
data/processed/                curated, ML-ready tables (tracked in git)
dashboard/                     React dashboard (Vite + TS + Tailwind + Recharts)
.github/workflows/update-dataset.yml   scheduled incremental updates
```

## Data dictionary

Canonical processed tables (see `src/f1dataset/schemas/tables.py` for exact
column-level docs):

- **sessions** - one row per practice/qualifying/sprint/race session
- **drivers** / **teams** - driver/team reference data per season
- **laps** - lap time, sector times, tire compound/age, track status per lap
- **telemetry** - speed/throttle/brake/gear/RPM/DRS samples through each lap
- **stints** - tire stint boundaries and compound per driver per session
- **weather** - air/track temp, humidity, rainfall, wind, sampled through the session
- **pit_stops** - pit stop lap and stationary duration
- **results** - finishing position, grid, status, points, total time

Derived feature tables (`f1dataset.features.build_all_features`):

- **telemetry_summary** - per-lap top speed, throttle/brake/DRS/gear usage
- **driver_behavior** - consistency, teammate delta, pace rank, braking/throttle tendencies
- **lap_strategy** - laps joined with weather + pit-stop context, for lap-time/strategy models
- **tire_degradation** - lap-time delta vs. stint-best, by tire age and compound

Raw data lands under `data/raw/season=<Y>/round=<N>/session=<S>/` as one
Parquet file per source table (e.g. `fastf1_laps.parquet`,
`openf1_car_data.parquet`). `f1dataset build-features` normalizes these into
the canonical tables above and writes both Parquet (`data/processed/`) and
compact JSON (`dashboard/public/data/`) outputs.

## Data source terms

OpenF1 and FastF1 are both free/open projects intended for personal and
research use; review their respective terms before any commercial or
redistribution use of the resulting dataset.
