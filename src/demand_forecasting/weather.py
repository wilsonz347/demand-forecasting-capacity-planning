"""Day-ahead weather forecasts per BA, as issued before the 6 p.m. day-before cutoff.

Source: NWS GFS MOS forecasts for airport weather stations, archived by the Iowa
Environmental Mesonet (IEM). Forecasts come every 3 hours; the hours in between are filled
by linear interpolation. Each BA gets one temperature and one dewpoint: the average of its
stations, weighted by 2020 metro population.
Run with `python -m demand_forecasting.weather`.
"""

import urllib.request
from pathlib import Path

import pandas as pd

from demand_forecasting.build_dataset import OUT_PATH as DATASET_PATH
from demand_forecasting.load import ROOT

# --- Stations ----------------------------------------------------------------------------

# Station -> 2020 metro population (Census CBSA estimates base 2020, cbsa-est2024-alldata.csv).
# The weights are fixed before modeling (docs/project_brief.md).
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

# --- Download ----------------------------------------------------------------------------

MOS_URL = (
    "https://mesonet.agron.iastate.edu/cgi-bin/request/mos.py"
    "?station={station}&model=GFS&sts=2020-12-30T00:00Z&ets=2026-10-24T00:00Z&format=csv"
)
LAST_RUN_NEEDED = "2026-10-22 12:00:00"  # the run that serves the last local day, 2026-10-23

# --- Which forecast run to use -------------------------------------------------------------

RUN_HOUR_UTC = 12  # use the latest run issued at or before 12:00 UTC on the day before
MAX_RUN_AGE = pd.Timedelta(hours=24)  # an older run means runs are missing: leave NaN

RAW_DIR = ROOT / "data" / "raw" / "weather"
OUT_PATH = ROOT / "data" / "derived" / "dataset_weather.parquet"


def download(station: str, raw_dir: Path = RAW_DIR) -> Path:
    """Save one station's forecast archive as <raw_dir>/<station>.csv (skip if present).

    The file is saved under a temporary name first and renamed only after it passes the
    checks, so a failed or partial download is retried next time instead of reused.
    """
    path = raw_dir / f"{station}.csv"
    if path.exists():
        return path

    raw_dir.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")

    url = MOS_URL.format(station=station)
    with urllib.request.urlopen(url, timeout=300) as response:
        partial.write_bytes(response.read())

    # Check it is real forecast data that reaches the end of the study.
    text = partial.read_text()
    last_line = text.rstrip().rsplit("\n", 1)[-1]
    last_run = last_line.split(",", 1)[0]
    looks_complete = text.startswith("runtime,ftime") and last_run >= LAST_RUN_NEEDED

    if not looks_complete:
        partial.unlink()
        raise ValueError(f"Bad or incomplete download for {station} (last run {last_run!r})")

    partial.rename(path)
    return path


def read_station(path: Path) -> pd.DataFrame:
    """Read one station file. Returns runtime, ftime (both UTC), temp_c, dewpoint_c.

    The file is in °F. A run archived twice (identical rows) is kept once; two different
    values for the same run and hour raise an error.
    """
    raw = pd.read_csv(path, usecols=["runtime", "ftime", "tmp", "dpt"])
    raw = raw.drop_duplicates()

    if raw.duplicated(["runtime", "ftime"]).any():
        raise ValueError(f"{path.name}: same run and hour with different values")

    return pd.DataFrame({
        "runtime": pd.to_datetime(raw["runtime"], utc=True),
        "ftime": pd.to_datetime(raw["ftime"], utc=True),
        "temp_c": (raw["tmp"] - 32) * 5 / 9,
        "dewpoint_c": (raw["dpt"] - 32) * 5 / 9,
    })


def to_hourly(mos: pd.DataFrame) -> pd.DataFrame:
    """Fill each run's 3-hourly forecasts to hourly, with straight lines between points.

    Fills within one run only (never mixing runs), and only between forecast times
    (nothing before a run's first value or after its last).
    """
    # Hours ahead of the run, e.g. 6, 9, 12, ...
    hours_ahead = (mos["ftime"] - mos["runtime"]) // pd.Timedelta(hours=1)
    mos = mos.assign(hours_ahead=hours_ahead)

    filled = []
    for column in ("temp_c", "dewpoint_c"):
        # One row per run, one column per hour ahead.
        wide = mos.pivot(index="runtime", columns="hours_ahead", values=column)

        # Add the missing in-between hours, then fill them along each row.
        every_hour = range(wide.columns.min(), wide.columns.max() + 1)
        wide = wide.reindex(columns=every_hour)
        wide = wide.interpolate(axis=1, limit_area="inside")

        filled.append(wide.stack().rename(column))

    hourly = pd.concat(filled, axis=1).reset_index()
    hourly["ftime"] = hourly["runtime"] + pd.to_timedelta(hourly["hours_ahead"], unit="h")

    return hourly[["runtime", "ftime", "temp_c", "dewpoint_c"]]


