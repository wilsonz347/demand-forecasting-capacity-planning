import numpy as np
import pandas as pd
import pytest

from demand_forecasting import ba_selection as sel


def test_window_matches_protocol_hour_counts():
    hours = sel.window_hours()
    assert len(hours) == 50_928
    counts = sel.hour_year(pd.Series(hours)).value_counts().to_dict()
    assert counts == sel.EXPECTED_HOURS


def test_hour_ending_midnight_belongs_to_previous_year():
    stamp = pd.Series([pd.Timestamp("2022-01-01 00:00", tz="UTC")])
    assert sel.hour_year(stamp).iloc[0] == 2021


def test_coverage_counts_missing_zero_and_negative_as_invalid():
    stamps = pd.date_range("2021-06-01 01:00", periods=4, freq="h", tz="UTC")
    df = pd.DataFrame({
        "ba": "AAA", "region": "SE", "utc_end": stamps,
        "demand_mw": [np.nan, 0.0, -5.0, 10.0],
        "forecast_mw": [1.0, 1.0, 1.0, 1.0],
    })
    row = sel.coverage_table(df).set_index("year").loc[2021]
    assert row["rows_present"] == 4
    assert row["valid_demand_hours"] == 1
    assert row["valid_forecast_hours"] == 4
    assert row["demand_coverage"] == 1 / 8760


def ranking(regions):
    """Ranking frame with BAs B01, B02, ... in rank order."""
    n = len(regions)
    return pd.DataFrame({
        "ba": [f"B{i:02d}" for i in range(1, n + 1)],
        "region": regions,
        "mean_demand_mw": np.arange(n, 0, -1, dtype=float),
        "rank": range(1, n + 1),
    })


def test_select_takes_top_ten_when_regions_suffice():
    selected, swaps = sel.select_bas(ranking(["A", "B", "C", "D"] * 3))
    assert selected == [f"B{i:02d}" for i in range(1, 11)]
    assert swaps == []


def test_select_swaps_in_new_region():
    # Top 10 span 3 regions; B11 brings a 4th and replaces B10 (lowest rank, region has 2+).
    selected, swaps = sel.select_bas(ranking(["A", "B", "C"] * 3 + ["A", "D"]))
    assert "B11" in selected and "B10" not in selected
    assert len(swaps) == 1


def test_select_raises_when_too_few_eligible():
    with pytest.raises(ValueError):
        sel.select_bas(ranking(["A", "B", "C", "D"] * 2))


def test_select_skips_new_ba_from_covered_region():
    # B11 is in a covered region, so B12 (new region D) comes in. This case used to loop.
    selected, swaps = sel.select_bas(ranking(["A", "B", "C"] * 3 + ["A", "A", "D"]))
    assert "B12" in selected and "B11" not in selected and "B10" not in selected
    assert len(swaps) == 1


def test_select_keeps_sole_member_of_a_region():
    # B10 is region C's only member, so the swap removes B09 (region A) instead.
    selected, _ = sel.select_bas(ranking(["A", "B"] * 4 + ["A", "C", "D"]))
    assert "B10" in selected and "B11" in selected and "B09" not in selected


def test_rank_uses_valid_demand_and_drops_excluded():
    stamps = pd.date_range("2021-06-01 01:00", periods=3, freq="h", tz="UTC")
    df = pd.DataFrame({
        "ba": ["AAA"] * 3 + ["SPA"] * 3, "region": ["SE"] * 3 + ["CENT"] * 3,
        "utc_end": list(stamps) * 2,
        "demand_mw": [10.0, 0.0, -50.0, 99.0, 99.0, 99.0],
        "forecast_mw": 1.0,
    })
    coverage = pd.DataFrame({"ba": ["AAA", "SPA"], "demand_pass": True, "forecast_pass": True})
    ranked = sel.rank_eligible(coverage, df)
    assert ranked["ba"].tolist() == ["AAA"]  # SPA is excluded
    assert ranked["mean_demand_mw"].iloc[0] == 10.0  # 0 and -50 are not valid demand


def frame(ba, region, stamps, demand=1.0):
    return pd.DataFrame({"ba": ba, "region": region, "utc_end": stamps,
                         "demand_mw": demand, "forecast_mw": 1.0})


def test_window_includes_both_end_stamps():
    stamps = pd.Series([sel.WINDOW_FIRST_END, sel.WINDOW_LAST_END,
                        sel.WINDOW_LAST_END + pd.Timedelta(hours=1)])
    assert sel.in_window(pd.DataFrame({"utc_end": stamps})).tolist() == [True, True, False]


def test_coverage_gives_zero_for_year_without_rows():
    table = sel.coverage_table(frame("AAA", "SE", [pd.Timestamp("2021-06-01 01:00", tz="UTC")]))
    row = table.set_index("year").loc[2023]
    assert row["rows_present"] == 0 and row["demand_coverage"] == 0 and not row["demand_pass"]


def test_two_regions_in_window_is_a_conflict():
    stamps = pd.date_range("2021-06-01 01:00", periods=2, freq="h", tz="UTC")
    with pytest.raises(ValueError):
        sel.ba_regions(frame("AAA", ["SE", "NW"], stamps))
