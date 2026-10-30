import numpy as np
import pandas as pd

from demand_forecasting import screening as sc


def frame(train, validation):
    values = np.asarray(train + validation, dtype=float)
    return pd.DataFrame({
        "ba": "TVA",
        "demand_mw": values,
        "forecast_mw": values,
        "split": ["train"] * len(train) + ["validation"] * len(validation),
    })


def test_spike_removed_and_real_peak_kept():
    df = frame([100.0] * 1000, [140.0, 1_000_000.0, -5.0])  # limit is 1.5 * 100 = 150
    out, spikes = sc.screen(df)
    assert out["demand_mw"].iloc[-3:].tolist()[0] == 140.0  # above train max, still real
    assert out["demand_mw"].iloc[-3:].isna().tolist() == [False, True, True]
    assert spikes.loc[0, "demand_mw_spikes"] == 1  # the <= 0 value is not a spike


def test_limit_uses_train_only():
    # A huge validation value must not raise the limit it is judged against.
    assert sc.upper_limits(frame([100.0] * 1000, [1e9] * 1000)).iloc[0] == 150.0


def test_each_ba_gets_its_own_limit():
    big, small = frame([1000.0] * 1000, [1200.0]), frame([100.0] * 1000, [1200.0])
    small["ba"] = "ISNE"
    out, _ = sc.screen(pd.concat([big, small], ignore_index=True))
    last = out.groupby("ba")["demand_mw"].last()
    assert last["TVA"] == 1200.0 and np.isnan(last["ISNE"])  # valid for one, spike for other


def test_no_train_rows_is_an_error():
    import pytest
    with pytest.raises(ValueError):
        sc.screen(frame([], [100.0]))
