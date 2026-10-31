"""Screen out implausible values before any forecast is built or scored.

A value is invalid if it is missing, <= 0, or above SPIKE_FACTOR times the BA's
SPIKE_QUANTILE of positive train-period demand. The limit uses the train split only, so
later years cannot shape it. Invalid values become NaN; no rows are dropped.

Only high values are caught: a sudden drop that stays above 0 passes.
"""

import pandas as pd

SPIKE_QUANTILE = 0.999  # a high percentile that a few bad readings cannot move
SPIKE_FACTOR = 1.5  # room above real record peaks; EIA also uses 1.5x for anomalies

COLUMNS = ["demand_mw", "forecast_mw"]


def upper_limits(df: pd.DataFrame) -> pd.Series:
    """Upper limit (MW) per BA, from positive train-period demand.

    Raise if a BA has no train rows, since its limit could not be set.
    """
    train = df[df["split"] == "train"]

    bas_without_train = set(df["ba"]) - set(train["ba"])
    if bas_without_train:
        raise ValueError(f"No train rows to set a limit for {sorted(bas_without_train)}")

    positive_demand = train["demand_mw"].where(train["demand_mw"] > 0)
    high_point = positive_demand.groupby(train["ba"], observed=True).quantile(SPIKE_QUANTILE)

    return SPIKE_FACTOR * high_point


def screen(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return a copy of df with invalid values set to NaN, plus per-BA spike counts.

    Spike counts are values that were present and > 0 but above the limit.
    """
    limit = df["ba"].map(upper_limits(df)).astype(float)

    out = df.copy()
    spike_counts = {}

    for column in COLUMNS:
        is_spike = out[column] > limit
        is_valid = (out[column] > 0) & ~is_spike

        spike_counts[f"{column}_spikes"] = is_spike.groupby(out["ba"], observed=True).sum()
        out[column] = out[column].where(is_valid)

    return out, pd.DataFrame(spike_counts).reset_index()
