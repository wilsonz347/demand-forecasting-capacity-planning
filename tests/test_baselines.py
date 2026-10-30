import numpy as np
import pandas as pd
import pytest

from demand_forecasting import baselines as bl


def hourly(demand, forecast=None, split="validation", ba="PJM"):
    """One BA, hourly from 2025-01-01, with the given demand values."""
    n = len(demand)
    return pd.DataFrame({
        "ba": ba,
        "utc_end": pd.date_range("2025-01-01 01:00", periods=n, freq="h", tz="UTC"),
        "demand_mw": np.asarray(demand, dtype=float),
        "forecast_mw": 100.0 if forecast is None else np.asarray(forecast, dtype=float),
        "split": split,
    })


WEEK_H = 168


def test_last_week_is_exactly_168_hours_earlier():
    df = hourly(np.arange(1, WEEK_H + 3))  # 170 hours, values 1..170
    out = bl.add_baselines(df)
    assert np.isnan(out["last_week"].iloc[WEEK_H - 1])  # nothing a week before
    assert out["last_week"].iloc[WEEK_H] == 1.0
    assert out["last_week"].iloc[WEEK_H + 1] == 2.0


def test_lag_ignores_invalid_and_missing_rows():
    df = hourly([0.0] + [5.0] * WEEK_H)  # first hour invalid (0)
    assert np.isnan(bl.add_baselines(df)["last_week"].iloc[WEEK_H])
    # Same lookup when the earlier row is absent entirely, not just invalid.
    assert np.isnan(bl.add_baselines(df.iloc[1:])["last_week"].iloc[-1])


def test_week_avg_averages_valid_weeks_only():
    demand = np.full(4 * WEEK_H + 1, 10.0)
    demand[0], demand[WEEK_H], demand[2 * WEEK_H], demand[3 * WEEK_H] = 10, 20, -1, 30
    out = bl.add_baselines(hourly(demand))
    assert out["week_avg"].iloc[4 * WEEK_H] == pytest.approx(20.0)  # mean of 10, 20, 30


def test_baseline_never_uses_the_hour_it_forecasts():
    df = hourly(np.full(WEEK_H + 1, 10.0))
    changed = df.copy()
    changed.loc[WEEK_H, "demand_mw"] = 999.0
    assert bl.add_baselines(df).iloc[WEEK_H][bl.METHODS].equals(
        bl.add_baselines(changed).iloc[WEEK_H][bl.METHODS])


def test_score_uses_same_hours_for_every_method():
    demand = np.full(WEEK_H + 2, 100.0)
    forecast = np.full(WEEK_H + 2, 110.0)
    forecast[-1] = np.nan  # operator missing in the last hour: no method is scored on it
    df = bl.add_baselines(hourly(demand, forecast))
    scores = bl.score(df).set_index("method")
    assert (scores["hours"] == 1).all()
    assert scores.loc["operator", "mae_mw"] == 10.0
    assert scores.loc["operator", "mape_pct"] == pytest.approx(10.0)


def test_score_ignores_train_and_test():
    df = bl.add_baselines(hourly(np.full(WEEK_H + 1, 100.0), split="test"))
    assert bl.score(df).empty


def test_lag_never_crosses_between_bas():
    a = hourly(np.full(WEEK_H + 1, 10.0), ba="AAA")
    b = hourly(np.full(WEEK_H + 1, 20.0), ba="BBB")
    b["utc_end"] += pd.Timedelta(hours=WEEK_H)  # BBB starts where AAA's week ends
    out = bl.add_baselines(pd.concat([a, b], ignore_index=True))
    assert out.loc[out["ba"] == "BBB", "last_week"].iloc[:WEEK_H].isna().all()
