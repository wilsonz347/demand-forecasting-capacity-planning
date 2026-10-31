"""First model: regularized linear regression (ridge), one per BA, scored on validation.

Validation restarts monthly (brief, "Splits"): for each block of about a month, the model
is fit on every earlier day (train plus earlier validation), then predicts the block.
It is scored against the baselines on exactly the same hours. The test split is dropped
on load. Run with `python -m demand_forecasting.model_linear`.
"""

import datetime as dt

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from demand_forecasting import baselines
from demand_forecasting.build_dataset import VALIDATION_FIRST_DATE
from demand_forecasting.features import OUT_PATH as FEATURES_PATH
from demand_forecasting.load import ROOT

CATEGORICAL = ["hour", "weekday", "month"]
NUMERIC = ["is_holiday", "cooling_c", "heating_c", "dewpoint_c",
           "demand_2d", "demand_7d", "demand_cutoff"]
ALPHA = 1.0  # ridge strength; fixed for now (tuning comes later, on validation only)
N_BLOCKS = 12  # validation blocks of one month each, starting at VALIDATION_FIRST_DATE
OUT_DIR = ROOT / "data" / "derived" / "model_linear"


def make_model():
    """One-hot calendar + scaled numbers -> ridge. Same columns for every fit."""
    return make_pipeline(
        ColumnTransformer([
            ("calendar", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
            ("numbers", StandardScaler(), NUMERIC),
        ]),
        Ridge(alpha=ALPHA),
    )


def block_starts() -> list:
    """First local date of each validation block: Oct 24, Nov 24, ... (N_BLOCKS of them)."""
    starts = pd.date_range(VALIDATION_FIRST_DATE, periods=N_BLOCKS, freq=pd.DateOffset(months=1))
    return [d.date() for d in starts]


def has_inputs(df: pd.DataFrame) -> pd.Series:
    """Rows with every input present (what a forecast needs; demand is not known yet)."""
    return df[CATEGORICAL + NUMERIC].notna().all(axis=1)


def usable(df: pd.DataFrame) -> pd.Series:
    """Rows a model can learn from: every input present and valid demand."""
    return has_inputs(df) & baselines.valid(df["demand_mw"]).notna()


def training_rows(df: pd.DataFrame, block_start) -> pd.DataFrame:
    """Usable rows dated at least two days before block_start.

    The block's first day is forecast at 6 p.m. on the day before, when that day's evening
    demand is not yet known. Dropping the whole day before keeps training to known data.
    """
    return df[usable(df) & (df["local_date"] < block_start - dt.timedelta(days=1))]


def predict_validation(df: pd.DataFrame) -> pd.Series:
    """Ridge forecast for every validation row (NaN where an input is missing).

    For each BA and each block [start, next start): fit make_model() on
    training_rows(that BA, start), then predict the block's rows that have all inputs.
    The last block runs to the end of the data.
    """
    out = pd.Series(np.nan, index=df.index)
    starts = block_starts()
    for _, rows in df.groupby("ba", observed=True):
        for start, end in zip(starts, starts[1:] + [None]):
            train = training_rows(rows, start)
            model = make_model().fit(train[CATEGORICAL + NUMERIC], train["demand_mw"])
            in_block = rows["local_date"] >= start
            if end is not None:
                in_block &= rows["local_date"] < end
            target = rows[in_block & has_inputs(rows)]
            out.loc[target.index] = model.predict(target[CATEGORICAL + NUMERIC])
    return out


def main() -> None:
    df = pd.read_parquet(FEATURES_PATH)
    df = baselines.add_baselines(df[df["split"] != "test"])
    df["linear"] = predict_validation(df)
    scores = baselines.score(df, [*baselines.METHODS, "linear"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scores.to_csv(OUT_DIR / "validation_scores.csv", index=False)
    print(scores.pivot(index="ba", columns="method", values="mape_pct").round(2))


if __name__ == "__main__":
    main()
