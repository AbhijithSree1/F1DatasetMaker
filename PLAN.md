# F1DatasetMaker — Project Plan

## Goal

Build an automated pipeline that continuously pulls F1 timing/telemetry data
and turns it into clean, versioned, ML-ready datasets for training multiple
model families: **vehicle/telemetry models, driver behavior models, lap
time & race strategy prediction, and tire degradation models.**

## Decisions locked in

- **Sources:** OpenF1 (2023+, high-resolution telemetry & live data) +
  FastF1 (2018+, official timing data, broadest history). No Ergast-only
  results-only source for now.
- **Output format:** Parquet, partitioned by season/round/session for raw
  data and by table for processed data.
- **Scope:** Full historical backfill (2018-present) plus ongoing
  auto-updates after every race weekend via a scheduled GitHub Action.
- **Language/stack:** Python 3.11, `fastf1`, `requests`, `pandas`/`pyarrow`,
  `typer` CLI, `tenacity` for retries.

## Status

Phases 0, 3, 4, and 8 (dashboard) are complete. Phase 2's raw-source
normalizers are written and unit-tested but **not yet run against real
ingested data** — this dev environment has no outbound network access to
OpenF1/FastF1, so everything downstream of ingestion (feature tables,
quality report, dashboard) has so far only been exercised against
`sample_data.generate_race_weekend()`, a synthetic race weekend built
directly in the canonical schema. The normalize/build-features code path
for *real* raw data (`f1dataset build-features`) is implemented and unit
tested with mocked FastF1/OpenF1-shaped frames, but needs a real backfill
run (e.g. in CI, which has network access) to validate end-to-end.

---

## Phase 1 — Ingestion hardening

- [x] OpenF1 client covering meetings/sessions/drivers/laps/car_data/
      position/location/intervals/pit/stints/weather/race_control/team_radio
- [x] FastF1 client wrapping session load + laps/telemetry/results/weather
      extraction
- [x] Raw data lands as Parquet under `data/raw/season=/round=/session=/`
- [ ] Resumability: skip sessions already on disk during backfill (partially
      done for `update`; extend to `backfill` with a `--force` override)
- [ ] Rate-limit / backoff tuning against OpenF1's actual limits in
      production (currently a generic exponential backoff)
- [ ] Handle sprint-weekend session naming variants across seasons (F1
      renamed sprint sessions multiple times: "Sprint Shootout" vs "Sprint
      Qualifying")
- [ ] Dedup/upsert logic so re-running backfill for an already-ingested
      session is a safe no-op

## Phase 2 — Normalization & entity resolution

- [x] `build_sessions_table` / `build_drivers_table` / `build_teams_table`:
      canonical reference tables from raw FastF1 metadata
      (`processing/normalize.py`)
- [x] `normalize_fastf1_laps` / `normalize_fastf1_telemetry` /
      `normalize_fastf1_weather` / `normalize_fastf1_results`: raw FastF1 ->
      canonical schema, unit tested against mocked FastF1-shaped frames
- [x] `normalize_openf1_stints` / `normalize_openf1_pit`: raw OpenF1 ->
      canonical schema; `derive_stints_from_laps` fallback for pre-2023
      seasons without OpenF1 stint data
- [x] `raw_loader.load_raw_tables`: tags every raw row with
      season/round/session from its directory path (authoritative
      regardless of what the source API called things) so normalization
      doesn't need per-source special-casing
- [ ] **Not yet validated against real data** (no network in this
      environment) — run `f1dataset backfill && f1dataset build-features`
      somewhere with network access and fix whatever the real FastF1/OpenF1
      responses inevitably don't match exactly (column name drift, dtype
      surprises, etc.)
- [ ] Reconcile driver/team identity across *seasons* (number reuse, team
      name changes e.g. Alfa Romeo -> Sauber -> Audi) — current ids are
      season-scoped by design, cross-season joins are a follow-up
- [ ] Session-key matching between FastF1 (year+round+identifier) and OpenF1
      (session_key) is currently done by session-name + circuit-location
      heuristic (`pipeline._lookup_openf1_session_key`) — validate this
      against a full season and handle mismatches

## Phase 3 — Feature engineering per model family

All four feature tables are implemented in `src/f1dataset/processing/` and
wired into `f1dataset.features.build_all_features`, which both `f1dataset
demo` and `f1dataset build-features` call:

- [x] **Tire degradation** (`tire_degradation.py`): stint-relative lap time
      delta, tire age, compound, stint lap index — excludes deleted/pit/
      safety-car laps so degradation isn't polluted by caution-period pace