def ba_weather(hourly: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Population-weighted temp_c and dewpoint_c per (ba, runtime, ftime).

    `hourly` maps station -> output of to_hourly. A (runtime, ftime) pair is kept only if
    every station of the BA has both values.
    Returns ba, runtime, ftime, temp_c, dewpoint_c.
    """
    per_ba = []

    for ba, stations in STATIONS.items():
        total_population = sum(stations.values())

        # Stack the BA's stations, each with its share of the population.
        station_rows = []
        for station, population in stations.items():
            rows = hourly[station].dropna(subset=["temp_c", "dewpoint_c"])
            rows = rows.assign(weight=population / total_population)
            station_rows.append(rows)
        rows = pd.concat(station_rows)

        # Weighted average = sum of (weight x value).
        rows["temp_c"] *= rows["weight"]
        rows["dewpoint_c"] *= rows["weight"]
        averaged = rows.groupby(["runtime", "ftime"]).agg(
            temp_c=("temp_c", "sum"),
            dewpoint_c=("dewpoint_c", "sum"),
            n_stations=("weight", "size"),
        )

        # Keep only hours where every station reported.
        complete = averaged[averaged["n_stations"] == len(stations)]
        complete = complete.drop(columns="n_stations").reset_index()
        per_ba.append(complete.assign(ba=ba))

    combined = pd.concat(per_ba, ignore_index=True)
    return combined[["ba", "runtime", "ftime", "temp_c", "dewpoint_c"]]


def issue_cutoff(local_date: pd.Series) -> pd.Series:
    """Latest allowed run time for forecasting local day D: 12:00 UTC on D minus 1 day."""
    midnight_utc = pd.to_datetime(local_date).dt.tz_localize("UTC")
    return midnight_utc - pd.Timedelta(hours=24 - RUN_HOUR_UTC)


def attach_weather(dataset: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Add weather_run, temp_c, and dewpoint_c to each dataset row.

    For each (ba, local_date), use the latest run issued at or before issue_cutoff, then
    take that run's value at ftime == utc_end (the reading at the end of the hour).
    Rows with no such value, or whose newest run is over MAX_RUN_AGE old, get NaN.
    """
    # merge_asof needs the "by" column to have the same type on both sides.
    weather = weather.astype({"ba": str})

    # 1. One row per (BA, day), with the latest allowed run time.
    days = dataset[["ba", "local_date"]].drop_duplicates().astype({"ba": str})
    days["cutoff"] = issue_cutoff(days["local_date"])
    days = days.sort_values("cutoff")

    # 2. For each day, pick the latest run at or before the cutoff (within MAX_RUN_AGE).
    runs = weather[["ba", "runtime"]].drop_duplicates().sort_values("runtime")
    chosen = pd.merge_asof(
        days,
        runs,
        left_on="cutoff",
        right_on="runtime",
        by="ba",
        direction="backward",
        tolerance=MAX_RUN_AGE,
    )
    chosen = chosen[["ba", "local_date", "runtime"]].rename(columns={"runtime": "weather_run"})

    # 3. Attach the chosen run to every hour, then that run's forecast for the hour.
    out = dataset.astype({"ba": str})
    out = out.merge(chosen, on=["ba", "local_date"], how="left")
    out = out.merge(
        weather.rename(columns={"runtime": "weather_run", "ftime": "utc_end"}),
        on=["ba", "weather_run", "utc_end"],
        how="left",
    )

    return out.astype({"ba": dataset["ba"].dtype})


def main() -> None:
    # Download (or reuse) every station and fill it to hourly.
    hourly = {}
    for stations in STATIONS.values():
        for station in stations:
            hourly[station] = to_hourly(read_station(download(station)))

    dataset = pd.read_parquet(DATASET_PATH)
    dataset = attach_weather(dataset, ba_weather(hourly))

    # There are no gaps today; a new one must be looked at, not passed on silently.
    n_missing = dataset["temp_c"].isna().sum()
    if n_missing:
        raise ValueError(f"{n_missing:,} rows have no weather forecast")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {len(dataset):,} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
