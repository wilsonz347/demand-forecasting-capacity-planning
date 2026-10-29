"""Build the modeling dataset: the 10 selected BAs, study window only, tagged by split.

No cleaning or imputation: invalid values stay as they are, so each model step decides
how to handle them. Run with `python -m demand_forecasting.build_dataset`.
"""

import pandas as pd

from demand_forecasting import ba_selection
from demand_forecasting.load import ROOT, load_balance

# Frozen in docs/ba_selection_results.md; main() checks the code still reproduces it.
SELECTED_BAS = ["PJM", "MISO", "ERCO", "SOCO", "CISO", "TVA", "NYIS", "ISNE", "DUK", "BPAT"]

# First UTC hour-ending stamp of each later split (docs/project_brief.md, "Time splits").
VALIDATION_FIRST_END = pd.Timestamp("2024-10-24 01:00", tz="UTC")
TEST_FIRST_END = pd.Timestamp("2025-10-24 01:00", tz="UTC")

SPLITS = pd.CategoricalDtype(["train", "validation", "test"], ordered=True)
OUT_PATH = ROOT / "data" / "derived" / "dataset.parquet"


def assign_split(utc_end: pd.Series) -> pd.Series:
    """Label each hour "train", "validation", or "test" by its UTC end stamp."""
    split = pd.Series("train", index=utc_end.index)
    split[utc_end >= VALIDATION_FIRST_END] = "validation"
    split[utc_end >= TEST_FIRST_END] = "test"
    return split.astype(SPLITS)


def build(df: pd.DataFrame, bas: list[str]) -> pd.DataFrame:
    """Keep the given BAs and the study window, add `split`, sort by (ba, utc_end).

    Columns: ba, region, utc_end, demand_mw, forecast_mw, split.
    """
    kept = df[df["ba"].isin(bas) & ba_selection.in_window(df)].drop(columns="source_file")
    kept = kept.assign(split=assign_split(kept["utc_end"]))
    if isinstance(kept["ba"].dtype, pd.CategoricalDtype):  # drop the ~57 BAs not kept
        kept["ba"] = kept["ba"].cat.remove_unused_categories()
        kept["region"] = kept["region"].cat.remove_unused_categories()
    return kept.sort_values(["ba", "utc_end"], ignore_index=True)


def main() -> None:
    df = load_balance()
    coverage = ba_selection.coverage_table(df)
    selected, _ = ba_selection.select_bas(ba_selection.rank_eligible(coverage, df))
    if selected != SELECTED_BAS:
        raise ValueError(f"Selection changed: got {selected}, frozen {SELECTED_BAS}")

    dataset = build(df, SELECTED_BAS)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_parquet(OUT_PATH, index=False)

    print(f"Wrote {len(dataset):,} rows to {OUT_PATH}")
    print(pd.crosstab(dataset["ba"], dataset["split"], margins=True))


if __name__ == "__main__":
    main()
