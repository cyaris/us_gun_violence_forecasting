# US Gun Violence Forecasting

Interactive Svelte visualization for exploring historical US gun violence victim counts and Prophet-based daily forecasts.

View the live tool at [cyaris.github.io/us_gun_violence_forecasting](https://cyaris.github.io/us_gun_violence_forecasting/).

The project has two parts:

- `backend/`: Python data pipeline that reads Gun Violence Archive exports, fits yearly Prophet models, and writes the visualization JSON.
- `frontend/`: SvelteKit app that renders the chart, controls, metrics, and forecast comparison UI.

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
- A local `svelte-lib` checkout available at `../svelte-lib` relative to this repository's parent directory, because the frontend depends on:

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

## Data Model

The generated JSON contains daily rows with:

- `date`: `YYYY-MM-DD`
- `observed_victims`: daily injured + killed victim count, or `null` for future forecast rows
- `is_forecast`: whether the row is a future forecast row
- `predicted_victims_<year>`: Prophet prediction from the model trained through that year

The frontend uses these columns to show:

- daily observations
- the latest overall model
- historical comparative models on hover
- smoothed moving-average views
- past and future metric summaries

## Data Source

The source shooting data comes from the Figshare dataset
[Gun Violence - All Shootings](https://figshare.com/articles/dataset/Gun_Violence_-_All_Shootings/25517224?file=45398359).

Original incident data is credited to the non-profit [Gun Violence Archive](https://www.gunviolencearchive.org/).

## Notes

- `backend/all-shootings-2014-2023.csv` and `frontend/src/lib/static/data.json` are local/generated data artifacts and are not committed.
- The backend fits one Prophet model per observed year, so regenerating data can take time.
- `npm run build` may show warnings from third-party `svelte-lib` or `svelte-select` components; those are dependency warnings rather than local component errors.
