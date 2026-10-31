# Data manifest

What is in `data/raw/`, as downloaded on 2026-10-28. Files are unchanged. Counts were measured by a one-off
script; the project's loader reproduces the totals (3,143,756 rows, 67 BAs).

## Files

SHA-256 shows the first 12 characters. UTC range is `UTC Time at End of Hour`.

| File | Bytes | SHA-256 | Modified | Rows | Cols | BAs | First UTC | Last UTC |
|---|---:|---|---|---:|---:|---:|---|---|
| `eia930-2021half1-balance.csv` | 43,073,764 | `40b183f333e0` | 2026-10-28 | 277,964 | 44 | 64 | 2021-01-01 06:00 | 2021-07-01 07:00 |
| `eia930-2021half2-balance.csv` | 43,438,192 | `66afadcab686` | 2026-10-28 | 279,747 | 44 | 64 | 2021-07-01 05:00 | 2022-01-01 08:00 |
| `eia930-2022half1-balance.csv` | 42,567,904 | `d3d315a0c29d` | 2026-10-28 | 273,621 | 44 | 63 | 2022-01-01 06:00 | 2022-07-01 07:00 |
| `eia930-2022half2-balance.csv` | 42,909,865 | `267575c29ef4` | 2026-10-28 | 275,330 | 44 | 63 | 2022-07-01 05:00 | 2023-01-01 08:00 |
| `eia930-2023half1-balance.csv` | 41,981,693 | `a0e14e9c07ab` | 2026-10-28 | 269,278 | 44 | 62 | 2023-01-01 06:00 | 2023-07-01 07:00 |
| `eia930-2023half2-balance.csv` | 42,574,041 | `c719fc1b513e` | 2026-10-28 | 272,378 | 44 | 62 | 2023-07-01 05:00 | 2024-01-01 08:00 |
| `eia930-2024half1-balance.csv` | 41,742,812 | `26768c495c3b` | 2026-10-28 | 266,398 | 44 | 61 | 2024-01-01 06:00 | 2024-07-01 07:00 |
| `eia930-2024half2-balance.csv` | 47,928,993 | `a602a8e577cf` | 2026-10-28 | 269,426 | 65 | 61 | 2024-07-01 05:00 | 2025-01-01 08:00 |
| `eia930-2025half1-balance.csv` | 47,565,054 | `fac4bb991dfa` | 2026-10-28 | 264,934 | 65 | 62 | 2025-01-01 06:00 | 2025-07-01 07:00 |
| `eia930-2025half2-balance.csv` | 48,256,021 | `1146158b9724` | 2026-10-28 | 267,218 | 65 | 61 | 2025-07-01 05:00 | 2026-01-01 08:00 |
| `eia930-2026half1-balance.csv` | 47,107,225 | `1b3eaf7b0af0` | 2026-10-28 | 260,590 | 65 | 62 | 2026-01-01 06:00 | 2026-07-01 07:00 |
| `eia930-2026half2-balance.csv` | 30,325,808 | `bb941fcb7b5c` | 2026-10-28 | 166,872 | 65 | 60 | 2026-07-01 05:00 | 2026-10-25 07:00 |
| `eia930-reference-tables.xlsx` | 45,259 | `9d4af4996f13` | 2026-10-28 | | | | | |

## Checks

- All 12 files have the 5 columns we use. Two layouts: 44 columns (to 2024 H1) and 65 (from 2024 H2), so
  columns are read by name.
- Timestamps look like `01/01/2021 7:00:00 AM` (UTC, no zone). All parse.
- No duplicate (BA, hour) pairs, within or across files. Files are cut by local date, so their UTC ranges
  overlap by a few hours.
- 67 BAs, 13 regions. Each BA has one region, matching the reference tables (`BAs` sheet).

## Missing and invalid values

Share of rows in each file.

