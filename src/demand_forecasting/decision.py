"""The project's question: does a range forecast lead to cheaper capacity decisions than the
operator's own forecast?

For each hour, a planner commits capacity before demand is known.
- Short by 1 MW costs RATIO; extra by 1 MW costs 1.
- The best amount to commit is the RATIO / (RATIO + 1) percentile of demand.

Two strategies, compared on exactly the same hours:
- range:    commit our forecast's percentile for that ratio (from model_quantile).
- operator: commit the operator's forecast plus a fixed margin per BA. The margin is the
            same percentile of the operator's past errors, from earlier years only.

Costs are assumptions, so several ratios are tested.

Caveats: the operator's forecast may be issued later than our 6 p.m. cutoff (its issue time
is undocumented), and its margin is one constant per BA.

Run with `python -m demand_forecasting.decision` for validation, or
`python -m demand_forecasting.decision test` for the one-time final run.
"""

import sys

import pandas as pd

from demand_forecasting import baselines
from demand_forecasting.features import OUT_PATH as FEATURES_PATH
from demand_forecasting.load import ROOT
from demand_forecasting.model_quantile import OUT_DIR as QUANTILE_DIR

# Shortfall cost per MW, with surplus cost = 1. Each maps to a percentile we forecast.
RATIOS = {1: "q50", 3: "q75", 9: "q90", 19: "q95"}  # e.g. 9:1 -> 9 / 10 = 90th percentile

OUT_DIR = ROOT / "data" / "derived" / "decision"


def percentile_of(ratio: int) -> float:
    """The best percentile to commit for a shortfall-to-surplus cost ratio."""
    return ratio / (ratio + 1)


def operator_margins(train: pd.DataFrame) -> pd.DataFrame:
    """Margin (MW) to add to the operator's forecast, per BA and ratio.

    For each ratio, the margin is that percentile of the operator's errors (actual minus
    forecast) over the train years. So "operator + margin" is the operator's own best
    version of the same decision, using only past information.
    Returns one row per BA, one column per ratio.
    """
    errors = pd.DataFrame({
        "ba": train["ba"].astype(str),
        "error": baselines.valid(train["demand_mw"]) - baselines.valid(train["forecast_mw"]),
    })
    errors = errors.dropna()

    margins = {}
    for ratio in RATIOS:
        margins[ratio] = errors.groupby("ba")["error"].quantile(percentile_of(ratio))

    return pd.DataFrame(margins)


def hourly_cost(actual: pd.Series, commit: pd.Series, ratio: int) -> pd.Series:
    """Cost of one hour: RATIO per MW short, 1 per MW extra."""
    shortfall = (actual - commit).clip(lower=0)
    surplus = (commit - actual).clip(lower=0)

    return ratio * shortfall + 1 * surplus


def compare(validation: pd.DataFrame, margins: pd.DataFrame) -> pd.DataFrame:
    """Average cost per hour of each strategy, per BA and ratio, on the same hours.

    Scored hours: valid actual demand, a valid operator forecast, and our percentiles.
    Returns ba, ratio, hours, range_cost, operator_cost, saving_pct
    (saving_pct > 0 means the range forecast was cheaper).
    """
    rows = validation.copy()
    rows["ba"] = rows["ba"].astype(str)
    rows["actual"] = baselines.valid(rows["demand_mw"])
    rows["operator"] = baselines.valid(rows["forecast_mw"])

    # Same hours for both strategies: everything needed must be present.
    rows = rows.dropna(subset=["actual", "operator", *RATIOS.values()])

    results = []
    for ratio, percentile in RATIOS.items():
        # What each strategy commits for every hour.
        range_commit = rows[percentile]
        operator_commit = rows["operator"] + rows["ba"].map(margins[ratio])
        if operator_commit.isna().any():  # a BA without a margin would silently drop hours
            raise ValueError(f"No operator margin for {sorted(rows.loc[operator_commit.isna(), 'ba'].unique())}")

        costs = pd.DataFrame({
            "ba": rows["ba"],
            "range_cost": hourly_cost(rows["actual"], range_commit, ratio),
            "operator_cost": hourly_cost(rows["actual"], operator_commit, ratio),
        })

        # Average cost per hour, per BA.
        by_ba = costs.groupby("ba")
        summary = by_ba[["range_cost", "operator_cost"]].mean()
        summary["hours"] = by_ba.size()
        summary["ratio"] = ratio

        results.append(summary.reset_index())

    results = pd.concat(results, ignore_index=True)

    # How much cheaper the range forecast was, in % of the operator's cost (never 0 in practice).
    difference = results["operator_cost"] - results["range_cost"]
    results["saving_pct"] = 100 * difference / results["operator_cost"]

    columns = ["ba", "ratio", "hours", "range_cost", "operator_cost", "saving_pct"]
    return results[columns]


def main(split: str = "validation") -> None:
    if split not in ("validation", "test"):
        raise ValueError(f"split must be 'validation' or 'test', not {split!r}")

    # The operator's margin may only use years before the one being scored.
    features = pd.read_parquet(FEATURES_PATH)
    earlier_years = ["train"] if split == "validation" else ["train", "validation"]
    margins = operator_margins(features[features["split"].isin(earlier_years)])

    forecasts = pd.read_parquet(QUANTILE_DIR / f"{split}_percentiles.parquet")
    results = compare(forecasts, margins)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT_DIR / f"{split}_costs.csv", index=False)

    print(f"{split}: saving of the range forecast vs operator + margin (%, positive = range cheaper):")
    print(results.pivot(index="ba", columns="ratio", values="saving_pct").round(1))


if __name__ == "__main__":
    main(*sys.argv[1:])
