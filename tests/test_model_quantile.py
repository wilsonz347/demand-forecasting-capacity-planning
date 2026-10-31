import datetime as dt

import numpy as np
import pandas as pd
import pytest

from demand_forecasting import model_linear as ml
from demand_forecasting import model_quantile as mq
from tests.test_model_linear import daily_frame


def test_nineteen_percentiles_from_5_to_95():
    assert len(mq.QUANTILES) == 19
    assert mq.QUANTILES[0] == 0.05 and mq.QUANTILES[-1] == 0.95
    assert mq.QUANTILE_COLUMNS[:3] == ["q05", "q10", "q15"]


def test_fix_crossing_sorts_each_row():
    crossed = pd.DataFrame({"q10": [5.0], "q50": [3.0], "q90": [9.0]})
    assert mq.fix_crossing(crossed).iloc[0].tolist() == [3.0, 5.0, 9.0]


def test_quantile_loss_punishes_being_low_more_for_a_high_percentile():
    actual = pd.Series([100.0, 100.0])
    forecast = pd.Series([90.0, 110.0])  # 10 too low, then 10 too high
    loss = mq.quantile_loss(actual, forecast, 0.9)
    assert loss.tolist() == pytest.approx([9.0, 1.0])


def test_score_ranges_counts_coverage():
    df = pd.DataFrame({"ba": "PJM", "split": "validation", "demand_mw": [50.0, 100.0, 150.0]})
    for column in mq.QUANTILE_COLUMNS:
        df[column] = 100.0
    df["q05"] = df["q10"] = 80.0
    df["q90"] = df["q95"] = 120.0
    scores = mq.score_ranges(df).iloc[0]
    assert scores["hours"] == 3
    assert scores["coverage_q10_q90"] == pytest.approx(1 / 3)  # only 100 is inside


def test_learned_ranges_are_roughly_calibrated():
    # Demand = 100 + 10 * cooling + noise, so the 10-90% range should hold about 80%.
    # Untuned quantile trees tend to give ranges a bit too narrow (about 67% here), so
    # this only checks the ranges are sensible; real calibration is checked on validation.
    df = daily_frame(dt.date(2023, 10, 24), 730)
    df["demand_mw"] += np.random.default_rng(2).normal(0, 5, len(df))
    pred = ml.predict_validation(df, make=mq.make_model, outputs=mq.QUANTILE_COLUMNS)
    val = df["local_date"] >= dt.date(2024, 10, 24)

    # Before any sorting, the model's columns must already run low to high.
    assert (pred.loc[val, "q95"] >= pred.loc[val, "q05"]).mean() > 0.95
    actual = df.loc[val, "demand_mw"]
    inside = (pred.loc[val, "q10"] <= actual) & (actual <= pred.loc[val, "q90"])
    assert 0.6 <= inside.mean() <= 0.95
