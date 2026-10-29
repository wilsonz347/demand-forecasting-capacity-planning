import pandas as pd

from demand_forecasting import build_dataset as bd


def test_split_boundaries():
    stamps = pd.Series(pd.to_datetime([
        "2024-10-24 00:00",  # last train hour
        "2024-10-24 01:00",  # first validation hour
        "2025-10-24 00:00",  # last validation hour
        "2025-10-24 01:00",  # first test hour
    ], utc=True))
    assert bd.assign_split(stamps).tolist() == ["train", "validation", "validation", "test"]


def test_test_period_is_one_full_year():
    last = pd.Timestamp("2026-10-24 00:00", tz="UTC")
    hours = pd.Series(pd.date_range(bd.TEST_FIRST_END, last, freq="h"))
    assert (bd.assign_split(hours) == "test").sum() == 8760


def test_build_keeps_selected_bas_inside_window():
    stamps = pd.to_datetime(["2021-01-01 00:00", "2022-06-01 12:00", "2026-10-24 01:00"], utc=True)
    df = pd.DataFrame({
        "ba": ["PJM", "PJM", "PJM"] + ["XXX"] * 3,
        "region": ["MIDA"] * 3 + ["SE"] * 3,
        "utc_end": list(stamps) * 2,
        "demand_mw": 1.0, "forecast_mw": 1.0, "source_file": "f.csv",
    })
    out = bd.build(df, ["PJM"])
    assert out["ba"].tolist() == ["PJM"]  # other BA dropped; both out-of-window hours dropped
    assert list(out.columns) == ["ba", "region", "utc_end", "demand_mw", "forecast_mw", "split"]
