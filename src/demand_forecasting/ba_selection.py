"""Choose balancing authorities (BAs) by the frozen rules in docs/ba_selection_protocol.md.

Uses data completeness only: no model output may feed into this module.
Run with `python -m demand_forecasting.ba_selection`.
"""

from collections import Counter

import pandas as pd

from demand_forecasting.load import ROOT, load_balance

# --- Frozen inputs (protocol, "Inputs") -------------------------------------------------

# An hour is named by its UTC end time and belongs to the year it *starts* in,
# so the stamp 2022-01-01 00:00 is the last hour of 2021.
WINDOW_FIRST_END = pd.Timestamp("2021-01-01 01:00", tz="UTC")
WINDOW_LAST_END = pd.Timestamp("2026-10-24 00:00", tz="UTC")
EXPECTED_HOURS = {2021: 8760, 2022: 8760, 2023: 8760, 2024: 8784, 2025: 8760, 2026: 7104}

# Revision 1: EIA says these BAs' forecasts don't compare well with actual demand.
EXCLUDED_BAS = {"AVA", "FPC", "GVL", "LGEE", "PSEI", "SEC", "SPA", "TEPC"}

COVERAGE_THRESHOLD = 0.95
N_SELECTED = 10
MIN_REGIONS = 4

# --- Outputs -----------------------------------------------------------------------------

OUT_DIR = ROOT / "data" / "derived" / "ba_selection"

# Column order of the protocol's coverage table.
COVERAGE_COLUMNS = [
    "ba", "region", "year", "expected_hours", "rows_present",
    "valid_demand_hours", "demand_coverage",
    "valid_forecast_hours", "forecast_coverage",
    "demand_pass", "forecast_pass",
]


def hour_year(utc_end: pd.Series) -> pd.Series:
    """Year each hour belongs to: the year its interval starts in."""
    interval_start = utc_end - pd.Timedelta(hours=1)
    return interval_start.dt.year


def window_hours() -> pd.DatetimeIndex:
    """Every UTC end time in the study window, hourly, both ends included."""
    return pd.date_range(WINDOW_FIRST_END, WINDOW_LAST_END, freq="h")


def in_window(df: pd.DataFrame) -> pd.Series:
    """True for rows inside the study window."""
    return df["utc_end"].between(WINDOW_FIRST_END, WINDOW_LAST_END)


def ba_regions(df: pd.DataFrame) -> pd.Series:
    """Region of each BA.

    The protocol requires exactly one region per BA inside the window; more is a conflict.
    """
    regions_in_window = df[in_window(df)].groupby("ba", observed=True)["region"].unique()
    has_several = regions_in_window[regions_in_window.str.len() > 1]
    if not has_several.empty:
        raise ValueError(f"BAs with more than one region: {has_several.to_dict()}")

    return df.groupby("ba", observed=True)["region"].first().astype(str)


def coverage_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per BA and year, with the protocol's coverage columns.

    Valid means present and > 0. Coverage divides by expected_hours (the calendar), not by
    the rows present, so absent rows count as missing. Every BA gets a row for every year,
    including years in which it has no rows at all (coverage 0).
    """
    rows = df[in_window(df)]

    # Mark each hour as valid or not. NaN > 0 is False, so missing values count as invalid.
    rows = rows.assign(
        year=hour_year(rows["utc_end"]),
        valid_demand=rows["demand_mw"] > 0,
        valid_forecast=rows["forecast_mw"] > 0,
    )

    # Count rows and valid hours per BA and year.
    counts = rows.groupby(["ba", "year"], observed=True).agg(
        rows_present=("utc_end", "size"),
        valid_demand_hours=("valid_demand", "sum"),
        valid_forecast_hours=("valid_forecast", "sum"),
    )

    # Add the (BA, year) pairs with no rows, so they show up with zero coverage.
    regions = ba_regions(df)
    every_pair = pd.MultiIndex.from_product(
        [regions.index, list(EXPECTED_HOURS)], names=["ba", "year"]
    )
    table = counts.reindex(every_pair, fill_value=0).reset_index()

    # Region, calendar hours, coverage, and pass/fail.
    table["ba"] = table["ba"].astype(str)
    table["region"] = table["ba"].map(regions)
    table["expected_hours"] = table["year"].map(EXPECTED_HOURS)

    for kind in ("demand", "forecast"):
        table[f"{kind}_coverage"] = table[f"valid_{kind}_hours"] / table["expected_hours"]
        table[f"{kind}_pass"] = table[f"{kind}_coverage"] >= COVERAGE_THRESHOLD

    return table[COVERAGE_COLUMNS]


def ba_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per-BA counts the protocol asks for: values <= 0 in the window, rows outside it.

    Duplicate hours are not counted here, because load_balance already refuses them.
    """
    inside = in_window(df)

    flags = pd.DataFrame({
        "ba": df["ba"],
        "demand_nonpositive": inside & (df["demand_mw"] <= 0),
        "forecast_nonpositive": inside & (df["forecast_mw"] <= 0),
        "rows_outside_window": ~inside,
    })

    report = flags.groupby("ba", observed=True).sum().reset_index()
    return report.astype({"ba": str})


