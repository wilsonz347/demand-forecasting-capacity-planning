"""Choose balancing authorities (BAs) by the frozen rules in docs/ba_selection_protocol.md.

Data completeness only: no model output may feed into this module.
Run with `python -m demand_forecasting.ba_selection`.
"""

from collections import Counter

import pandas as pd

from demand_forecasting.load import ROOT, load_balance

# Frozen inputs (protocol, "Frozen inputs"). An hour is named by its UTC end stamp and
# belongs to the year its interval starts in, so the stamp 2022-01-01 00:00 is in 2021.
WINDOW_FIRST_END = pd.Timestamp("2021-01-01 01:00", tz="UTC")
WINDOW_LAST_END = pd.Timestamp("2026-10-24 00:00", tz="UTC")
EXPECTED_HOURS = {2021: 8760, 2022: 8760, 2023: 8760, 2024: 8784, 2025: 8760, 2026: 7104}
EXCLUDED_BAS = {"AVA", "FPC", "GVL", "LGEE", "PSEI", "SEC", "SPA", "TEPC"}  # revision 1

COVERAGE_THRESHOLD = 0.95
N_SELECTED = 10
MIN_REGIONS = 4

OUT_DIR = ROOT / "data" / "derived" / "ba_selection"
COVERAGE_COLUMNS = [  # order as in the protocol's coverage table
    "ba", "region", "year", "expected_hours", "rows_present",
    "valid_demand_hours", "demand_coverage", "valid_forecast_hours", "forecast_coverage",
    "demand_pass", "forecast_pass",
]


def hour_year(utc_end: pd.Series) -> pd.Series:
    """Year each hour belongs to: the year its interval starts in (utc_end minus 1 hour)."""
    return (utc_end - pd.Timedelta(hours=1)).dt.year


def window_hours() -> pd.DatetimeIndex:
    """Every UTC end stamp in the study window, hourly, both ends inclusive."""
    return pd.date_range(WINDOW_FIRST_END, WINDOW_LAST_END, freq="h")


def in_window(df: pd.DataFrame) -> pd.Series:
    return df["utc_end"].between(WINDOW_FIRST_END, WINDOW_LAST_END)


def ba_regions(df: pd.DataFrame) -> pd.Series:
    """Region per BA; raise if any BA has more than one inside the window (protocol: a conflict)."""
    inside = df[in_window(df)].groupby("ba", observed=True)["region"].unique()
    multi = inside[inside.str.len() > 1]
    if not multi.empty:
        raise ValueError(f"BAs with more than one region: {multi.to_dict()}")
    return df.groupby("ba", observed=True)["region"].first().astype(str)


