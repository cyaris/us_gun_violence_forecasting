#!/usr/bin/env python3
"""Regenerate the Svelte forecast data from Gun Violence Archive exports."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_CSV = REPO_ROOT / "backend/all-shootings-2014-2023.csv"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "svelte/src/lib/static/data.json"

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the US gun violence daily harmed-victim forecast data JSON "
            "used by the Svelte visualization."
        )
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=DEFAULT_INPUT_CSV,
        help=f"GVA combined CSV to read. Defaults to {DEFAULT_INPUT_CSV}.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help=f"JSON file to update. Defaults to {DEFAULT_OUTPUT_JSON}.",
    )
    parser.add_argument(
        "--forecast-days",
        type=int,
        default=365,
        help="Number of future daily predictions to append after the final observed date.",
    )
    parser.add_argument(
        "--changepoint-prior-scale",
        type=float,
        default=0.5,
        help="Prophet changepoint_prior_scale value from the original notebook.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and summarize the source CSV without fitting Prophet or writing JSON.",
    )
    return parser.parse_args()


def import_prophet():
    try:
        from fbprophet import Prophet

        return Prophet
    except ModuleNotFoundError as fbprophet_error:
        if fbprophet_error.name != "fbprophet":
            raise

    try:
        from prophet import Prophet

        return Prophet
    except ModuleNotFoundError as prophet_error:
        if prophet_error.name != "prophet":
            raise
        raise RuntimeError(
            "Prophet is not installed. Install either the legacy 'fbprophet' package "
            "or the renamed 'prophet' package, then rerun this script."
        ) from prophet_error


def load_daily_harmed(input_csv: Path) -> pd.DataFrame:
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    incidents = pd.read_csv(
        input_csv,
        usecols=["Incident_Date", "Victims_Killed", "Victims_Injured"],
    )
    incidents["date"] = pd.to_datetime(incidents["Incident_Date"], errors="raise")
    incidents["num_harmed"] = (
        pd.to_numeric(incidents["Victims_Killed"], errors="coerce").fillna(0)
        + pd.to_numeric(incidents["Victims_Injured"], errors="coerce").fillna(0)
    )

    daily = incidents.groupby("date", as_index=False)["num_harmed"].sum()
    all_dates = pd.DataFrame({"date": pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")})
    daily = all_dates.merge(daily, on="date", how="left")
    daily["num_harmed"] = daily["num_harmed"].fillna(0).astype(int)
    return daily


def future_dataframe_lengths(df_date: pd.DataFrame, forecast_days: int) -> dict[int, int]:
    lengths: dict[int, int] = {}
    max_observed_date = df_date["date"].max()

    for year in df_date["date"].dt.year.drop_duplicates():
        next_year_dates = df_date.loc[df_date["date"].dt.year == year + 1, "date"]
        if next_year_dates.empty:
            lengths[int(year)] = forecast_days
        else:
            lengths[int(year)] = len(pd.period_range(next_year_dates.min(), max_observed_date, freq="D")) + forecast_days

    return lengths


def build_forecast_data(
    df_date: pd.DataFrame,
    forecast_days: int,
    changepoint_prior_scale: float,
) -> pd.DataFrame:
    Prophet = import_prophet()
    model_input = df_date.rename(columns={"date": "ds", "num_harmed": "y"})
    lengths = future_dataframe_lengths(df_date, forecast_days)
    d3_data: pd.DataFrame | None = None

    logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
    logging.getLogger("prophet").setLevel(logging.WARNING)

    for year in df_date["date"].dt.year.drop_duplicates():
        year = int(year)
        print(f"Fitting Prophet model through {year}...", flush=True)

        harmed_prophet = Prophet(
            changepoint_prior_scale=changepoint_prior_scale,
            daily_seasonality=True,
            yearly_seasonality=True,
        )
        harmed_prophet.fit(model_input[model_input["ds"].dt.year <= year])

        harmed_forecast = harmed_prophet.make_future_dataframe(periods=lengths[year], freq="D")
        harmed_forecast = harmed_prophet.predict(harmed_forecast)

        pred_col = f"pred_{year}"
        trend_col = f"yearly_trend_calc_{year}"
        harmed_forecast[trend_col] = harmed_forecast["yhat"] - harmed_forecast["yhat"].shift(periods=365)
        harmed_forecast = harmed_forecast.rename(columns={"ds": "date", "yhat": pred_col})

        if d3_data is None:
            d3_data = harmed_forecast[["date", pred_col]].merge(df_date, on="date", how="outer")
            d3_data = harmed_forecast[["date", trend_col]].merge(d3_data, on="date", how="outer")
        else:
            d3_data = harmed_forecast[["date", pred_col]].merge(d3_data, on="date", how="outer")
            d3_data = harmed_forecast[["date", trend_col]].merge(d3_data, on="date", how="outer")

    if d3_data is None:
        raise ValueError("No yearly models were fit because the daily dataset is empty.")

    return d3_data


def prepare_for_visualization(d3_data: pd.DataFrame) -> pd.DataFrame:
    d3_data = d3_data.reset_index()

    d3_data["non_observation"] = None
    first_future_index = d3_data.index[d3_data["num_harmed"].isna()].min()
    if pd.notna(first_future_index):
        d3_data.loc[d3_data["index"] >= first_future_index, "non_observation"] = 1

    d3_data["num_harmed"] = pd.Series(
        [None if pd.isna(value) else int(value) for value in d3_data["num_harmed"]],
        index=d3_data.index,
        dtype=object,
    )
    d3_data["year"] = d3_data["date"].dt.year
    d3_data["nyd"] = None
    new_year_indices = d3_data.index[(d3_data["date"].dt.day == 1) & (d3_data["date"].dt.month == 1)]
    for i, new_year_index in enumerate(new_year_indices):
        d3_data.loc[new_year_index, "nyd"] = i

    d3_data.insert(0, "Unnamed: 0", range(len(d3_data)))
    d3_data["date"] = d3_data["date"].dt.strftime("%Y-%m-%d")
    return d3_data


def write_json(d3_data: pd.DataFrame, output_json: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(d3_data.to_json(orient="records", double_precision=10) + "\n")


def main() -> int:
    args = parse_args()
    df_date = load_daily_harmed(args.input_csv)
    lengths = future_dataframe_lengths(df_date, args.forecast_days)

    print(
        f"Loaded {len(df_date):,} daily rows from {df_date['date'].min().date()} "
        f"through {df_date['date'].max().date()}."
    )
    print(f"Years to model: {', '.join(str(year) for year in lengths)}")
    print(f"Output JSON: {args.output_json}")

    if args.dry_run:
        return 0

    d3_data = build_forecast_data(
        df_date,
        forecast_days=args.forecast_days,
        changepoint_prior_scale=args.changepoint_prior_scale,
    )
    d3_data = prepare_for_visualization(d3_data)
    write_json(d3_data, args.output_json)

    print(f"Wrote {len(d3_data):,} rows to {args.output_json}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
