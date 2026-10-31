"""Day-ahead weather forecasts per BA, as they were issued before the 6 p.m. day-before cutoff.

Source: NWS GFS MOS point forecasts for airport stations, from the Iowa Environmental
Mesonet (IEM) archive. Forecasts are every 3 hours; hours in between are filled by
linear interpolation. Each BA gets one temperature and dewpoint: the average of its
stations weighted by 2020 metro population. Run with `python -m demand_forecasting.weather`.
"""

import urllib.request
from pathlib import Path

import pandas as pd

from demand_forecasting.build_dataset import OUT_PATH as DATASET_PATH
from demand_forecasting.load import ROOT

# Station -> 2020 metro population (Census CBSA estimates base 2020, cbsa-est2024-alldata.csv).
# Weights are fixed before modeling. See docs/project_brief.md, question 5.
STATIONS = {
    "PJM": {"KORD": 9_454_363, "KDCA": 6_278_595, "KPHL": 6_245_017},
    "MISO": {"KDTW": 4_392_388, "KMSP": 3_690_231, "KSTL": 2_820_847},
    "ERCO": {"KDFW": 7_638_258, "KIAH": 7_150_233, "KSAT": 2_558_387},
    "SOCO": {"KATL": 6_106_805, "KBHM": 1_180_600},
    "CISO": {"KLAX": 13_204_657, "KSFO": 4_753_655, "KONT": 4_601_631},
    "TVA": {"KBNA": 2_014_425, "KMEM": 1_345_440, "KTYS": 903_474},
    "NYIS": {"KLGA": 20_083_412, "KBUF": 1_166_870, "KROC": 1_065_355},
    "ISNE": {"KBOS": 4_944_732, "KPVD": 1_676_652, "KBDL": 1_151_909},
    "DUK": {"KCLT": 2_660_162, "KGSP": 928_208, "KGSO": 776_508},
    "BPAT": {"KSEA": 4_018_783, "KPDX": 2_512_850, "KGEG": 585_792},
}

MOS_URL = (
    "https://mesonet.agron.iastate.edu/cgi-bin/request/mos.py"
    "?station={station}&model=GFS&sts=2020-12-30T00:00Z&ets=2026-10-24T00:00Z&format=csv"
)
RUN_HOUR_UTC = 12  # use the latest run issued at or before 12Z on the day before
MAX_RUN_AGE = pd.Timedelta(hours=24)  # older than this means runs are missing: leave NaN
LAST_RUN_NEEDED = "2026-10-22 12:00:00"  # serves the last local day, 2026-10-23
RAW_DIR = ROOT / "data" / "raw" / "weather"
OUT_PATH = ROOT / "data" / "derived" / "dataset_weather.parquet"


def download(station: str, raw_dir: Path = RAW_DIR) -> Path:
    """Save one station's MOS archive as <raw_dir>/<station>.csv; skip if already there."""
    path = raw_dir / f"{station}.csv"
    if path.exists():
        return path
    raw_dir.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")  # renamed only when checked, so a failed run is retried
    with urllib.request.urlopen(MOS_URL.format(station=station), timeout=300) as resp:
        partial.write_bytes(resp.read())
    text = partial.read_text()
    last_run = text.rstrip().rsplit("\n", 1)[-1].split(",", 1)[0]
    if not text.startswith("runtime,ftime") or last_run < LAST_RUN_NEEDED:
        partial.unlink()
        raise ValueError(f"Bad or incomplete download for {station} (last run {last_run!r})")
    partial.rename(path)
    return path


def read_station(path: Path) -> pd.DataFrame:
    """Columns: runtime, ftime (both UTC), temp_c, dewpoint_c. Values in the file are in °F.

    Exact duplicate rows (a run archived twice) are dropped; conflicting ones raise.
    """
    df = pd.read_csv(path, usecols=["runtime", "ftime", "tmp", "dpt"]).drop_duplicates()
    if df.duplicated(["runtime", "ftime"]).any():
        raise ValueError(f"{path.name}: same run and hour with different values")
    return pd.DataFrame({
        "runtime": pd.to_datetime(df["runtime"], utc=True),
        "ftime": pd.to_datetime(df["ftime"], utc=True),
        "temp_c": (df["tmp"] - 32) * 5 / 9,
        "dewpoint_c": (df["dpt"] - 32) * 5 / 9,
    })


