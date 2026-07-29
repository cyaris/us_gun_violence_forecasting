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
    lib/components/USGunViolenceForecasting.svelte
    lib/static/data.json           # generated forecast data, ignored by git
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

That file is intentionally ignored by git.

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

The generated `data.json` is also ignored by git.

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

The Vite dev server is configured to use port `3000`.

## Frontend Commands

```bash
npm run check        # Svelte diagnostics
npm run build        # production build
npm run preview      # preview production build
npm run lint         # eslint
npm run format       # prettier
```

## GitHub Actions Workflows

These local wrappers inherit their reusable implementations from `cyaris/shared-automation`. Manual `workflow_dispatch` paths delegated to the shared workflows are restricted to the `cyaris` GitHub actor by default.

### `.github/workflows/auto-create-dev-pr.yml`

The `Auto-create dev pull request` workflow runs on pushes to `dev` and delegates to the shared
`cyaris/shared-automation/.github/workflows/auto-create-dev-pr.yml` workflow. It opens a `dev` to repository-default
branch pull request when one does not already exist.

This workflow has no GitHub Actions UI dispatch path. To run the same behavior manually, dispatch the reusable workflow
from `cyaris/shared-automation` or create the pull request with `gh pr create`. The workflow passes `RELEASE_TOKEN` so
the shared workflow can create pull requests when the default token is restricted.

### `.github/workflows/ci.yml`

The `CI` workflow runs on pushes, pull requests, and manual dispatch. It calls the shared
`cyaris/shared-automation/.github/workflows/ci.yml` workflow with `working-directory: frontend` to install
frontend dependencies and run the default format, lint, and Svelte check commands. CI skips `npm run build` because a
clean checkout does not include the ignored generated forecast data file; run production builds after regenerating
`frontend/src/lib/static/data.json`.

The workflow can be dispatched from the GitHub Actions UI with **Actions > CI > Run workflow**. Manual dispatch exposes
the `svelte-lib-ref` input for choosing the sibling `svelte-lib` ref checked out for the local `file:` dependency.
Push and pull-request runs use `SVELTE_LIB_REF` when set, otherwise they select `dev` for matching `dev` base, head, or
ref names and `main` for all other refs.

### `.github/workflows/rollup-upload.yml`

The `Rollup upload` GitHub Actions workflow builds the frontend rollup bundle and uploads it to
`s3://cyaris.github.io/us_gun_violence_forecasting/`.

The workflow runs automatically on pushes to `main` or `master`, including merges into those branches, and can be
dispatched from the GitHub Actions UI with **Actions > Rollup upload > Run workflow**. Manual dispatch uploads staged
`test_bundle.*` files by default. Set `production` during manual dispatch to upload live `bundle.*` files instead; set
`dry-run` to print S3 operations without writing objects. Automatic push runs always use production upload names and
disable `dry-run`.

Set the repository variable `SVELTE_LIB_REF` to control which `svelte-lib` branch, tag, or SHA the automatic production
workflow checks out for both the local file dependency and the shared rollup upload action. Manual dispatch exposes the
same value as the `svelte-lib-ref` input.

The workflow checks out `cyaris/shared-automation` for the shared rollup upload action and separately checks out the private `svelte-lib` repository as a local dependency.
Provide `CHECKOUT_TOKEN` with read access to `svelte-lib` and any private local dependency repositories. AWS
authentication uses `AWS_ROLLUP_UPLOAD_ROLE_ARN` when present, otherwise it expects AWS access-key secrets.

The upload refreshes cache metadata in place for
`us_gun_violence_forecasting/all-shootings-2014-2023.csv`.

### `.github/workflows/auto-release.yml`

The `Auto release` workflow runs from manual dispatch only and delegates to the shared
`cyaris/shared-automation/.github/workflows/auto-release.yml` workflow. It reconciles commit history through a selected
commit against existing GitHub releases, updates existing release notes and titles when enabled, and creates missing
releases when warranted by the repository release policy.

The workflow can be dispatched from the GitHub Actions UI with **Actions > Auto release > Run workflow**. Manual dispatch
accepts optional `release-sha`, `shared-automation-ref`, `publish`, and `update-existing` inputs; when `release-sha` is
blank, it reconciles through the current default branch tip. Release reconciliation requires `OPENAI_API_KEY`; missing
credentials or failed OpenAI API requests fail the workflow. `RELEASE_TOKEN` and `CHECKOUT_TOKEN` can be provided when
the default token cannot create releases or read private repositories.

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

## Data Source

The source shooting data comes from the Figshare dataset
<a href="https://figshare.com/articles/dataset/Gun_Violence_-_All_Shootings/25517224?file=45398359" target="_blank" rel="noopener noreferrer">Gun Violence - All Shootings</a>.

Original incident data is credited to the non-profit <a href="https://www.gunviolencearchive.org/" target="_blank" rel="noopener noreferrer">Gun Violence Archive</a>.

## Notes

- `backend/all-shootings-2014-2023.csv` and `frontend/src/lib/static/data.json` are local/generated data artifacts and are not committed.
- The backend fits one Prophet model per observed year, so regenerating data can take time.
- `npm run build` may show warnings from third-party `svelte-lib` or `svelte-select` components; those are dependency warnings rather than local component errors.
