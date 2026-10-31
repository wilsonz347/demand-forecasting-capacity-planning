import datetime as dt

import numpy as np
import pandas as pd

from demand_forecasting import features as ft
from demand_forecasting.build_dataset import local_date


def frame(ba, start_utc, hours, demand=None):
    stamps = pd.date_range(start_utc, periods=hours, freq="h", tz="UTC")
    df = pd.DataFrame({"ba": ba, "utc_end": stamps,
                       "demand_mw": np.arange(hours, dtype=float) + 1 if demand is None else demand,
                       "temp_c": 20.0})
    df["local_date"] = local_date(df["ba"], df["utc_end"])
    return df


def test_calendar_uses_local_hour_starting_at_zero():
    # PJM in January is UTC-5: the hour ending 06:00 UTC is local 00:00-01:00, hour 0.
    df = ft.add_calendar(frame("PJM", "2025-01-06 06:00", 1))
    row = df.iloc[0]
    assert (row["hour"], row["weekday"], row["month"]) == (0, 0, 1)  # Monday, January


def test_holiday_flag():
    # July 4, 2025 (Friday), PJM local noon = 16:00 UTC (EDT).
    assert ft.add_calendar(frame("PJM", "2025-07-04 16:00", 1))["is_holiday"].iloc[0]
    assert not ft.add_calendar(frame("PJM", "2025-07-07 16:00", 1))["is_holiday"].iloc[0]


def test_weather_terms_split_at_comfort_temperature():
    df = pd.DataFrame({"temp_c": [10.0, 18.0, 30.0]})
    out = ft.add_weather_terms(df)
    assert out["heating_c"].tolist() == [8.0, 0.0, 0.0]
    assert out["cooling_c"].tolist() == [0.0, 0.0, 12.0]


def test_cutoff_demand_is_6pm_local_the_day_before():
    df = frame("PJM", "2025-01-01 06:00", 72)  # local Jan 1 00:00 onward, EST
    out = ft.add_lags(df)
    # Every hour of local Jan 2 sees the demand of the hour ending 18:00 local on Jan 1
    # (= 23:00 UTC Jan 1, the 18th row, value 18).
    jan2 = out[out["local_date"] == dt.date(2025, 1, 2)]
    assert (jan2["demand_cutoff"] == 18.0).all()


def test_no_lag_reads_after_the_cutoff():
    df = frame("PJM", "2025-01-01 06:00", 24 * 9)
    changed = df.copy()
    # Change everything after 6 p.m. local on Jan 8 (hour ending 23:00 UTC).
    late = changed["utc_end"] > pd.Timestamp("2025-01-08 23:00", tz="UTC")
    changed.loc[late, "demand_mw"] = 999.0
    cols = ["demand_2d", "demand_7d", "demand_cutoff"]
    jan9 = df["local_date"] == dt.date(2025, 1, 9)
    pd.testing.assert_frame_equal(ft.add_lags(df).loc[jan9, cols], ft.add_lags(changed).loc[jan9, cols])
