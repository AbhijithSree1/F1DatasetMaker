# F1DatasetMaker Dashboard

A static React SPA (Vite + TypeScript + Tailwind + Recharts) for exploring
the dataset built by the Python pipeline in the repo root. No backend: it
fetches pre-computed JSON from `public/data/`.

```bash
npm install
npm run dev
```

`public/data/*.json` is written by `f1dataset demo` or `f1dataset
build-features` (see the root [README](../README.md)) via
`src/f1dataset/dashboard_export.py`. Regenerate it after re-running the
pipeline, then just refresh the browser -- the dev server serves the JSON
directly from `public/`.

## Pages

- **Overview** -- standings, podium, fastest lap, position-by-lap chart
- **Lap Times & Strategy** -- lap time evolution (Safety Car periods shaded), tire stint Gantt chart, pit stops
- **Telemetry** -- speed/throttle/brake/gear traces for any two drivers, overlaid by distance, plus a time-delta trace
- **Driver Behavior** -- consistency, pace-vs-consistency, teammate delta
- **Tire Degradation** -- lap-time delta vs. tire age, by compound
- **Data Quality** -- the schema-conformance and sanity-check report from the pipeline

## Commands

- `npm run dev` -- start the dev server
- `npm run build` -- typecheck + production build to `dist/`
- `npm run lint` -- oxlint
