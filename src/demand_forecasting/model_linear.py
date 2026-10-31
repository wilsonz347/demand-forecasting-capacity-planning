"""First model: ridge regression (a regularized linear model), one per BA.

Validation is split into 12 monthly blocks. For each block the model is fit on all
earlier days (train plus earlier validation), then predicts the block, as it would be
retrained in real use. It is scored next to the baselines on exactly the same hours.
The test split is dropped on load. Run with `python -m demand_forecasting.model_linear`.
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

# --- Inputs ------------------------------------------------------------------------------

CATEGORICAL = ["hour", "weekday", "month"]  # one-hot encoded: one column per value
NUMERIC = [  # scaled to mean 0 and spread 1
    "is_holiday",
    "cooling_c",
    "heating_c",
    "dewpoint_c",
    "demand_2d",
    "demand_7d",
    "demand_cutoff",
]
INPUTS = CATEGORICAL + NUMERIC

# --- Settings ----------------------------------------------------------------------------

ALPHA = 1.0  # ridge penalty strength; fixed for now (tuning uses validation only)
N_BLOCKS = 12  # one-month validation blocks, starting at VALIDATION_FIRST_DATE

OUT_DIR = ROOT / "data" / "derived" / "model_linear"


def make_model():
    """A fresh, unfitted ridge model: one-hot calendar and scaled numbers, then ridge.

    The encoder and scaler are inside the pipeline, so each fit learns them from its own
    training rows only.
    """
    preprocess = ColumnTransformer([
        ("calendar", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ("numbers", StandardScaler(), NUMERIC),
    ])
    return make_pipeline(preprocess, Ridge(alpha=ALPHA))


def block_starts(first_date: dt.date = VALIDATION_FIRST_DATE) -> list[dt.date]:
    """First local date of each monthly block, from first_date: Oct 24, Nov 24, and so on.

    first_date is VALIDATION_FIRST_DATE for validation, TEST_FIRST_DATE for the final test.
    """
    starts = pd.date_range(first_date, periods=N_BLOCKS, freq=pd.DateOffset(months=1))
    return [start.date() for start in starts]


def has_inputs(df: pd.DataFrame) -> pd.Series:
    """Rows with every input present: what a forecast needs (actual demand isn't known yet)."""
    return df[INPUTS].notna().all(axis=1)


def usable(df: pd.DataFrame) -> pd.Series:
    """Rows a model can learn from: every input present, and valid actual demand."""
    return has_inputs(df) & baselines.valid(df["demand_mw"]).notna()


def training_rows(df: pd.DataFrame, block_start: dt.date) -> pd.DataFrame:
    """Usable rows dated at least two days before block_start.

    The block's first day is forecast at 6 p.m. on the day before, when that day's evening
    demand is not known yet. Leaving out the whole day before keeps training to known data.
    """
    day_before_block = block_start - dt.timedelta(days=1)
    return df[usable(df) & (df["local_date"] < day_before_block)]


def predict_validation(
    df: pd.DataFrame,
    make=make_model,
    outputs: list[str] | None = None,
    first_date: dt.date = VALIDATION_FIRST_DATE,
) -> pd.Series | pd.DataFrame:
    """Forecast every validation row (NaN where an input is missing).

    `make` returns a fresh, unfitted model: ridge by default; other modules pass their own.
    For each BA and each monthly block, fit on that BA's training rows, then predict the
    block. The last block runs to the end of the data.

    Returns a Series (one forecast per row), or, if `outputs` is given, a DataFrame with
    one column per model output (used for percentile forecasts).

    first_date sets the year being forecast: validation by default, or TEST_FIRST_DATE for
    the one-time test run (then df must include the test rows).
    """
    if outputs is None:
        predictions = pd.Series(np.nan, index=df.index)
    else:
        predictions = pd.DataFrame(np.nan, index=df.index, columns=outputs)

    starts = block_starts(first_date)
    ends = starts[1:] + [None]

    for _, ba_rows in df.groupby("ba", observed=True):
        for start, end in zip(starts, ends):
            # Fit on everything known before this block.
            train = training_rows(ba_rows, start)
            model = make().fit(train[INPUTS], train["demand_mw"])

            # Predict the block's rows that have all inputs.
            in_block = ba_rows["local_date"] >= start
            if end is not None:
                in_block &= ba_rows["local_date"] < end
            block = ba_rows[in_block & has_inputs(ba_rows)]

            predictions.loc[block.index] = model.predict(block[INPUTS])

    return predictions


def main() -> None:
    df = pd.read_parquet(FEATURES_PATH)
    df = df[df["split"] != "test"]  # the test year stays untouched
    df = baselines.add_baselines(df)

    df["linear"] = predict_validation(df)
    scores = baselines.score(df, [*baselines.METHODS, "linear"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scores.to_csv(OUT_DIR / "validation_scores.csv", index=False)
    print(scores.pivot(index="ba", columns="method", values="mape_pct").round(2))


if __name__ == "__main__":
    main()
