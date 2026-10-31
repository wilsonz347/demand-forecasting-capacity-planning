import datetime as dt

import numpy as np
import pandas as pd

from demand_forecasting import model_linear as ml


def daily_frame(first, days, ba="PJM"):
    """One row per day (enough for the model logic), with demand = 100 + 10 * cooling_c."""
    dates = [first + dt.timedelta(days=i) for i in range(days)]
    rng = np.random.default_rng(0)
    cooling = rng.uniform(0, 10, days)
    df = pd.DataFrame({
        "ba": ba, "local_date": dates,
        "hour": 12, "weekday": [d.weekday() for d in dates], "month": [d.month for d in dates],
        "is_holiday": False, "cooling_c": cooling, "heating_c": 0.0, "dewpoint_c": 10.0,
        "demand_2d": 100.0, "demand_7d": 100.0, "demand_cutoff": 100.0,
    })
    df["demand_mw"] = 100 + 10 * df["cooling_c"]
    return df


def test_twelve_monthly_blocks_from_validation_start():
    starts = ml.block_starts()
    assert len(starts) == 12
    assert starts[0] == dt.date(2024, 10, 24) and starts[-1] == dt.date(2025, 9, 24)


def test_training_rows_stop_two_days_before_the_block():
    # Nov 23's evening is not known at 6 p.m. on Nov 23, when Nov 24 is forecast.
    df = daily_frame(dt.date(2024, 9, 1), 120)
    rows = ml.training_rows(df, dt.date(2024, 11, 24))
    assert rows["local_date"].max() == dt.date(2024, 11, 22)


def test_training_rows_skip_unusable():
    df = daily_frame(dt.date(2024, 9, 1), 10)
    df.loc[0, "demand_mw"] = 0.0  # invalid demand
    df.loc[1, "demand_7d"] = np.nan  # missing input
    assert len(ml.training_rows(df, dt.date(2025, 1, 1))) == 8


def test_predict_validation_learns_a_simple_relation():
    df = daily_frame(dt.date(2023, 10, 24), 730)  # two years: train, then validation
    pred = ml.predict_validation(df)
    val = df["local_date"] >= dt.date(2024, 10, 24)
    assert pred[~val].isna().all()  # only validation rows are predicted
    assert np.allclose(pred[val], df.loc[val, "demand_mw"], rtol=0.02)


def test_predicts_even_when_actual_demand_is_missing():
    # A forecast needs only the inputs; the actual is unknown at forecast time.
    df = daily_frame(dt.date(2023, 10, 24), 730)
    df.loc[df.index[-1], "demand_mw"] = np.nan
    assert not np.isnan(ml.predict_validation(df).iloc[-1])
