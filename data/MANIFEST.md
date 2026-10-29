# Data manifest

Inventory of `data/raw/` as found on 2026-10-28. Files are unmodified downloads; nothing was cleaned or imputed.
All numbers below were measured from the files by a read-only, stdlib-only Python pass (`csv`, `hashlib`,
`zipfile`). That script is not in the repo; the counts should be reproduced by the project loader before any
conclusion depends on them.

## Files

Modified date is the local file mtime (assumed to be the download date). SHA-256 shows the first 12 hex digits.
UTC range is `UTC Time at End of Hour` (min / max over all rows).

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

Across all 12 balance files: 67 distinct BAs, 13 distinct `Region` values
(CAL, CAR, CENT, FLA, MIDA, MIDW, NE, NW, NY, SE, SW, TEN, TEX).

## Schema checks

- All 12 files contain `Balancing Authority`, `UTC Time at End of Hour`, `Demand (MW)`,
  `Demand Forecast (MW)`, and `Region`.
- 44 columns in 2021 H1 through 2024 H1; 65 columns from 2024 H2 on. `Region` is column 44 and 65 respectively,
  so columns must be selected by name, not position.
- No ragged rows (every row has the header's column count). No non-numeric values in the two demand columns.

## Timestamps

- Format: `MM/DD/YYYY H:MM:SS AM|PM`, 12-hour clock, no zone suffix (e.g. `01/01/2021 7:00:00 AM`).
  Parsed with `%m/%d/%Y %I:%M:%S %p`: **0 failures** in every file.
- Files are cut on **local** date per BA (`Data Date`), not on UTC. So adjacent files' UTC ranges overlap by a
  few hours (e.g. 2021 H1 ends 2021-07-01 07:00 UTC, 2021 H2 starts 2021-07-01 05:00 UTC).

## Duplicates

- Duplicate (BA, UTC) pairs within each file: **0** in all 12.
- Duplicate (BA, UTC) pairs across files: **0**. The UTC overlap above does not produce repeated keys.
- No daylight-saving duplicates were found (they would show up as within-file duplicates).

## Missing and non-positive values

Missing = empty field. Non-positive = parsed value <= 0. Percentages are of rows in the file (not of
calendar hours).

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

The 2026 H2 row count, column count, BA count, and missing percentages match the owner's earlier manual
inspection (166,872 / 65 / 60 / 12.49% / 12.31%).

## Regions

- No BA has more than one `Region` value, within any file or across all 12 files.
- Every BA in the files appears in the reference workbook's `BAs` sheet, and its file `Region` equals the
  workbook's `Region/Country Code` for all 67 BAs.

## Reference workbook (`eia930-reference-tables.xlsx`)

Sheets: `BAs` (81 data rows), `Regions`, `BA Subregions`, `BA Connections`, `Energy Sources`,
`Date Energy Sources Available`, `Notes`.

- **BA region source: sheet `BAs`, column `Region/Country Code`.** The same sheet has `Time Zone`,
  `Generation Only BA`, `Active BA`, `Activation Date`, `Retirement Date`.
- `Regions` maps region code to name and time zone.
- 14 BAs in the workbook never appear in these files (AESO, BCHA, CEN, CFE, EEI, GRMA, HQT, IESO, MHEB, NBSO,
  NSB, OVEC, SPC, WAUE); mostly Canadian/Mexican or retired, not checked individually.

## Study window coverage (hours ending 2021-01-01 01:00 through 2026-10-24 00:00 UTC)

- Calendar count of the window: **50,928 hours** (reproduced).
- **Not fully covered.** The union of all files' stamps misses 5 window hours: ending 2021-01-01 01:00-05:00 UTC.
  Per BA it is worse, because a BA's first row is its local Jan 1 hour 1: the first 5 (Eastern), 6 (Central),
  7 (Mountain), or 8 (Pacific) window hours are absent for every BA. Those hours are in the 2020 H2 file,
  which is not in `data/raw`.
- Apart from those start hours, the 57 BAs present throughout have no absent window rows (no UTC gaps).
- 10 BAs do not span the window (first / last UTC stamp; workbook dates in brackets):

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

- BAs with no `Demand (MW)` value in any row of a file (all are generation-only per the workbook): AVRN, DEAA,
  GRID, GWA, SEPA, YAD in every file; GLHB, GRIF, HGMA, WWA while present; SIKE from 2025 H1.

## Trailing gaps at file ends

- **2026 H2:** the file has rows for local 2026-10-24, but for all **53** BAs that report demand, all 24 demand
  values on local 10/24 are missing (1,272 rows). `Demand Forecast (MW)` is present on all 1,272 of those rows.
  Each of the 53 BAs' last reported demand is local 10/24 00:00 (end of local Oct 23). The other 7 BAs in the
  file report no demand at all and have no 10/24 rows.
- **Other boundaries:** no market-wide trailing gap. Single BAs miss demand for the whole last local day(s):
  - FMPP: 12/31/2022, 12/31/2023, 12/31/2024 (last day of three H2 files)
  - JEA: 12/31/2024
  - IID: 06/29/2024; SCEG: 06/30/2024
  - The other last-demand stamps before a file's end are retirements (AEC 2021-09-01; WACM, WAUW 2026-04-01).

## Surprising (separate from the facts above)

1. **The window start cannot be covered by these 12 files.** Protocol expects 8,760 hours for 2021 per BA, but
   every BA lacks its first 5-8 hours (local Dec 31, 2020, in the 2020 H2 file). Either add 2020 H2 or count them
   as missing; under the protocol as written they count as missing (tiny vs a 5% budget, but the acceptance test
   on expected hours passes while rows_present will not equal it).
2. **53, not 48, BAs miss local Oct 24.** The brief says 48 BAs miss exactly 24 values. Measured: 53 miss all 24
   hours of local 10/24. Likely the 48 counted BAs whose *total* file missing was exactly 24 (the other 5 have
   additional gaps); not verified.
3. **Forecasts exist on the day demand is missing** (local Oct 24). Consistent with a day-ahead forecast issued
   before the actuals are reported. Says nothing yet about issue time.
4. **The file ends at local Oct 24, not Oct 23.** Last UTC stamp is 2026-10-25 07:00. The window cut at
   2026-10-24 00:00 UTC is still correct, but it also drops hours ending 01:00-07:00 UTC Oct 24 that *do* have
   demand for Central/Mountain/Pacific BAs (local Oct 23 evening).
5. **Non-positive forecasts jumped** from tens per file to 1,074 (2025 H2) and 2,120 (2026 H1). By year, the
   largest counts are SPA (502 in 2025, 1,377 in 2026), FMPP (518 in 2025), CPLW (600 in 2026), CPLE (480 in 2026).
   CPLE and FMPP are mid-size BAs; this may matter for forecast coverage under the protocol.
6. **WACM and WAUW retired on 2026-04-01; BHBA and SWPW started that day,** all in region NW. WACM/WAUW will fail
   2026 coverage under "every year used"; BHBA/SWPW fail all earlier years.
7. **FMPP misses its last local day in three consecutive H2 files** (Dec 31, 2022-2024). A BA-specific pattern
   worth watching if FMPP is near the cutoff.
8. The workbook's file name is `eia930-reference-tables.xlsx`, not `EIA930_Reference_Tables.xlsx` as in
   `data/README.md`.

## Not verified

- That these files match EIA's current published versions (EIA revises data; no published checksums found or checked).
- DST handling of `Local Time at End of Hour` (`Data Date` was later checked row by row for the 10 selected
  BAs: commit 62f45b6).
- Why the 2026 H2 demand is missing on Oct 24 (assumed reporting lag, not confirmed).
