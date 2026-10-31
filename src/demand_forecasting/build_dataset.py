"""Build the modeling dataset: the 10 selected BAs, whole local days, tagged by split.

Nothing is cleaned or filled in: invalid values stay as they are, and each model step
decides how to handle them. Run with `python -m demand_forecasting.build_dataset`.
"""

import datetime as dt

import pandas as pd

from demand_forecasting import ba_selection
from demand_forecasting.load import ROOT, load_balance

# Frozen in docs/ba_selection_results.md. main() checks the code still picks the same list.
SELECTED_BAS = ["PJM", "MISO", "ERCO", "SOCO", "CISO", "TVA", "NYIS", "ISNE", "DUK", "BPAT"]

# The time zone EIA uses to date each BA's hours (its `Data Date`), checked row by row
# against the raw files. MISO is dated in Eastern Standard Time all year (no daylight saving).
TIMEZONES = {
    "PJM": "America/New_York",
    "MISO": "Etc/GMT+5",
    "NYIS": "America/New_York",
    "ISNE": "America/New_York",
    "DUK": "America/New_York",
    "ERCO": "America/Chicago",
    "SOCO": "America/Chicago",
    "TVA": "America/Chicago",
    "CISO": "America/Los_Angeles",
    "BPAT": "America/Los_Angeles",
}

# Splits by local date (docs/project_brief.md), so no day is cut in two.
FIRST_DATE = dt.date(2021, 1, 1)
VALIDATION_FIRST_DATE = dt.date(2024, 10, 24)
TEST_FIRST_DATE = dt.date(2025, 10, 24)
LAST_DATE = dt.date(2026, 10, 23)  # local Oct 24, 2026 has no demand for any BA

SPLITS = pd.CategoricalDtype(["train", "validation", "test"], ordered=True)
OUT_PATH = ROOT / "data" / "derived" / "dataset.parquet"
COLUMNS = ["ba", "region", "utc_end", "local_date", "demand_mw", "forecast_mw", "split"]


def local_date(ba: pd.Series, utc_end: pd.Series) -> pd.Series:
    """Local date of each hour: the date its interval starts on, in the BA's time zone.

    This matches EIA's `Data Date`: the hour ending at local midnight is hour 24 of the
    previous day.
    """
    interval_start = utc_end - pd.Timedelta(hours=1)
    dates = pd.Series(pd.NaT, index=utc_end.index, dtype="object")

    for name, zone in TIMEZONES.items():
        rows = ba == name
        dates[rows] = interval_start[rows].dt.tz_convert(zone).dt.date

    return dates


def assign_split(dates: pd.Series) -> pd.Series:
    """Label each local date "train", "validation", or "test"."""
    split = pd.Series("train", index=dates.index)
    split[dates >= VALIDATION_FIRST_DATE] = "validation"
    split[dates >= TEST_FIRST_DATE] = "test"
    return split.astype(SPLITS)


def build(df: pd.DataFrame, bas: list[str]) -> pd.DataFrame:
    """Keep the given BAs and local dates FIRST_DATE..LAST_DATE; add local_date and split.

    Returns the COLUMNS, sorted by (ba, utc_end).
    """
    bas_without_zone = set(bas) - TIMEZONES.keys()
    if bas_without_zone:
        raise ValueError(f"No time zone for {sorted(bas_without_zone)}; add them to TIMEZONES")

    kept = df[df["ba"].isin(bas)].drop(columns="source_file")

    # Keep whole local days only.
    kept = kept.assign(local_date=local_date(kept["ba"], kept["utc_end"]))
    kept = kept[kept["local_date"].between(FIRST_DATE, LAST_DATE)]

    kept = kept.assign(split=assign_split(kept["local_date"]))

    # Forget the ~57 BAs that were dropped, so they don't linger as empty categories.
    if isinstance(kept["ba"].dtype, pd.CategoricalDtype):
        kept["ba"] = kept["ba"].cat.remove_unused_categories()
        kept["region"] = kept["region"].cat.remove_unused_categories()

    return kept[COLUMNS].sort_values(["ba", "utc_end"], ignore_index=True)


def main() -> None:
    df = load_balance()

    # Stop if the selection rules no longer pick the frozen list.
    coverage = ba_selection.coverage_table(df)
    ranking = ba_selection.rank_eligible(coverage, df)
    selected, _ = ba_selection.select_bas(ranking)
    if selected != SELECTED_BAS:
        raise ValueError(f"Selection changed: got {selected}, frozen {SELECTED_BAS}")

    dataset = build(df, SELECTED_BAS)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_parquet(OUT_PATH, index=False)

    print(f"Wrote {len(dataset):,} rows to {OUT_PATH}")
    print(pd.crosstab(dataset["ba"], dataset["split"], margins=True))


if __name__ == "__main__":
    main()
