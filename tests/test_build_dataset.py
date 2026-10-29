import datetime as dt

import pandas as pd
import pytest

from demand_forecasting import build_dataset as bd


def utc(*stamps):
    return pd.Series(pd.to_datetime(list(stamps), utc=True))


def test_local_date_follows_ba_zone_and_hour_24():
    # Hour ending local midnight belongs to the previous day (EIA "Hour Number 24").
    ba = pd.Series(["PJM", "PJM", "CISO"])
    stamps = utc("2025-01-02 05:00", "2025-01-02 06:00", "2025-01-02 06:00")
    assert bd.local_date(ba, stamps).tolist() == [
        dt.date(2025, 1, 1), dt.date(2025, 1, 2), dt.date(2025, 1, 1)]


def test_miso_uses_standard_time_all_year():
    # 2021-07-01 05:00 UTC is 01:00 EDT on Jul 1, but 00:00 EST, so EIA dates it Jun 30.
    stamps = utc("2021-07-01 05:00")
    assert bd.local_date(pd.Series(["MISO"]), stamps).tolist() == [dt.date(2021, 6, 30)]
    assert bd.local_date(pd.Series(["PJM"]), stamps).tolist() == [dt.date(2021, 7, 1)]


def test_fall_back_day_has_25_hours():
    # Local 2025-11-02 in New York runs 04:00 UTC (00:00 EDT) to 05:00 UTC next day (00:00 EST).
    hours = pd.Series(pd.date_range("2025-11-02 05:00", periods=25, freq="h", tz="UTC"))
    assert (bd.local_date(pd.Series(["PJM"] * 25), hours) == dt.date(2025, 11, 2)).all()


def test_build_rejects_ba_without_time_zone():
    df = pd.DataFrame({"ba": ["XXX"], "region": ["SE"], "utc_end": utc("2022-06-01 12:00"),
                       "demand_mw": 1.0, "forecast_mw": 1.0, "source_file": "f.csv"})
    with pytest.raises(ValueError):
        bd.build(df, ["XXX"])


def test_split_boundaries_by_local_date():
    dates = pd.Series([dt.date(2024, 10, 23), dt.date(2024, 10, 24),
                       dt.date(2025, 10, 23), dt.date(2025, 10, 24)])
    assert bd.assign_split(dates).tolist() == ["train", "validation", "validation", "test"]


def test_boundary_day_stays_whole():
    # All 24 hours of local 2025-10-24 in New York (EDT, UTC-4) are test, none validation.
    hours = pd.Series(pd.date_range("2025-10-24 05:00", periods=24, freq="h", tz="UTC"))
    dates = bd.local_date(pd.Series(["PJM"] * 24), hours)
    assert (dates == dt.date(2025, 10, 24)).all()
    assert (bd.assign_split(dates) == "test").all()


def test_build_keeps_selected_bas_and_whole_local_days():
    stamps = utc("2021-01-01 05:00",  # PJM local Dec 31, 2020: dropped
                 "2022-06-01 12:00",  # kept
                 "2026-10-24 03:00",  # PJM local Oct 23, 2026 evening: kept
                 "2026-10-24 05:00")  # PJM local Oct 24, 2026: dropped
    df = pd.DataFrame({
        "ba": ["PJM"] * 4 + ["XXX"] * 4, "region": ["MIDA"] * 4 + ["SE"] * 4,
        "utc_end": list(stamps) * 2,
        "demand_mw": 1.0, "forecast_mw": 1.0, "source_file": "f.csv",
    })
    out = bd.build(df, ["PJM"])
    assert out["utc_end"].tolist() == [stamps[1], stamps[2]]
    assert list(out.columns) == bd.COLUMNS
