# US Gun Violence Forecasting

Interactive Svelte visualization for exploring historical US gun violence victim counts and Prophet-based daily forecasts.

The main purpose of the tool is to compare forecasts across time. As each new
year of observed data becomes available, the backend fits another Prophet model;
the frontend then lets users hover over the chart to see how forecasts from
earlier model snapshots compare with later ones and with the eventual observed
victim counts. The hover interaction is designed to show how the forecast
changed as more data was received.

View the live tool at <a href="https://charlieyaris.com/us_gun_violence_forecasting/" target="_blank" rel="noopener noreferrer">charlieyaris.com/us_gun_violence_forecasting</a>.

The project has two parts:

- `backend/`: Python data pipeline that reads Gun Violence Archive exports, fits yearly Prophet models, and writes the visualization JSON
- `frontend/`: SvelteKit app that renders the chart, controls, metrics, and forecast comparison UI

## Repository Structure

```text
backend/
  all-shootings-2014-2023.csv      # local source data, ignored by git
  pyproject.toml                   # Python dependencies and tooling config
  src/
    update_forecast_data.py        # forecast data generation CLI
    utils.py                       # logging helpers

frontend/
  package.json                     # frontend scripts
  src/
    lib/components/Tool.svelte
    lib/static/data.json           # generated forecast data committed for clean Rollup builds
    routes/+page.svelte            # renders the visualization
```

## Prerequisites

- Python 3.11+
- Node.js and npm

The frontend also expects a local `svelte-lib` checkout at `../svelte-lib` relative to this repository's parent
directory because it depends on:

```json
"svelte-lib": "file:../../svelte-lib"
```

## Backend Setup

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

The backend expects the source CSV at:

```text
backend/all-shootings-2014-2023.csv
```

That source CSV is intentionally ignored by git.

## Generate Forecast Data

Dry-run the source data load:

```bash
cd backend
source .venv/bin/activate
python src/update_forecast_data.py --dry-run
```

Regenerate the frontend JSON:

```bash
python src/update_forecast_data.py
```

By default, this writes:

```text
frontend/src/lib/static/data.json
```

The repository commits generated `data.json` so clean GitHub Actions checkouts can build the Rollup bundle.

Useful options:

```bash
python src/update_forecast_data.py \
  --input-csv backend/all-shootings-2014-2023.csv \
  --output-json frontend/src/lib/static/data.json \
  --forecast-days 365 \
  --changepoint-prior-scale 0.01
```

## Frontend Setup

From the repository root:

```bash
cd frontend
npm install
```

Run the dev server:

```bash
npm run dev
```

The Vite dev server listens on port `3000`.

## Frontend Commands

Useful commands:

```bash
npm run check        # Svelte diagnostics
npm run build        # production build
npm run preview      # preview production build
npm run lint         # eslint
npm run format       # prettier
```

## Data Model

The generated JSON contains daily rows with:

- `date`: `YYYY-MM-DD`
- `observed_victims`: daily injured + killed victim count, or `null` for future forecast rows
- `is_forecast`: whether the row is a future forecast row
- `predicted_victims_<year>`: Prophet prediction from the model trained through that year

The frontend uses these columns to show:

- daily observations
- the latest overall model
- historical comparative models on hover, so users can compare earlier and later forecasts for the same dates
- smoothed moving-average views
- past and future metric summaries

Moving-average values appear on the row that completes each window. Average yearly trend compares matching calendar
dates; February 29 compares with February 28 in a non-leap prior year instead of shifting to March 1.

## Data Source

The source shooting data comes from the Figshare dataset
<a href="https://figshare.com/articles/dataset/Gun_Violence_-_All_Shootings/25517224?file=45398359" target="_blank" rel="noopener noreferrer">Gun Violence - All Shootings</a>.

Original incident data is credited to the non-profit <a href="https://www.gunviolencearchive.org/" target="_blank" rel="noopener noreferrer">Gun Violence Archive</a>.

## Notes

- `backend/all-shootings-2014-2023.csv` is a local source data artifact and is not committed.
- The backend generates `frontend/src/lib/static/data.json` from local source data, and the repository commits it for
  clean Rollup builds.
- The backend fits one Prophet model per observed year, so regenerating data can take time.
- `npm run build` may show warnings from third-party `svelte-lib` or `svelte-select` components; those are dependency warnings rather than local component errors.

## GitHub Actions Workflows

These local wrappers inherit their reusable implementations from `cyaris/shared-automation`. The
[shared-automation workflow reference](https://github.com/cyaris/shared-automation#workflows) documents shared
behavior, inputs, and secrets.

### `.github/workflows/frontend-ci.yml`

Runs tests, linting, formatting checks, Svelte checks, and the frontend build on pushes to `dev` or `main` that affect
the frontend or its CI wrapper. The shared workflow checks out the matching `svelte-lib` branch so staged and
production validation use the corresponding upstream package.

### `.github/workflows/auto-create-dev-pr.yml`

Runs on pushes to `dev` and calls the
[shared auto-create-dev-pr workflow](https://github.com/cyaris/shared-automation#githubworkflowsauto-create-dev-pryml).

### `.github/workflows/rollup.yml`

Calls the [shared rollup workflow](https://github.com/cyaris/shared-automation#githubworkflowsrollupyml) with these
local details:

- triggers: pushes to `dev` and `master`, plus manual dispatch
- working directory: `frontend`
- destination: `s3://cyaris.github.io/us_gun_violence_forecasting/`
- production naming: unprefixed bundles from `master`
- staged naming: `dev_bundle.*` from `dev`
- local dependency: `svelte-lib` `dev` for staged runs and `main` for production runs, resolved to an exact SHA
- metadata refresh: cache metadata refreshed in place for `us_gun_violence_forecasting/all-shootings-2014-2023.csv`

### `.github/workflows/upstream-watch.yml`

Runs daily at 12:53 UTC, 30 minutes before the GitHub Pages build for `cyaris.github.io`, and on manual dispatch, then
calls the
[shared upstream-watch workflow](https://github.com/cyaris/shared-automation#githubworkflowsupstream-watchyml). It
watches `svelte-lib`'s `dev` and `main` branch commits independently. When either branch moves, it dispatches this
repository's `Rollup` workflow on the matching `dev` or `master` branch so staged and production bundles pick up the
corresponding upstream code without waiting for a push here.

### `.github/workflows/auto-release.yml`

Runs from manual dispatch only and calls the
[shared auto-release workflow](https://github.com/cyaris/shared-automation#githubworkflowsauto-releaseyml). This
repository contributes `.github/release-policy.yml` overrides. Release creation or existing-release updates require
reviewing the generated plan and explicitly enabling publication for an approved run.

### `.github/workflows/workflow-validation.yml`

Runs on `dev` and `master` pushes that change `.github/release-policy.yml`, `.github/workflows/**`, or `renovate.json`,
and on manual dispatch, then calls the
[shared workflow-validation workflow](https://github.com/cyaris/shared-automation#githubworkflowsworkflow-validationyml)
to validate rollup upload wrapper logic, release-policy configuration, and Renovate configuration.
