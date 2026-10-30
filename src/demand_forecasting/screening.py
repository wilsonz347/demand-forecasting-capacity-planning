"""Screen out implausible values before any forecast is built or scored (brief, question 6).

A value is invalid if it is missing, <= 0, or above SPIKE_FACTOR times the BA's
SPIKE_QUANTILE of positive train-period demand.
Only high-side errors are caught; implausible drops that stay > 0 pass. The limit comes from the train split only,
so later years cannot shape it. Invalid values become NaN; rows are never dropped here.
"""

import pandas as pd

SPIKE_QUANTILE = 0.999  # high enough that a few spikes cannot move it
SPIKE_FACTOR = 1.5  # room above real record peaks; EIA also uses 1.5x for anomalies

COLUMNS = ["demand_mw", "forecast_mw"]


def upper_limits(df: pd.DataFrame) -> pd.Series:
    """Per-BA upper limit (MW) from positive train-period demand. Raise if a BA has no train rows."""
    train = df[df["split"] == "train"]
    if missing := set(df["ba"]) - set(train["ba"]):
        raise ValueError(f"No train rows to set a limit for {sorted(missing)}")
    demand = train["demand_mw"].where(train["demand_mw"] > 0)
    return SPIKE_FACTOR * demand.groupby(train["ba"], observed=True).quantile(SPIKE_QUANTILE)


def screen(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (copy of df with invalid values set to NaN, per-BA counts of spikes removed).

    Counts are of values that were present and > 0 but above the limit.
    """
    limit = df["ba"].map(upper_limits(df)).astype(float)
    out = df.copy()
    spikes = {}
    for col in COLUMNS:
        spike = out[col] > limit
        spikes[f"{col}_spikes"] = spike.groupby(out["ba"], observed=True).sum()
        out[col] = out[col].where((out[col] > 0) & ~spike)
    return out, pd.DataFrame(spikes).reset_index()
