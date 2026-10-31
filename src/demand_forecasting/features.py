"""Model inputs for each BA-hour, using only what is known at 6 p.m. local on the day before.

Three groups: calendar, weather (forecast), and past demand. Demand is screened first
(screening.py), so invalid past values are NaN, never used. Run with
`python -m demand_forecasting.features` to write data/derived/features.parquet.
"""

import holidays
import pandas as pd

from demand_forecasting import baselines
from demand_forecasting.build_dataset import TIMEZONES
from demand_forecasting.load import ROOT
from demand_forecasting.screening import screen
from demand_forecasting.weather import OUT_PATH as WEATHER_PATH

COMFORT_C = 18.0  # below this, demand rises with heating; above it, with cooling
CUTOFF_LOCAL_HOUR = 18  # inputs for day D: data up to 6 p.m. local on D-1
OUT_PATH = ROOT / "data" / "derived" / "features.parquet"


def local_time(df: pd.DataFrame) -> pd.Series:
    """Each row's hour-ending time in its BA's zone, as naive local clock time."""
    out = pd.Series(pd.NaT, index=df.index, dtype="datetime64[us]")
    for name, zone in TIMEZONES.items():
        rows = df["ba"] == name
        out[rows] = df.loc[rows, "utc_end"].dt.tz_convert(zone).dt.tz_localize(None)
    return out


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Add hour (0-23, by interval start), weekday (0 = Monday), month, and is_holiday."""
    start = local_time(df) - pd.Timedelta(hours=1)  # the hour ending 01:00 is hour 0
    dates = pd.to_datetime(df["local_date"])
    us_holidays = holidays.US(years=range(dates.dt.year.min(), dates.dt.year.max() + 1))
    return df.assign(
        hour=start.dt.hour,
        weekday=start.dt.day_of_week,
        month=start.dt.month,
        is_holiday=df["local_date"].isin(us_holidays),
    )


def add_weather_terms(df: pd.DataFrame) -> pd.DataFrame:
    """Add cooling_c = max(temp - COMFORT_C, 0) and heating_c = max(COMFORT_C - temp, 0)."""
    return df.assign(
        cooling_c=(df["temp_c"] - COMFORT_C).clip(lower=0),
        heating_c=(COMFORT_C - df["temp_c"]).clip(lower=0),
    )


def add_lags(df: pd.DataFrame) -> pd.DataFrame:
    """Add past-demand inputs, each known by the cutoff for day D:

    - demand_2d: same hour 48 h earlier (always before the cutoff).
    - demand_7d: same hour 168 h earlier.
    - demand_cutoff: demand in the hour ending 6 p.m. local on D-1 (the latest known level).
    """
    # Lookup of each BA's demand at 6 p.m. local, by date. Only that hour is kept, so the
    # repeated 1 a.m. on fall-back days cannot create duplicate keys.
    clock = local_time(df)
    at_cutoff = (clock.dt.hour == CUTOFF_LOCAL_HOUR) & (clock.dt.minute == 0)
    six_pm = pd.Series(
        baselines.valid(df.loc[at_cutoff, "demand_mw"]).to_numpy(),
        index=[df.loc[at_cutoff, "ba"], clock[at_cutoff].dt.date],
    )
    day_before = pd.to_datetime(df["local_date"]) - pd.Timedelta(days=1)
    return df.assign(
        demand_2d=baselines.lagged_demand(df, pd.Timedelta(hours=48)),
        demand_7d=baselines.lagged_demand(df, pd.Timedelta(hours=168)),
        demand_cutoff=six_pm.reindex([df["ba"], day_before.dt.date]).to_numpy(),
    )


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Screen values, then add calendar, weather terms, and lags."""
    df, _ = screen(df)
    return add_lags(add_weather_terms(add_calendar(df)))


def main() -> None:
    features = build_features(pd.read_parquet(WEATHER_PATH))
    features.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(features):,} rows to {OUT_PATH}")
    print(features.drop(columns=["split"]).isna().mean().round(4).to_string())


if __name__ == "__main__":
    main()
