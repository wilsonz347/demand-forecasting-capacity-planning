# Data

Only this file and `MANIFEST.md` are committed. Everything else here is git-ignored.

## Sources

**EIA-930 balance files** (U.S. Energy Information Administration, public domain)
- About the data: https://www.eia.gov/electricity/930-content/about.html
- We use the six-month **balance** files, 2021 H1 to 2026 H2, plus the reference tables.

**Weather forecasts**: NWS airport forecasts (GFS MOS), archived by the Iowa Environmental Mesonet
(https://mesonet.agron.iastate.edu/mos/). Public domain; credit IEM.

## Getting the files

**EIA (by hand):**
1. Open the EIA Hourly Electric Grid Monitor, click Download Data, then Six-Month Files.
2. Download the **Balance** file for each half-year, 2021 H1 to 2026 H2 (12 files).
3. Download the reference tables: https://www.eia.gov/electricity/930-content/EIA930_Reference_Tables.xlsx
   (saved here as `eia930-reference-tables.xlsx`).
4. Put them, unchanged, in `data/raw/`. Note new files in `MANIFEST.md`.

**Weather (automatic):** `uv run python -m demand_forecasting.weather` downloads each airport into
`data/raw/weather/`.

## Building everything

```
uv run python -m demand_forecasting.ba_selection   # BA selection tables
uv run python -m demand_forecasting.build_dataset  # data/derived/dataset.parquet
uv run python -m demand_forecasting.weather        # data/derived/dataset_weather.parquet
uv run python -m demand_forecasting.baselines      # baseline scores
```
