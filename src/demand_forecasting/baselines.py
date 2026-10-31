"""Score the three baselines on the validation year, per BA.

Baselines:
- last_week: demand at the same hour 7 days earlier.
- week_avg: average of the same hour 1, 2, 3, and 4 weeks earlier.
- operator: the operator's own day-ahead forecast.

Every input is at least 7 days old, so all of them respect the 6 p.m. day-before cutoff.
"Last week" means 168 hours in UTC, so for about a week after each clock change it is one
local hour off. Test rows are dropped on load, and values are screened first.
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
    """Keep values that are present and > 0; everything else becomes NaN."""
    return values.where(values > 0)


def lagged_demand(df: pd.DataFrame, lag: pd.Timedelta) -> pd.Series:
    """Valid demand of the same BA exactly `lag` earlier, lined up with df's rows.

    NaN where that earlier hour is missing or invalid. It looks up (ba, utc_end - lag)
    directly instead of shifting rows, so gaps in the data cannot misalign anything.
    """
    # Table of demand, looked up by (BA, hour).
    demand_by_hour = pd.Series(
        valid(df["demand_mw"]).to_numpy(),
        index=[df["ba"], df["utc_end"]],
    )

    # For every row, ask: what was this BA's demand `lag` earlier?
    earlier = demand_by_hour.reindex([df["ba"], df["utc_end"] - lag])

    return pd.Series(earlier.to_numpy(), index=df.index)


def add_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with one forecast column per baseline METHOD."""
    # Demand 1, 2, 3, and 4 weeks earlier.
    weeks_back = [lagged_demand(df, k * WEEK) for k in range(1, N_WEEKS + 1)]

    # The average skips missing weeks; it is NaN only if all four are missing.
    week_average = pd.concat(weeks_back, axis=1).mean(axis=1)

    return df.assign(
        last_week=weeks_back[0],
        week_avg=week_average,
        operator=valid(df["forecast_mw"]),
    )


def score(df: pd.DataFrame, methods: list[str] = METHODS) -> pd.DataFrame:
    """MAE (MW) and MAPE (%) per BA and method, on validation hours only.

    An hour is scored only if actual demand is valid and every method has a forecast,
    so all methods are judged on exactly the same hours.
    Returns ba, method, hours, mae_mw, mape_pct.
    """
    rows = df[df["split"] == "validation"].copy()
    rows["actual"] = valid(rows["demand_mw"])
    rows = rows.dropna(subset=["actual", *methods])

    # Long format: one row per (hour, method), so one calculation covers every method.
    long = rows.melt(
        id_vars=["ba", "actual"],
        value_vars=methods,
        var_name="method",
        value_name="forecast",
    )
    long["abs_error"] = (long["forecast"] - long["actual"]).abs()
    long["pct_error"] = 100 * long["abs_error"] / long["actual"]

    scores = long.groupby(["ba", "method"], observed=True).agg(
        hours=("abs_error", "size"),
        mae_mw=("abs_error", "mean"),
        mape_pct=("pct_error", "mean"),
    )
    return scores.reset_index()


def main() -> None:
    df = pd.read_parquet(DATASET_PATH)
    df = df[df["split"] != "test"]
    df, spikes = screen(df)

    scores = score(add_baselines(df))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scores.to_csv(OUT_DIR / "validation_scores.csv", index=False)
    spikes.to_csv(OUT_DIR / "spikes_removed.csv", index=False)

    print("Spikes removed (train + validation):")
    print(spikes.to_string(index=False), end="\n\n")
    print(scores.pivot(index="ba", columns="method", values="mape_pct").round(2))


if __name__ == "__main__":
    main()
