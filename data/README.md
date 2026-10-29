# Data

Nothing in this folder is committed except this file (see `.gitignore`).

## Sources

**EIA-930 Hourly and Daily Balancing Authority Operations (U.S. Energy Information Administration)**
- Six-month files, from July 2015 (second half) onward, in `balance`, `interchange`, and `subregion` flavors.
- This project uses the **balance** files only.
- EIA's page: https://www.eia.gov/electricity/930-content/about.html
- A Zenodo catalog listing also offers six-month ZIPs (`eia930-2015half2.zip` through `eia930-2026half2.zip`,
  about 15-20 MB each, per the author's inspection of the catalog). Confirm the record, its license, and that it
  matches EIA's files before relying on it.
- EIA's terms of use were not stated on the pages read. Confirm before publishing derived data.

**Open-Meteo (weather)**
- Free for non-commercial use, data licensed CC BY 4.0 with attribution ("Weather data by Open-Meteo.com").
- Historical reanalysis (ERA5) back to 1940, and a historical forecast archive from 2021. Re-check the current
  terms and coverage for the chosen locations.

## How to get the balance files (manual)

EIA publishes no stable direct link on its about page, so download through the dashboard:

1. Open the EIA Hourly Electric Grid Monitor dashboard.
2. Click the Download Data icon (upper right), then the Six-Month Files column.
3. Choose each period and the **Balance** file. Needed: 2021 H1 through 2026 H2 (12 files). Also grab
   the reference tables: https://www.eia.gov/electricity/930-content/EIA930_Reference_Tables.xlsx
   (the copy in `data/raw/` is named `eia930-reference-tables.xlsx`)
4. Put them, unmodified, in `data/raw/`. Record file names, sizes, and download date in `data/MANIFEST.md`
   (commit the manifest; the data stays ignored).

Measured facts for every file are in `MANIFEST.md`.
See `docs/project_brief.md` for open questions.