| File | Demand missing | Demand <= 0 | Forecast missing | Forecast <= 0 |
|---|---:|---:|---:|---:|
| 2021 H1 | 44,410 (15.98%) | 343 | 44,383 (15.97%) | 68 |
| 2021 H2 | 44,309 (15.84%) | 195 | 44,683 (15.97%) | 10 |
| 2022 H1 | 44,232 (16.17%) | 53 | 44,054 (16.10%) | 10 |
| 2022 H2 | 41,288 (15.00%) | 40 | 45,001 (16.34%) | 29 |
| 2023 H1 | 39,162 (14.54%) | 77 | 39,499 (14.67%) | 38 |
| 2023 H2 | 38,663 (14.19%) | 77 | 38,627 (14.18%) | 56 |
| 2024 H1 | 35,156 (13.20%) | 104 | 35,328 (13.26%) | 66 |
| 2024 H2 | 35,590 (13.21%) | 128 | 35,950 (13.34%) | 73 |
| 2025 H1 | 34,929 (13.18%) | 98 | 35,108 (13.25%) | 50 |
| 2025 H2 | 33,579 (12.57%) | 142 | 33,787 (12.64%) | 1,074 |
| 2026 H1 | 32,665 (12.54%) | 145 | 32,704 (12.55%) | 2,120 |
| 2026 H2 | 20,844 (12.49%) | 54 | 20,534 (12.31%) | 472 |

## Coverage of the study window

- Window: hours ending 2021-01-01 01:00 to 2026-10-24 00:00 UTC (50,928 hours).
- Every BA misses its first 5-8 window hours (local Dec 31, 2020, in a file we don't have).
- Otherwise, the 57 BAs present throughout have no missing hours.
- 10 BAs start or stop during the window:

| BA | First UTC | Last UTC | Workbook |
|---|---|---|---|
| AEC | 2021-01-01 07:00 | 2021-09-01 05:00 | retired 9/1/2021 |
| GLHB | 2021-01-01 07:00 | 2022-09-01 05:00 | generation-only, retired 9/1/2022 |
| GRIF | 2021-01-01 08:00 | 2023-11-01 07:00 | generation-only, retired 11/1/2023 |
| HGMA | 2021-01-01 08:00 | 2025-06-01 07:00 | generation-only, retired 6/1/2025 |
| WWA | 2021-01-01 08:00 | 2025-10-01 06:00 | generation-only, retired 10/1/2025 |
| WACM | 2021-01-01 08:00 | 2026-04-01 07:00 | retired 4/1/2026 |
| WAUW | 2021-01-01 08:00 | 2026-04-01 06:00 | retired 4/1/2026 |
| SIKE | 2025-06-01 06:00 | 2026-10-24 05:00 | generation-only, activated 6/1/2025 |
| BHBA | 2026-04-01 07:00 | 2026-10-25 06:00 | activated 4/1/2026 |
| SWPW | 2026-04-01 06:00 | 2026-10-25 05:00 | activated 4/1/2026 |

- Generation-only BAs report no demand: AVRN, DEAA, GLHB, GRID, GRIF, GWA, HGMA, SEPA, SIKE, WWA, YAD.

## Gaps at file ends

- **Last file:** local Oct 24, 2026 has no demand for any of the 53 BAs that report it (forecasts are
  present). This day is outside the study window.
- **Other files:** no common gap. A few BAs miss their last day: FMPP (Dec 31 of 2022, 2023, 2024), JEA
  (Dec 31, 2024), IID (Jun 29, 2024), SCEG (Jun 30, 2024).

## Worth knowing

- Forecasts <= 0 jumped in 2025 H2 (1,074) and 2026 H1 (2,120), mostly SPA, FMPP, CPLW, CPLE.
- WACM and WAUW stopped on 2026-04-01; BHBA and SWPW started that day (all in region NW).

## Not checked

- Whether these files match EIA's current versions (EIA revises data).
- Why demand is missing on Oct 24, 2026 (probably a reporting delay).