- [x] **Vehicle/telemetry models** (`vehicle_telemetry.py`): per-lap top
      speed, throttle/brake/DRS/gear-shift summary, plus
      `build_distance_trace` for compact distance-binned traces (used by
      the dashboard's telemetry comparison page)
- [x] **Driver behavior models** (`driver_behavior.py`): green-flag-only
      lap-time consistency (std dev), pace rank, teammate delta, braking/
      throttle tendencies
- [x] **Lap time / strategy models** (`lap_strategy.py`): every lap joined
      with the nearest weather sample and pit-stop duration, keeping the
      compound/tyre-age/track-status columns already on `laps`
- [x] `build-features` CLI command runs the full pipeline: raw Parquet ->
      normalize -> feature tables -> Parquet + dashboard JSON

## Phase 4 — Data quality & validation

- [x] Schema conformance checks against `schemas/tables.py`
      (`processing/data_quality.build_schema_report`) — missing/extra
      columns and per-column null rates, run automatically by `demo` /
      `build-features` and surfaced on the dashboard's Data Quality page
- [x] Sanity/range checks (`run_sanity_checks`): positive lap times, sectors
      sum to lap time, speed/throttle/temperature ranges, unique finishing
      positions per session
- [ ] Per-season coverage report (sessions ingested vs. scheduled) — needs
      a real backfill to be meaningful
- [ ] `pandera`/CI integration to fail a workflow run on regressions, rather
      than just printing a summary

## Phase 5 — Automation

- [x] `.github/workflows/update-dataset.yml` skeleton: scheduled run of
      `f1dataset update` + `build-features`, commits `data/processed/`
      changes back to the branch
- [ ] Needs repo Settings -> Actions -> "Read and write permissions" enabled
      for `GITHUB_TOKEN` before the commit-back step will succeed
- [ ] Alerting on ingestion failures (e.g. a GitHub issue auto-filed on
      workflow failure)

## Phase 6 — Distribution

- [ ] Tag dataset releases (e.g. `v2024.1`) so ML consumers can pin a
      version instead of tracking the moving `data/processed/` directory
- [ ] Evaluate publishing to the Hugging Face Hub as a proper dataset (with
      a dataset card) once `data/processed/` is large enough that git
      history bloat becomes a problem — Parquet in git is fine at
      current scale but doesn't scale indefinitely
- [ ] Write per-table dataset cards (schema, coverage, known gaps,
      license/attribution)

## Phase 7 (stretch) — Baseline models

Small notebooks/scripts that consume the processed tables end-to-end, to
prove the dataset is actually usable for what it was built for:
- Lap-time prediction baseline (gradient boosting on lap + weather + tire
  features)
- Tire degradation regression per compound/circuit
- Driver style clustering from braking/throttle telemetry features

## Phase 8 — Interactive dashboard

- [x] `dashboard/`: React + TypeScript + Vite + Tailwind + Recharts SPA,
      dark F1-themed UI, reads static JSON from `dashboard/public/data/`
      (no backend) written by `f1dataset.dashboard_export`
- [x] Overview (standings, podium, fastest lap, position-by-lap), Lap Times
      & Strategy (lap evolution with SC shading, tire-stint Gantt, pit
      stops), Telemetry (two-driver speed/throttle/brake/gear overlay +
      time-delta trace), Driver Behavior, Tire Degradation, and Data
      Quality pages
- [x] Header banner clearly flags synthetic vs. real data
      (`meta.json.synthetic`)
- [x] Verified with a headless-browser pass across all six routes (zero
      console errors) after fixing two real rendering bugs found that way:
      a clipped Y-axis label (lap-time axis needed more width) and a
      `'dataMax + N'` domain-string that recharts wasn't parsing correctly
      when mixed with a literal `0` (replaced with an explicit computed
      domain)
- [ ] Code-split the bundle (currently one ~680kB JS chunk) if the app
      grows further
- [ ] Point the dashboard at a specific season/round once multiple events
      are ingested (currently assumes a single session pair, matching what
      `demo`/`build-features` produce today)

---

## Open questions / risks

- **OpenF1 rate limits & uptime**: it's a community-run free API; the
  client backs off on 429/5xx but sustained backfills across 7 seasons will
  take real wall-clock time. Worth checking their limits before automating
  large day-one backfills.
- **FastF1 cache growth**: the FastF1 HTTP cache (`data/.fastf1_cache/`) can
  get large over a full historical backfill; it's gitignored and cached
  separately in CI (`actions/cache`), not committed.
- **Repo size over time**: `data/processed/` is tracked in git per your
  answer, which is simplest to start but will grow every week during a
  season. Phase 6 flags migrating to Hugging Face Hub or git-lfs if/when
  that becomes a problem — not needed yet.
- **Data licensing**: OpenF1/FastF1 data is intended for personal/research
  use; this plan assumes model training for personal/research purposes, not
  redistribution as a commercial product. Revisit before any commercial use.
