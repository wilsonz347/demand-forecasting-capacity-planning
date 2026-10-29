import pandas as pd
import pytest

from demand_forecasting import load

HEADER = (
    '"Balancing Authority","Data Date","UTC Time at End of Hour","Demand Forecast (MW)",'
    '"Demand (MW)","Net Generation (MW)","Region"'
)


def write_csv(path, rows):
    path.write_text("\n".join([HEADER, *rows]) + "\n")
    return path


def test_read_balance_file_keeps_renames_and_parses(tmp_path):
    f = write_csv(tmp_path / "eia930-2021half1-balance.csv", [
        "AAA,01/01/2021,01/01/2021 7:00:00 AM,679,373,475,SE",
        "AAA,01/01/2021,01/01/2021 8:00:00 AM,,,453,SE",
    ])
    df = load.read_balance_file(f)
    assert set(df.columns) == set(load.COLUMNS.values())
    assert df["utc_end"].iloc[0] == pd.Timestamp("2021-01-01 07:00", tz="UTC")
    assert df["demand_mw"].isna().iloc[1]  # missing stays missing, not 0


def test_read_balance_file_rejects_missing_column(tmp_path):
    f = tmp_path / "eia930-2021half1-balance.csv"
    f.write_text('"Balancing Authority","UTC Time at End of Hour"\nAAA,01/01/2021 7:00:00 AM\n')
    with pytest.raises(ValueError):
        load.read_balance_file(f)


def test_load_balance_rejects_duplicate_hours_across_files(tmp_path, monkeypatch):
    monkeypatch.setattr(load, "EXPECTED_FILES", 2)
    row = "AAA,01/01/2021,01/01/2021 7:00:00 AM,679,373,475,SE"
    write_csv(tmp_path / "eia930-2021half1-balance.csv", [row])
    write_csv(tmp_path / "eia930-2021half2-balance.csv", [row])
    with pytest.raises(ValueError):
        load.load_balance(tmp_path)
