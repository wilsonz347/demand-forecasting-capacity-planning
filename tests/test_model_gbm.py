import datetime as dt

import numpy as np

from demand_forecasting import model_gbm as gb
from demand_forecasting import model_linear as ml
from tests.test_model_linear import daily_frame


def test_gbm_learns_an_interaction_that_ridge_cannot():
    # Cooling adds demand only in the afternoon: an hour x weather interaction.
    df = daily_frame(dt.date(2023, 10, 24), 730)
    rng = np.random.default_rng(1)
    df["hour"] = rng.integers(0, 24, len(df))
    df["demand_mw"] = 100 + np.where(df["hour"] >= 12, 10 * df["cooling_c"], 0)
    val = df["local_date"] >= dt.date(2024, 10, 24)

    def mae(pred):
        return (pred[val] - df.loc[val, "demand_mw"]).abs().mean()

    gbm_error = mae(ml.predict_validation(df, make=gb.make_model))
    ridge_error = mae(ml.predict_validation(df))

    assert gbm_error < 3
    assert gbm_error < ridge_error / 2
