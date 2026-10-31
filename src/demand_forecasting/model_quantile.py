"""Demand ranges: XGBoost that forecasts several percentiles of demand at once.

The capacity decision needs a percentile, not the average: with a shortfall cost 4 times
the surplus cost, the best amount to commit is the 80th percentile, 4 / (4 + 1).
This model forecasts the 5th to 95th percentiles in steps of 5, with the same inputs,
monthly refits, and training cutoff as the other models.

It is checked two ways on validation:
- quantile (pinball) loss: the standard score for percentile forecasts (lower is better);
- coverage: does the 10-90% range contain actual demand about 80% of the time, and the
  5-95% range about 90%?

The test split is dropped on load. Run with `python -m demand_forecasting.model_quantile`.
"""

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from demand_forecasting import baselines, model_gbm, model_linear
from demand_forecasting.load import ROOT

# Percentiles to forecast: 0.05, 0.10, ..., 0.95.
QUANTILES = [round(float(q), 2) for q in np.arange(0.05, 0.96, 0.05)]
QUANTILE_COLUMNS = [f"q{round(q * 100):02d}" for q in QUANTILES]  # "q05", "q10", ...

# Ranges to check: (lower percentile, upper percentile) -> the share it should contain.
RANGES = {("q10", "q90"): 0.80, ("q05", "q95"): 0.90}

OUT_DIR = ROOT / "data" / "derived" / "model_quantile"


def make_model() -> XGBRegressor:
    """A fresh XGBoost model that forecasts every percentile in QUANTILES at once.

    Same tree settings as model_gbm; only the loss changes, to the quantile loss.
    """
    return XGBRegressor(
        objective="reg:quantileerror",
        quantile_alpha=QUANTILES,
        **model_gbm.SETTINGS,
    )


def fix_crossing(percentiles: pd.DataFrame) -> pd.DataFrame:
    """Sort each row so the percentiles never cross (the 10th can't be above the 20th).

    Each percentile is learned separately, so small crossings can happen.
    """
    sorted_values = np.sort(percentiles.to_numpy(), axis=1)
    return pd.DataFrame(sorted_values, index=percentiles.index, columns=percentiles.columns)


def quantile_loss(actual: pd.Series, forecast: pd.Series, q: float) -> pd.Series:
    """Quantile (pinball) loss of one percentile forecast, per row.

    Being under costs q per MW, being over costs (1 - q) per MW. So a 90th percentile is
    punished 9 times more for being too low than too high, which pushes it up to where
    demand is below it 90% of the time.
    """
    error = actual - forecast  # positive: the forecast was too low

    too_low_cost = q * error
    too_high_cost = (q - 1) * error  # error is negative here, so this is positive

    loss = np.where(error >= 0, too_low_cost, too_high_cost)
    return pd.Series(loss, index=actual.index)


def score_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """Per BA on validation: mean quantile loss (over all QUANTILES) and range coverage.

    Scored hours: valid actual demand and every percentile present.
    Returns ba, hours, quantile_loss_mw, and one coverage column per RANGES entry, e.g.
    coverage_q10_q90 (should be near 0.80).
    """
    rows = df[df["split"] == "validation"].copy()
    rows["actual"] = baselines.valid(rows["demand_mw"])
    rows = rows.dropna(subset=["actual", *QUANTILE_COLUMNS])

    # Average the loss over all percentiles, for each hour.
    losses = [
        quantile_loss(rows["actual"], rows[column], q)
        for q, column in zip(QUANTILES, QUANTILE_COLUMNS)
    ]
    rows["quantile_loss_mw"] = pd.concat(losses, axis=1).mean(axis=1)

    # 1 if the actual fell inside the range, else 0. Its average is the coverage.
    coverage_columns = []
    for low, high in RANGES:
        column = f"coverage_{low}_{high}"
        inside = (rows[low] <= rows["actual"]) & (rows["actual"] <= rows[high])
        rows[column] = inside.astype(float)
        coverage_columns.append(column)

    by_ba = rows.groupby("ba", observed=True)
    scores = by_ba[["quantile_loss_mw", *coverage_columns]].mean()
    scores.insert(0, "hours", by_ba.size())

    return scores.reset_index()


def main() -> None:
    df = pd.read_parquet(model_linear.FEATURES_PATH)
    df = df[df["split"] != "test"]  # the test year stays untouched

    percentiles = model_linear.predict_validation(df, make=make_model, outputs=QUANTILE_COLUMNS)
    df[QUANTILE_COLUMNS] = fix_crossing(percentiles)

    scores = score_ranges(df)

    # Save the forecasts too: the capacity decision step reads them.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    keep = ["ba", "utc_end", "local_date", "split", "demand_mw", "forecast_mw", *QUANTILE_COLUMNS]
    df.loc[df["split"] == "validation", keep].to_parquet(OUT_DIR / "validation_percentiles.parquet")
    scores.to_csv(OUT_DIR / "validation_scores.csv", index=False)

    print(scores.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
