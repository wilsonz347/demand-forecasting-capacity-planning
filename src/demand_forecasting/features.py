"""Model inputs for each BA-hour, using only what is known at 6 p.m. local on the day before.

Three groups of inputs:
- calendar: hour, weekday, month, holiday;
- weather (forecast): heating and cooling degrees, plus dewpoint;
- past demand: 2 days earlier, 7 days earlier, and at the 6 p.m. cutoff.

Values are screened first, so invalid past demand is NaN and never used.
Run with `python -m demand_forecasting.features` to write data/derived/features.parquet.
"""

import holidays
import pandas as pd

from demand_forecasting import baselines
from demand_forecasting.build_dataset import TIMEZONES
from demand_forecasting.load import ROOT
from demand_forecasting.screening import screen
from demand_forecasting.weather import OUT_PATH as WEATHER_PATH

COMFORT_C = 18.0  # below this, demand rises with heating; above it, with cooling
CUTOFF_LOCAL_HOUR = 18  # inputs for day D use data up to 6 p.m. local on D-1
OUT_PATH = ROOT / "data" / "derived" / "features.parquet"


def local_time(df: pd.DataFrame) -> pd.Series:
    """Each row's hour-ending time on its BA's local clock (without a time zone)."""
    clock = pd.Series(pd.NaT, index=df.index, dtype="datetime64[us]")

    for name, zone in TIMEZONES.items():
        rows = df["ba"] == name
        clock[rows] = df.loc[rows, "utc_end"].dt.tz_convert(zone).dt.tz_localize(None)

    return clock


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Add hour (0-23, by when the hour starts), weekday (0 = Monday), month, is_holiday."""
    # Label hours by their start, so the hour ending 01:00 is hour 0.
    hour_start = local_time(df) - pd.Timedelta(hours=1)

    # U.S. federal holidays (including observed days) for every year in the data.
    dates = pd.to_datetime(df["local_date"])
    years = range(dates.dt.year.min(), dates.dt.year.max() + 1)
    us_holidays = holidays.US(years=years)

    return df.assign(
        hour=hour_start.dt.hour,
        weekday=hour_start.dt.day_of_week,
        month=hour_start.dt.month,
        is_holiday=df["local_date"].isin(us_holidays),
    )


def add_weather_terms(df: pd.DataFrame) -> pd.DataFrame:
    """Split temperature into degrees of cooling and of heating, around COMFORT_C.

    Demand rises both when it is hot and when it is cold. Two separate inputs let a
    linear model learn both sides of that U-shape.
    """
    return df.assign(
        cooling_c=(df["temp_c"] - COMFORT_C).clip(lower=0),
        heating_c=(COMFORT_C - df["temp_c"]).clip(lower=0),
    )


def add_lags(df: pd.DataFrame) -> pd.DataFrame:
    """Add past-demand inputs, each known by the cutoff for day D.

    - demand_2d: same hour 48 h earlier (always before the cutoff).
    - demand_7d: same hour 168 h earlier.
    - demand_cutoff: demand in the hour ending 6 p.m. local on D-1, the latest known level.
    """
    # Table of each BA's demand at 6 p.m. local, by date. Keeping only that hour also
    # avoids the repeated 1 a.m. on fall-back days, which would make duplicate keys.
    clock = local_time(df)
    is_six_pm = (clock.dt.hour == CUTOFF_LOCAL_HOUR) & (clock.dt.minute == 0)
    six_pm_demand = pd.Series(
        baselines.valid(df.loc[is_six_pm, "demand_mw"]).to_numpy(),
        index=[df.loc[is_six_pm, "ba"], clock[is_six_pm].dt.date],
    )

    # For every row, look up 6 p.m. on the day before its local date.
    day_before = pd.to_datetime(df["local_date"]) - pd.Timedelta(days=1)
    demand_at_cutoff = six_pm_demand.reindex([df["ba"], day_before.dt.date]).to_numpy()

    return df.assign(
        demand_2d=baselines.lagged_demand(df, pd.Timedelta(hours=48)),
        demand_7d=baselines.lagged_demand(df, pd.Timedelta(hours=168)),
        demand_cutoff=demand_at_cutoff,
    )


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Screen values, then add calendar, weather, and past-demand inputs."""
    df, _ = screen(df)
    df = add_calendar(df)
    df = add_weather_terms(df)
    df = add_lags(df)
    return df


def main() -> None:
    features = build_features(pd.read_parquet(WEATHER_PATH))
    features.to_parquet(OUT_PATH, index=False)

    print(f"Wrote {len(features):,} rows to {OUT_PATH}")
    print("Share missing per column:")
    print(features.drop(columns=["split"]).isna().mean().round(4).to_string())


if __name__ == "__main__":
    main()
