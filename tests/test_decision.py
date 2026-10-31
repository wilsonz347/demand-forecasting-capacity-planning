import pandas as pd
import pytest

from demand_forecasting import decision as dc


def test_ratio_maps_to_its_percentile():
    assert dc.percentile_of(9) == pytest.approx(0.9)
    assert dc.RATIOS[9] == "q90"


def test_hourly_cost_weights_shortfall_by_ratio():
    actual = pd.Series([100.0, 100.0, 100.0])
    commit = pd.Series([90.0, 110.0, 100.0])  # 10 short, 10 extra, exact
    assert dc.hourly_cost(actual, commit, 4).tolist() == [40.0, 10.0, 0.0]


def test_operator_margin_is_a_percentile_of_past_errors():
    # Operator errors (actual - forecast) are 0, 1, ..., 99 MW.
    train = pd.DataFrame({"ba": "PJM", "demand_mw": [1000.0 + e for e in range(100)],
                          "forecast_mw": 1000.0})
    margins = dc.operator_margins(train)
    assert margins.loc["PJM", 1] == pytest.approx(49.5)  # median error
    assert margins.loc["PJM", 9] == pytest.approx(89.1)  # 90th percentile error


def test_compare_uses_same_hours_and_reports_saving():
    validation = pd.DataFrame({"ba": "PJM", "demand_mw": [100.0, 100.0, None],
                               "forecast_mw": [90.0, 90.0, 90.0]})
    for column in dc.RATIOS.values():
        validation[column] = 100.0  # our range nails it
    margins = pd.DataFrame({ratio: [0.0] for ratio in dc.RATIOS}, index=["PJM"])

    results = dc.compare(validation, margins).set_index("ratio")
    assert (results["hours"] == 2).all()  # the hour with no actual is skipped
    assert results.loc[9, "range_cost"] == 0.0
    assert results.loc[9, "operator_cost"] == 90.0  # 10 short x 9
    assert results.loc[9, "saving_pct"] == 100.0
