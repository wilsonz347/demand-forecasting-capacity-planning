"""Score the three baselines on the validation year, per BA.

Baselines: same hour last week, hour-of-week average over 4 weeks, and the operator's
day-ahead forecast. Every input is at least 7 days older than the hour it forecasts, so
all of them respect the 6 p.m. day-before cutoff. Test rows are dropped on load, and
values are screened first (screening.py). "Last week" is 168 hours in UTC, so for about
a week after each clock change it is one local hour off.
Run with `python -m demand_forecasting.baselines`.
"""

import pandas as pd

from demand_forecasting.build_dataset import OUT_PATH as DATASET_PATH
from demand_forecasting.load import ROOT
from demand_forecasting.screening import screen

WEEK = pd.Timedelta(days=7)
N_WEEKS = 4
METHODS = ["last_week", "week_avg", "operator"]
OUT_DIR = ROOT / "data" / "derived" / "baselines"


def valid(values: pd.Series) -> pd.Series:
    """Values that are present and > 0; everything else becomes NaN (never used or scored)."""
    return values.where(values > 0)


def lagged_demand(df: pd.DataFrame, lag: pd.Timedelta) -> pd.Series:
    """Valid demand of the same BA exactly `lag` earlier (by UTC), aligned to df's rows.

    NaN where that earlier hour is absent or invalid. Uses a lookup by (ba, utc_end), not
    shift(), so gaps in the data cannot misalign rows.
    """
    by_hour = pd.Series(valid(df["demand_mw"]).to_numpy(), index=[df["ba"], df["utc_end"]])
    earlier = by_hour.reindex([df["ba"], df["utc_end"] - lag])
    return pd.Series(earlier.to_numpy(), index=df.index)


def add_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with one column per METHOD: its forecast for each hour.

    last_week: demand 7 days earlier. week_avg: mean of the valid values 1-4 weeks
    earlier (NaN only if all four are missing). operator: valid(forecast_mw).
    """
    weeks = [lagged_demand(df, k * WEEK) for k in range(1, N_WEEKS + 1)]
    return df.assign(
        last_week=weeks[0],
        week_avg=pd.concat(weeks, axis=1).mean(axis=1),
        operator=valid(df["forecast_mw"]),
    )


def score(df: pd.DataFrame, methods: list[str] = METHODS) -> pd.DataFrame:
    """MAE (MW) and MAPE (%) per BA and method, on validation hours only.

    Scored hours: split == "validation", valid demand, and all `methods` present, so every
    method is judged on exactly the same hours. Returns columns
    ba, method, hours, mae_mw, mape_pct.
    """
    rows = df[df["split"] == "validation"].assign(actual=lambda d: valid(d["demand_mw"]))
    rows = rows.dropna(subset=["actual", *methods])
    long = rows.melt(id_vars=["ba", "actual"], value_vars=methods,
                     var_name="method", value_name="forecast")
    long["abs_error"] = (long["forecast"] - long["actual"]).abs()
    long["pct_error"] = 100 * long["abs_error"] / long["actual"]
    return (
        long.groupby(["ba", "method"], observed=True)
        .agg(hours=("abs_error", "size"), mae_mw=("abs_error", "mean"),
             mape_pct=("pct_error", "mean"))
        .reset_index()
    )


def main() -> None:
    df = pd.read_parquet(DATASET_PATH)
    df, spikes = screen(df[df["split"] != "test"])
    scores = score(add_baselines(df))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scores.to_csv(OUT_DIR / "validation_scores.csv", index=False)
    spikes.to_csv(OUT_DIR / "spikes_removed.csv", index=False)
    print("Spikes removed (train + validation):")
    print(spikes.to_string(index=False), end="\n\n")
    print(scores.pivot(index="ba", columns="method", values="mape_pct").round(2))


if __name__ == "__main__":
    main()
