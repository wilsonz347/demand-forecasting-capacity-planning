"""Load the EIA-930 balance files into one table.

Reads only the five columns this project needs, by name, because the files come in two
layouts (44 and 65 columns). Nothing is cleaned, dropped, or filled in here; later steps
decide that. Facts about the files are in data/MANIFEST.md.
"""

from pathlib import Path

import pandas as pd

# --- Paths -------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
FILE_GLOB = "eia930-*-balance.csv"
EXPECTED_FILES = 12

# --- Columns -----------------------------------------------------------------------------

# Raw column name -> short name used in this project.
COLUMNS = {
    "Balancing Authority": "ba",
    "Region": "region",
    "UTC Time at End of Hour": "utc_end",
    "Demand (MW)": "demand_mw",
    "Demand Forecast (MW)": "forecast_mw",
}

# "category" stores repeated text (BA codes, regions) once, which saves a lot of memory.
# "float64" keeps missing values as NaN instead of turning the column into whole numbers.
DTYPES = {
    "Balancing Authority": "category",
    "Region": "category",
    "Demand (MW)": "float64",
    "Demand Forecast (MW)": "float64",
}

# Example: "01/01/2021 7:00:00 AM". The file gives no time zone, but the column is UTC.
TIMESTAMP_FORMAT = "%m/%d/%Y %I:%M:%S %p"


def read_balance_file(path: Path) -> pd.DataFrame:
    """Read one balance CSV and return the five COLUMNS, renamed.

    Raise ValueError naming the file if any needed column is missing.
    """
    # Check the header first, so a bad file fails with a clear message.
    header = pd.read_csv(path, nrows=0).columns
    missing = [column for column in COLUMNS if column not in header]
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {missing}")

    data = pd.read_csv(path, usecols=list(COLUMNS), dtype=DTYPES)
    data = data.rename(columns=COLUMNS)

    # A wrongly formatted timestamp raises an error here (a blank one becomes NaT).
    data["utc_end"] = pd.to_datetime(data["utc_end"], format=TIMESTAMP_FORMAT, utc=True)

    return data


def load_balance(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Read every balance file into one table, sorted by (ba, utc_end).

    Adds a `source_file` column. Raise if there are not EXPECTED_FILES files, or if any
    (ba, utc_end) pair appears more than once.
    """
    files = sorted(raw_dir.glob(FILE_GLOB))
    if len(files) != EXPECTED_FILES:
        raise ValueError(f"Expected {EXPECTED_FILES} files in {raw_dir}, found {len(files)}")

    # Read each file and remember where every row came from.
    tables = []
    for file in files:
        table = read_balance_file(file)
        table["source_file"] = file.name
        tables.append(table)
    df = pd.concat(tables, ignore_index=True)

    # Each file has its own list of BAs, so concat turns the categories back into text.
    df = df.astype({"ba": "category", "region": "category", "source_file": "category"})

    # The same BA and hour twice would be counted twice later, so stop here instead.
    duplicates = df.duplicated(["ba", "utc_end"], keep=False)
    if duplicates.any():
        raise ValueError(f"Duplicate (ba, utc_end) pairs:\n{df[duplicates].head(10)}")

    return df.sort_values(["ba", "utc_end"], ignore_index=True)
