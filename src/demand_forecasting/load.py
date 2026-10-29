"""Load the EIA-930 balance files into one tidy frame.

Reads only the columns this project needs, by name (the files come in a 44- and a
65-column version). Does not clean, drop, or impute anything: that is a decision for
later steps. Facts about the files are in data/MANIFEST.md.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
FILE_GLOB = "eia930-*-balance.csv"
EXPECTED_FILES = 12

# Raw column name -> name used in this project.
COLUMNS = {
    "Balancing Authority": "ba",
    "Region": "region",
    "UTC Time at End of Hour": "utc_end",
    "Demand (MW)": "demand_mw",
    "Demand Forecast (MW)": "forecast_mw",
}
# Category for repeated text cuts memory several-fold; float keeps NaN for missing values.
DTYPES = {
    "Balancing Authority": "category",
    "Region": "category",
    "Demand (MW)": "float64",
    "Demand Forecast (MW)": "float64",
}
TIMESTAMP_FORMAT = "%m/%d/%Y %I:%M:%S %p"  # e.g. "01/01/2021 7:00:00 AM", no zone; it is UTC


def read_balance_file(path: Path) -> pd.DataFrame:
    """Read one balance CSV and return the COLUMNS, renamed.

    Output dtypes: ba, region -> category; utc_end -> datetime (UTC);
    demand_mw, forecast_mw -> float64 (missing stays NaN).

    Raise ValueError naming the file if any column in COLUMNS is absent.
    """
    header = pd.read_csv(path, nrows=0).columns
    missing = [col for col in COLUMNS if col not in header]
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {missing}")

    data = pd.read_csv(path, usecols=list(COLUMNS), dtype=DTYPES).rename(columns=COLUMNS)
    data["utc_end"] = pd.to_datetime(data["utc_end"], format=TIMESTAMP_FORMAT, utc=True)
    return data


def load_balance(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Read every balance file in raw_dir into one frame, sorted by (ba, utc_end).

    Adds a `source_file` column. Raise if the file count is not EXPECTED_FILES or if
    any (ba, utc_end) pair appears more than once (within or across files).
    """
    files = sorted(raw_dir.glob(FILE_GLOB))
    if len(files) != EXPECTED_FILES:
        raise ValueError(f"Expected {EXPECTED_FILES} files in {raw_dir}, found {len(files)}")

    df = pd.concat(
        [read_balance_file(f).assign(source_file=f.name) for f in files], ignore_index=True
    )
    # Categories differ by file (BAs come and go), so concat falls back to text; restore.
    df = df.astype({"ba": "category", "region": "category", "source_file": "category"})

    dupes = df.duplicated(["ba", "utc_end"], keep=False)
    if dupes.any():
        raise ValueError(f"Duplicate (ba, utc_end) pairs:\n{df[dupes].head(10)}")

    return df.sort_values(["ba", "utc_end"], ignore_index=True)