def coverage_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per BA and year, columns as in the protocol's coverage table.

    Valid means present and > 0. Coverage divides by expected_hours (the calendar),
    not by rows_present, so absent rows count as missing. Every BA in df gets a row for
    every year, including years it has no rows (coverage 0).
    """
    kept = df[in_window(df)]
    counts = (
        kept.assign(
            year=hour_year(kept["utc_end"]),
            valid_demand=kept["demand_mw"] > 0,  # NaN > 0 is False
            valid_forecast=kept["forecast_mw"] > 0,
        )
        .groupby(["ba", "year"], observed=True)
        .agg(
            rows_present=("utc_end", "size"),
            valid_demand_hours=("valid_demand", "sum"),
            valid_forecast_hours=("valid_forecast", "sum"),
        )
    )
    regions = ba_regions(df)
    every_pair = pd.MultiIndex.from_product([regions.index, list(EXPECTED_HOURS)], names=["ba", "year"])
    table = counts.reindex(every_pair, fill_value=0).reset_index()

    table["ba"] = table["ba"].astype(str)
    table.insert(1, "region", table["ba"].map(regions))
    table.insert(3, "expected_hours", table["year"].map(EXPECTED_HOURS))
    for kind in ("demand", "forecast"):
        table[f"{kind}_coverage"] = table[f"valid_{kind}_hours"] / table["expected_hours"]
        table[f"{kind}_pass"] = table[f"{kind}_coverage"] >= COVERAGE_THRESHOLD
    return table[COVERAGE_COLUMNS]


def ba_report(df: pd.DataFrame) -> pd.DataFrame:
    """Per-BA counts the protocol asks for: non-positive values in the window, rows outside it.

    Duplicate UTC stamps are not counted here: load_balance already refuses them.
    """
    inside = in_window(df)
    return (
        df.assign(
            demand_nonpositive=inside & (df["demand_mw"] <= 0),
            forecast_nonpositive=inside & (df["forecast_mw"] <= 0),
            rows_outside_window=~inside,
        )
        .groupby("ba", observed=True)[["demand_nonpositive", "forecast_nonpositive", "rows_outside_window"]]
        .sum()
        .reset_index()
        .astype({"ba": str})
    )


def rank_eligible(coverage: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Ranking R (protocol steps 2-3): eligible BAs sorted by mean valid demand.

    Eligible: not in EXCLUDED_BAS and both passes true in every year.
    Mean demand: mean of valid (> 0) demand_mw inside the window, per BA.
    Returns columns ba, region, mean_demand_mw, rank (1 = largest);
    ties broken by BA code ascending.
    """
    passed = coverage.groupby("ba")[["demand_pass", "forecast_pass"]].all().all(axis=1)
    eligible = set(passed[passed].index) - EXCLUDED_BAS

    valid = df[in_window(df) & (df["demand_mw"] > 0) & df["ba"].isin(eligible)]
    ranking = (
        valid.groupby("ba", observed=True)["demand_mw"].mean()
        .rename("mean_demand_mw")
        .reset_index()
        .astype({"ba": str})
        .sort_values(["mean_demand_mw", "ba"], ascending=[False, True], ignore_index=True)
    )
    ranking.insert(1, "region", ranking["ba"].map(ba_regions(df)))
    ranking["rank"] = ranking.index + 1
    return ranking


def select_bas(ranking: pd.DataFrame) -> tuple[list[str], list[dict]]:
    """Protocol steps 4-7: take the top N_SELECTED, then repair to MIN_REGIONS regions.

    Each swap adds the highest-ranked unselected BA from a region not yet selected and
    removes the lowest-ranked selected BA whose region has 2+ selected. Every swap adds
    one region and loses none, so the loop ends. Returns (BA codes in rank order, swap
    log). Raise ValueError on a protocol conflict.
    """
    if len(ranking) < N_SELECTED:
        raise ValueError(f"Conflict: {len(ranking)} eligible BAs, need {N_SELECTED}")

    rows = ranking.to_dict("records")  # already in rank order
    selected = rows[:N_SELECTED]
    swaps = []
    while len(per_region := Counter(r["region"] for r in selected)) < MIN_REGIONS:
        add = next((r for r in rows if r not in selected and r["region"] not in per_region), None)
        drop = next((r for r in reversed(selected) if per_region[r["region"]] >= 2), None)
        if add is None or drop is None:
            raise ValueError(f"Conflict: cannot reach {MIN_REGIONS} regions; selected {selected}")
        swaps.append({
            "removed_ba": drop["ba"], "removed_region": drop["region"], "removed_rank": drop["rank"],
            "added_ba": add["ba"], "added_region": add["region"], "added_rank": add["rank"],
        })
        selected = sorted([r for r in selected if r is not drop] + [add], key=lambda r: r["rank"])
    return [r["ba"] for r in selected], swaps


def main() -> None:
    df = load_balance()
    coverage = coverage_table(df)
    ranking = rank_eligible(coverage, df)
    selected, swaps = select_bas(ranking)

    # Raw tables for docs/ba_selection_results.md; data/ is git-ignored.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(OUT_DIR / "coverage.csv", index=False)
    ba_report(df).to_csv(OUT_DIR / "ba_report.csv", index=False)
    ranking.to_csv(OUT_DIR / "ranking.csv", index=False)
    pd.DataFrame(swaps).to_csv(OUT_DIR / "swaps.csv", index=False)

    print(f"Eligible: {len(ranking)}. Selected: {', '.join(selected)}. Swaps: {len(swaps)}.")
    print(f"Tables written to {OUT_DIR}")


if __name__ == "__main__":
    main()
