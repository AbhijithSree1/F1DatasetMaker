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

## Status: Phase 0 complete (this commit)

Repo scaffolding, working ingestion clients, canonical schema definitions,
one fully-implemented processing module (tire degradation) as the reference
pattern, CLI, tests, and the scheduled-update workflow skeleton are in
place. Everything below is the remaining roadmap.

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

- [ ] Build canonical `sessions`, `drivers` tables (see
      `schemas/tables.py`) by merging FastF1 + OpenF1 metadata, keyed by the
      ids in `processing/normalize.py`
- [ ] Reconcile driver/team identity across seasons (number reuse, team name
      changes e.g. Alfa Romeo -> Sauber -> Audi)
- [ ] Unify units (km/h vs mph, Celsius, seconds vs lap-relative timestamps)
      between the two sources
- [ ] Session-key matching between FastF1 (year+round+identifier) and OpenF1
      (session_key) is currently done by session-name + circuit-location
      heuristic (`pipeline._lookup_openf1_session_key`) — validate this
      against a full season and handle mismatches

## Phase 3 — Feature engineering per model family

- [x] **Tire degradation** (reference implementation,
      `processing/tire_degradation.py`): stint-relative lap time delta,
      tire age, compound, stint lap index
- [ ] **Vehicle/telemetry models**: resample telemetry onto a common
      distance basis per corner/straight, derive acceleration/braking
      g-force proxies, gear-shift points, DRS-zone usage, per-corner speed
      traces
- [ ] **Driver behavior models**: braking distance from corner apex,
      throttle-application smoothness, lap-to-lap consistency (variance),
      teammate delta under matched conditions, qualifying-vs-race pace gap
- [ ] **Lap time / strategy models**: full lap table joined with
      tire/stint/weather/track-status/safety-car flags, suitable for
      lap-time or pit-strategy prediction
- [ ] `build-features` CLI command wired up to actually run these (currently
      a placeholder)

## Phase 4 — Data quality & validation

- [ ] Schema conformance checks against `schemas/tables.py` (e.g. via
      `pandera`) run in CI on every processed-table change
- [ ] Per-season coverage report (sessions ingested vs. scheduled, null
      rates per column)
- [ ] Outlier/sanity checks (e.g. impossible speeds, negative lap times)

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