def to_hourly(mos: pd.DataFrame) -> pd.DataFrame:
    """Fill each run's 3-hourly forecasts to hourly by linear interpolation.

    Interpolates within a run only (never across runs), and only between forecast
    times (no extrapolation past the run's first or last value).
    """
    lead = (mos["ftime"] - mos["runtime"]) // pd.Timedelta(hours=1)
    out = []
    for col in ("temp_c", "dewpoint_c"):
        # One row per run, one column per lead hour; fill the missing hours along each row.
        wide = mos.assign(lead=lead).pivot(index="runtime", columns="lead", values=col)
        wide = wide.reindex(columns=range(wide.columns.min(), wide.columns.max() + 1))
        out.append(wide.interpolate(axis=1, limit_area="inside").stack().rename(col))
    hourly = pd.concat(out, axis=1).reset_index()
    hourly["ftime"] = hourly["runtime"] + pd.to_timedelta(hourly["lead"], unit="h")
    return hourly[["runtime", "ftime", "temp_c", "dewpoint_c"]]


def ba_weather(hourly: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Population-weighted temp_c and dewpoint_c per (ba, runtime, ftime).

    `hourly` maps station -> output of to_hourly. Keeps only (runtime, ftime) pairs where
    every station of the BA has both values. Returns columns ba, runtime, ftime,
    temp_c, dewpoint_c.
    """
    out = []
    for ba, stations in STATIONS.items():
        total = sum(stations.values())
        rows = pd.concat([
            hourly[s].dropna(subset=["temp_c", "dewpoint_c"]).assign(weight=pop / total)
            for s, pop in stations.items()
        ])
        rows["temp_c"] *= rows["weight"]
        rows["dewpoint_c"] *= rows["weight"]
        agg = rows.groupby(["runtime", "ftime"]).agg(
            temp_c=("temp_c", "sum"), dewpoint_c=("dewpoint_c", "sum"), n=("weight", "size"))
        out.append(agg[agg["n"] == len(stations)].drop(columns="n").reset_index().assign(ba=ba))
    return pd.concat(out, ignore_index=True)[["ba", "runtime", "ftime", "temp_c", "dewpoint_c"]]


def issue_cutoff(local_date: pd.Series) -> pd.Series:
    """Latest allowed run time for forecasting local day D: 12Z UTC on D minus 1 day."""
    return pd.to_datetime(local_date).dt.tz_localize("UTC") - pd.Timedelta(hours=24 - RUN_HOUR_UTC)


def attach_weather(dataset: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Add weather_run, temp_c, and dewpoint_c to each dataset row.

    For each (ba, local_date), use the latest run with runtime <= issue_cutoff, then
    take that run's value at ftime == utc_end (an instant reading at the end of the hour).
    Rows with no such value, or whose newest run is over MAX_RUN_AGE old, get NaN.
    """
    weather = weather.astype({"ba": str})
    days = dataset[["ba", "local_date"]].drop_duplicates().astype({"ba": str})
    days = days.assign(cutoff=issue_cutoff(days["local_date"])).sort_values("cutoff")
    runs = weather[["ba", "runtime"]].drop_duplicates().sort_values("runtime")
    chosen = pd.merge_asof(days, runs, left_on="cutoff", right_on="runtime",
                           by="ba", direction="backward", tolerance=MAX_RUN_AGE)

    out = dataset.astype({"ba": str}).merge(
        chosen[["ba", "local_date", "runtime"]].rename(columns={"runtime": "weather_run"}),
        on=["ba", "local_date"], how="left")
    out = out.merge(
        weather.rename(columns={"runtime": "weather_run", "ftime": "utc_end"}),
        on=["ba", "weather_run", "utc_end"], how="left")
    return out.astype({"ba": dataset["ba"].dtype})


def main() -> None:
    hourly = {s: to_hourly(read_station(download(s))) for ba in STATIONS for s in STATIONS[ba]}
    dataset = attach_weather(pd.read_parquet(DATASET_PATH), ba_weather(hourly))
    if missing := dataset["temp_c"].isna().sum():  # none today; a new gap must be looked at
        raise ValueError(f"{missing:,} rows have no weather forecast")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(dataset):,} rows; missing temp_c: {dataset['temp_c'].isna().sum()}")


if __name__ == "__main__":
    main()
