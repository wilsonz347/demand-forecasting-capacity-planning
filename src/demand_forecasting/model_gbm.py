"""Gradient boosting (XGBoost), one model per BA, scored next to ridge and the baselines.

Same inputs, monthly refits, and scorer as model_linear.py; only the model changes.
Trees split raw numbers, so no encoding or scaling is needed. The test split is dropped
on load. Run with `python -m demand_forecasting.model_gbm`.
"""

import pandas as pd
from xgboost import XGBRegressor

from demand_forecasting import baselines, model_linear
from demand_forecasting.load import ROOT

# XGBoost's defaults, except these two. Not tuned yet (tuning uses validation only).
# Note: it is fit on squared error but scored on MAE/MAPE, like ridge; revisit when tuning.
SETTINGS = {
    "n_estimators": 300,  # number of trees added one after another
    "learning_rate": 0.05,  # how much of each tree's correction is kept
}

OUT_DIR = ROOT / "data" / "derived" / "model_gbm"


def make_model() -> XGBRegressor:
    """A fresh, unfitted XGBoost model with SETTINGS."""
    return XGBRegressor(**SETTINGS)


def main() -> None:
    df = pd.read_parquet(model_linear.FEATURES_PATH)
    df = df[df["split"] != "test"]  # the test year stays untouched
    df = baselines.add_baselines(df)

    # Both models go through the same loop, so the comparison changes only the model.
    df["linear"] = model_linear.predict_validation(df)
    df["gbm"] = model_linear.predict_validation(df, make=make_model)

    # Score everything in one call, so every method is judged on the same hours.
    scores = baselines.score(df, [*baselines.METHODS, "linear", "gbm"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scores.to_csv(OUT_DIR / "validation_scores.csv", index=False)
    print(scores.pivot(index="ba", columns="method", values="mape_pct").round(2))


if __name__ == "__main__":
    main()
