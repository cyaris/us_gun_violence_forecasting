#!/usr/bin/env python3
"""Regenerate the Svelte forecast data from Gun Violence Archive exports."""

import argparse
import logging
from pathlib import Path

import pandas as pd
from prophet import Prophet

from utils import initialize_logger

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_CSV: Path = REPO_ROOT / "backend/all-shootings-2014-2023.csv"
DEFAULT_OUTPUT_JSON: Path = REPO_ROOT / "svelte/src/lib/static/data.json"

logger = initialize_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the US gun violence daily harmed-victim forecast data JSON " "used by the Svelte visualization."
        )
    )
    parser.add_argument(
        "--input-csv",
        default=DEFAULT_INPUT_CSV,
        help=f"GVA combined CSV to read. Defaults to {DEFAULT_INPUT_CSV}.",
        type=Path,
    )
    parser.add_argument(
        "--output-json",
        default=DEFAULT_OUTPUT_JSON,
        help=f"JSON file to update. Defaults to {DEFAULT_OUTPUT_JSON}.",
        type=Path,
    )
    parser.add_argument(
        "--forecast-days",
        default=365,
        help="Number of future daily predictions to append after the final observed date.",
        type=int,
    )
    parser.add_argument(
        "--changepoint-prior-scale", default=0.5, help="Prophet changepoint_prior_scale value.", type=float
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and summarize the source CSV without fitting Prophet or writing JSON.",
    )

    return parser.parse_args()


def load_daily_harmed(input_csv: Path) -> pd.DataFrame:
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    incidents = pd.read_csv(input_csv, usecols=["Incident_Date", "Victims_Injured", "Victims_Killed"])
    incidents["date"] = pd.to_datetime(incidents["Incident_Date"])
    incidents["num_harmed"] = pd.to_numeric(incidents["Victims_Killed"], errors="coerce").fillna(0) + pd.to_numeric(
        incidents["Victims_Injured"], errors="coerce"
    ).fillna(0)

    daily = incidents.groupby("date", as_index=False)["num_harmed"].sum()
    all_dates = pd.DataFrame({"date": pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")})
    daily = all_dates.merge(daily, how="left", on="date")
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
            lengths[int(year)] = (
                len(pd.period_range(next_year_dates.min(), max_observed_date, freq="D")) + forecast_days
            )

    return lengths


def build_forecast_data(df_date: pd.DataFrame, forecast_days: int, changepoint_prior_scale: float) -> pd.DataFrame:
    model_input = df_date.rename(columns={"date": "ds", "num_harmed": "y"})
    lengths = future_dataframe_lengths(df_date, forecast_days)
    df: pd.DataFrame | None = None

    logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
    logging.getLogger("prophet").setLevel(logging.WARNING)

    for year in df_date["date"].dt.year.drop_duplicates():
        year = int(year)

        logger.info(f"Fitting Prophet model through {year}...")

        harmed_prophet = Prophet(
            changepoint_prior_scale=changepoint_prior_scale, daily_seasonality=True, yearly_seasonality=True
        )
        harmed_prophet.fit(model_input[model_input["ds"].dt.year <= year])

        harmed_forecast = harmed_prophet.make_future_dataframe(freq="D", periods=lengths[year])
        harmed_forecast = harmed_prophet.predict(harmed_forecast)

        pred_col = f"pred_{year}"
        trend_col = f"yearly_trend_calc_{year}"

        harmed_forecast[trend_col] = harmed_forecast["yhat"] - harmed_forecast["yhat"].shift(periods=365)
        harmed_forecast = harmed_forecast.rename(columns={"ds": "date", "yhat": pred_col})

        if df is None:
            df = harmed_forecast[["date", pred_col]].merge(df_date, how="outer", on="date")
            df = harmed_forecast[["date", trend_col]].merge(df, how="outer", on="date")
        else:
            df = harmed_forecast[["date", pred_col]].merge(df, how="outer", on="date")
            df = harmed_forecast[["date", trend_col]].merge(df, how="outer", on="date")

    if df is None:
        raise ValueError("No yearly models were fit because the daily dataset is empty.")

    return df


def prepare_for_visualization(df: pd.DataFrame) -> pd.DataFrame:
    df = df.reset_index()

    df["non_observation"] = None
    first_future_index = df.index[df["num_harmed"].isna()].min()
    if pd.notna(first_future_index):
        df.loc[df["index"] >= first_future_index, "non_observation"] = 1

    df["num_harmed"] = pd.Series(
        [None if pd.isna(value) else int(value) for value in df["num_harmed"]], dtype=object, index=df.index
    )

    df["year"] = df["date"].dt.year

    df.insert(0, "Unnamed: 0", range(len(df)))
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    return df


def write_json(df: pd.DataFrame, output_json: Path) -> None:
    output_json.parent.mkdir(exist_ok=True, parents=True)
    output_json.write_text(df.to_json(double_precision=10, orient="records") + "\n")


def main() -> int:
    args = parse_args()
    df_date = load_daily_harmed(args.input_csv)

    logger.info(
        f"Loaded {len(df_date):,} daily rows from {df_date['date'].min().date()} "
        f"through {df_date['date'].max().date()}."
    )
    logger.info(
        f"Years to model: {', '.join(str(year) for year in future_dataframe_lengths(df_date, args.forecast_days))}"
    )
    logger.info(f"Output JSON: {args.output_json}")

    if args.dry_run:
        return 0

    df = build_forecast_data(
        df_date, changepoint_prior_scale=args.changepoint_prior_scale, forecast_days=args.forecast_days
    )
    df = prepare_for_visualization(df)
    write_json(df, args.output_json)

    logger.info(f"Wrote {len(df):,} rows to {args.output_json}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        logger.error(str(error))
        raise SystemExit(1)
