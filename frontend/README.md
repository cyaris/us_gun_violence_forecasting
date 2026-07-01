# US Gun Violence Forecasting Frontend

SvelteKit frontend for the US Gun Violence Forecasting visualization. The app renders historical daily victim counts, Prophet-generated forecast series, smoothing controls, visibility filters, and comparative model hover states.

The live project is published at [charlieyaris.com/us_gun_violence_forecasting](https://charlieyaris.com/us_gun_violence_forecasting/).

For the full project overview, backend setup, data source, and forecast-generation workflow, see the repository-level [README](../README.md).

## What is included

- `src/lib/components/USGunViolenceForecasting.svelte`: main interactive visualization.
- `src/routes/+page.svelte`: route that renders the visualization.
- `src/lib/static/data.json`: generated forecast data consumed by the app.
- Shared UI components and Vite configuration from the local `svelte-lib` package.

## Prerequisites

- Node.js and npm.
- A sibling `svelte-lib` checkout, because this project depends on:

```json
"svelte-lib": "file:../../svelte-lib"
```

- Generated forecast data at:

```text
src/lib/static/data.json
```

That file is produced by the backend pipeline and is intentionally ignored by git.

## Setup

Install dependencies from this directory:

```sh
npm install
```

Run the development server:

```sh
npm run dev
```

Open the local Vite URL shown in the terminal. The dev server is configured through the shared `svelte-lib` Vite config.

## Commands

```sh
npm run check        # Svelte diagnostics
npm run build        # production build
npm run preview      # preview production build
npm run lint         # eslint
npm run lint:fix     # eslint with fixes
npm run format       # prettier write
npm run format:check # prettier check
```

Package build helpers are also available:

```sh
npm run rollup
npm run rollup:watch
```

## Data Expectations

The frontend imports `src/lib/static/data.json` directly. The generated rows are expected to include:

- `date`: day in `YYYY-MM-DD` format.
- `observed_victims`: daily injured plus killed victim count, or `null` for forecast rows.
- `is_forecast`: whether the row is a future forecast row.
- `predicted_victims_<year>`: model prediction from a Prophet model trained through that year.

Regenerate this file from the repository root with the backend command documented in [../README.md](../README.md).

## Local Development Notes

- Rebuild `svelte-lib` after changing shared components so this app can consume the updated package output.
- `npm run check` runs `svelte-kit sync` before Svelte diagnostics.
- Build warnings may come from third-party wrapped components in `svelte-lib`; verify whether they affect this app before treating them as local regressions.