def rank_eligible(coverage: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Protocol steps 2-3: rank the eligible BAs by mean valid demand.

    Eligible: not excluded, and both coverages pass in every year.
    Mean demand: the mean of valid (> 0) demand inside the window.
    Returns ba, region, mean_demand_mw, and rank (1 = largest); ties go by BA code.
    """
    # A BA passes only if every one of its years passes, for both demand and forecast.
    passes_every_year = (
        coverage.groupby("ba")[["demand_pass", "forecast_pass"]].all().all(axis=1)
    )
    eligible = set(passes_every_year[passes_every_year].index) - EXCLUDED_BAS

    # Mean valid demand of each eligible BA.
    valid_rows = df[in_window(df) & (df["demand_mw"] > 0) & df["ba"].isin(eligible)]
    mean_demand = valid_rows.groupby("ba", observed=True)["demand_mw"].mean()

    ranking = mean_demand.rename("mean_demand_mw").reset_index()
    ranking = ranking.astype({"ba": str})

    # Largest first; equal means are ordered by BA code.
    ranking = ranking.sort_values(
        ["mean_demand_mw", "ba"], ascending=[False, True], ignore_index=True
    )
    ranking.insert(1, "region", ranking["ba"].map(ba_regions(df)))
    ranking["rank"] = ranking.index + 1

    return ranking


def select_bas(ranking: pd.DataFrame) -> tuple[list[str], list[dict]]:
    """Protocol steps 4-7: take the top N_SELECTED, then swap until MIN_REGIONS are covered.

    Each swap brings in the highest-ranked unselected BA from a region not yet selected,
    and drops the lowest-ranked selected BA whose region has 2 or more selected. Every swap
    adds a region and loses none, so the loop always ends.

    Returns (selected BA codes in rank order, swap log). Raise ValueError on a conflict.
    """
    if len(ranking) < N_SELECTED:
        raise ValueError(f"Conflict: {len(ranking)} eligible BAs, need {N_SELECTED}")

    candidates = ranking.to_dict("records")  # already in rank order
    selected = candidates[:N_SELECTED]
    swaps = []

    while True:
        selected_per_region = Counter(ba["region"] for ba in selected)
        if len(selected_per_region) >= MIN_REGIONS:
            break

        # Highest-ranked unselected BA from a region we don't have yet.
        add = next(
            (ba for ba in candidates
             if ba not in selected and ba["region"] not in selected_per_region),
            None,
        )
        # Lowest-ranked selected BA whose region would still be covered without it.
        drop = next(
            (ba for ba in reversed(selected) if selected_per_region[ba["region"]] >= 2),
            None,
        )
        if add is None or drop is None:
            raise ValueError(f"Conflict: cannot reach {MIN_REGIONS} regions; selected {selected}")

        swaps.append({
            "removed_ba": drop["ba"],
            "removed_region": drop["region"],
            "removed_rank": drop["rank"],
            "added_ba": add["ba"],
            "added_region": add["region"],
            "added_rank": add["rank"],
        })

        selected = [ba for ba in selected if ba is not drop] + [add]
        selected.sort(key=lambda ba: ba["rank"])

    return [ba["ba"] for ba in selected], swaps


def main() -> None:
    df = load_balance()

    coverage = coverage_table(df)
    ranking = rank_eligible(coverage, df)
    selected, swaps = select_bas(ranking)

    # Tables behind docs/ba_selection_results.md (data/ is git-ignored).
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(OUT_DIR / "coverage.csv", index=False)
    ba_report(df).to_csv(OUT_DIR / "ba_report.csv", index=False)
    ranking.to_csv(OUT_DIR / "ranking.csv", index=False)
    pd.DataFrame(swaps).to_csv(OUT_DIR / "swaps.csv", index=False)

    print(f"Eligible: {len(ranking)}. Selected: {', '.join(selected)}. Swaps: {len(swaps)}.")
    print(f"Tables written to {OUT_DIR}")


if __name__ == "__main__":
    main()
