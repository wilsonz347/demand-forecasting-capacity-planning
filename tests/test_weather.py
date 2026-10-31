import datetime as dt

import numpy as np
import pandas as pd
import pytest

from demand_forecasting import weather as wx


def utc(*stamps):
    return pd.to_datetime(list(stamps), utc=True)


def test_read_station_converts_fahrenheit(tmp_path):
    f = tmp_path / "KAAA.csv"
    f.write_text("runtime,ftime,model,tmp,dpt,station\n"
                 "2025-01-01 12:00:00,2025-01-01 18:00:00,GFS,32,212,KAAA\n")
    row = wx.read_station(f).iloc[0]
    assert row["temp_c"] == pytest.approx(0.0) and row["dewpoint_c"] == pytest.approx(100.0)
    assert row["ftime"] == pd.Timestamp("2025-01-01 18:00", tz="UTC")


def test_to_hourly_draws_straight_line_within_a_run():
    run = pd.Timestamp("2025-01-01 12:00", tz="UTC")
    mos = pd.DataFrame({"runtime": run, "ftime": utc("2025-01-01 15:00", "2025-01-01 18:00"),
                        "temp_c": [30.0, 24.0], "dewpoint_c": [10.0, 10.0]})
    out = wx.to_hourly(mos).set_index("ftime")["temp_c"]
    assert out.tolist() == pytest.approx([30.0, 28.0, 26.0, 24.0])  # 15, 16, 17, 18 UTC


def test_ba_weather_weights_by_population(monkeypatch):
    monkeypatch.setattr(wx, "STATIONS", {"XX": {"KAAA": 3, "KBBB": 1}})
    run, t = pd.Timestamp("2025-01-01 12:00", tz="UTC"), pd.Timestamp("2025-01-01 18:00", tz="UTC")
    one = lambda temp: pd.DataFrame({"runtime": [run], "ftime": [t], "temp_c": [temp], "dewpoint_c": [0.0]})
    out = wx.ba_weather({"KAAA": one(10.0), "KBBB": one(20.0)})
    assert out["temp_c"].iloc[0] == pytest.approx(12.5)  # 0.75 * 10 + 0.25 * 20


def test_issue_cutoff_is_noon_utc_the_day_before():
    out = wx.issue_cutoff(pd.Series([dt.date(2025, 5, 30)]))
    assert out.iloc[0] == pd.Timestamp("2025-05-29 12:00", tz="UTC")


def test_attach_uses_latest_run_before_cutoff_and_never_a_later_one():
    # 12Z on May 29 is missing; the 06Z run must be used, never the 18Z one.
    runs = utc("2025-05-28 12:00", "2025-05-29 06:00", "2025-05-29 18:00")
    target = pd.Timestamp("2025-05-30 18:00", tz="UTC")
    weather = pd.DataFrame({"ba": "PJM", "runtime": runs, "ftime": target,
                            "temp_c": [1.0, 2.0, 3.0], "dewpoint_c": 0.0})
    dataset = pd.DataFrame({"ba": ["PJM"], "utc_end": [target], "local_date": [dt.date(2025, 5, 30)]})
    row = wx.attach_weather(dataset, weather).iloc[0]
    assert row["temp_c"] == 2.0
    assert row["weather_run"] == runs[1]


def test_read_station_drops_exact_duplicates_and_rejects_conflicts(tmp_path):
    head = "runtime,ftime,model,tmp,dpt,station\n"
    row = "2025-01-01 12:00:00,2025-01-01 18:00:00,GFS,50,40,KAAA\n"
    same = tmp_path / "same.csv"
    same.write_text(head + row + row)
    assert len(wx.read_station(same)) == 1
    clash = tmp_path / "clash.csv"
    clash.write_text(head + row + row.replace(",50,", ",51,"))
    with pytest.raises(ValueError):
        wx.read_station(clash)


def test_to_hourly_never_extrapolates_past_a_run():
    run = pd.Timestamp("2025-01-01 12:00", tz="UTC")
    mos = pd.DataFrame({"runtime": run, "ftime": utc("2025-01-01 18:00", "2025-01-01 21:00"),
                        "temp_c": [1.0, 4.0], "dewpoint_c": 0.0})
    out = wx.to_hourly(mos).dropna()
    assert out["ftime"].min() == mos["ftime"].min() and out["ftime"].max() == mos["ftime"].max()


def test_ba_weather_drops_hours_missing_at_any_station(monkeypatch):
    monkeypatch.setattr(wx, "STATIONS", {"XX": {"KAAA": 1, "KBBB": 1}})
    run = pd.Timestamp("2025-01-01 12:00", tz="UTC")
    t1, t2 = utc("2025-01-01 18:00", "2025-01-01 19:00")
    a = pd.DataFrame({"runtime": run, "ftime": [t1, t2], "temp_c": 1.0, "dewpoint_c": 0.0})
    b = pd.DataFrame({"runtime": run, "ftime": [t1], "temp_c": 1.0, "dewpoint_c": 0.0})
    assert wx.ba_weather({"KAAA": a, "KBBB": b})["ftime"].tolist() == [t1]


def test_attach_leaves_nan_when_newest_run_is_too_old():
    target = pd.Timestamp("2025-05-30 18:00", tz="UTC")
    weather = pd.DataFrame({"ba": "PJM", "runtime": utc("2025-05-27 12:00"), "ftime": target,
                            "temp_c": 1.0, "dewpoint_c": 0.0})
    dataset = pd.DataFrame({"ba": ["PJM"], "utc_end": [target], "local_date": [dt.date(2025, 5, 30)]})
    assert np.isnan(wx.attach_weather(dataset, weather)["temp_c"].iloc[0])
