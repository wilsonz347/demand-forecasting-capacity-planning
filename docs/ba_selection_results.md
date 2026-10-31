# BA selection results

Made by `uv run python -m demand_forecasting.ba_selection` (commit `bfc6f30`), following the
[protocol](ba_selection_protocol.md). Recorded 2026-10-29, before any model was fit.

## Result

**37 BAs qualify. The top 10 are in 10 different regions, so no swaps were needed.**

| Rank | BA | Region | Mean demand (MW) | 2021 hours absent | Demand <= 0 | Forecast <= 0 | Rows outside window |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | PJM | MIDA | 174,324 | 5 | 0 | 0 | 28 |
| 2 | MISO | MIDW | 74,694 | 5 | 0 | 0 | 29 |
| 3 | ERCO | TEX | 51,978 | 6 | 0 | 0 | 29 |
| 4 | SOCO | SE | 27,283 | 6 | 0 | 0 | 29 |
| 5 | CISO | CAL | 25,613 | 8 | 0 | 0 | 31 |
| 6 | TVA | TEN | 19,178 | 6 | 5 | 0 | 29 |
| 7 | NYIS | NY | 17,226 | 5 | 11 | 115 | 28 |
| 8 | ISNE | NE | 13,169 | 5 | 0 | 0 | 28 |
| 9 | DUK | CAR | 12,323 | 5 | 0 | 24 | 28 |
| 10 | BPAT | NW | 6,741 | 8 | 0 | 0 | 31 |

- *2021 hours absent:* local Dec 31, 2020 is not in our files. Counted as missing.
- *<= 0:* invalid hours inside the window (kept in the raw data).
- *Rows outside window:* hours after 2026-10-24 00:00 UTC.

## Inputs

| Item | Value |
|---|---|
| Window (UTC, hour ending) | 2021-01-01 01:00 to 2026-10-24 00:00, 50,928 hours |
| Years | 2021-2025 full, 2026 to Oct 23 |
| Data | 12 EIA-930 balance files, listed in [`data/MANIFEST.md`](../data/MANIFEST.md) |
| Region source | `Region` column of the balance files (matches the reference tables for all 67 BAs; checked by hand) |
| Rules | 95% valid demand and forecast in every year; top 10 by mean valid demand; at least 4 regions |
| Excluded | AVA, FPC, GVL, LGEE, PSEI, SEC, SPA, TEPC (revision 1) |

## Near the cutoff

Ranks 6-15. All are well above 95%, so the cut is set by size, not data quality.

| Rank | BA | Region | Mean demand (MW) | Lowest yearly demand coverage | Lowest yearly forecast coverage |
|---:|---|---|---:|---:|---:|
| 6 | TVA | TEN | 19,178 | 99.9% | 99.8% |
| 7 | NYIS | NY | 17,226 | 99.9% | 99.5% |
| 8 | ISNE | NE | 13,169 | 99.9% | 99.9% |
| 9 | DUK | CAR | 12,323 | 99.7% | 99.7% |
| 10 | BPAT | NW | 6,741 | 99.9% | 99.9% |
| 11 | PACE | NW | 5,917 | 99.9% | 98.7% |
| 12 | PSCO | NW | 5,233 | 99.6% | 99.9% |
| 13 | NEVP | NW | 4,623 | 99.8% | 99.6% |
| 14 | AZPS | SW | 4,052 | 99.8% | 99.6% |
| 15 | SC | CAR | 3,048 | 98.6% | 98.6% |

## Large BAs that did not qualify

Shown so the effect of the rules is visible. The rules were not changed.

| BA | Mean demand (MW) | Would rank about | Why not |
|---|---:|---:|---|
| SWPP | 33,003 | 4 | forecast 93.2% in 2026 |
| FPL | 16,298 | 8 | demand 93.7% in 2022 |
| CPLE | 7,075 | 10 | forecast 93.2% in 2026 (non-positive forecasts) |
| FPC | 6,569 | 11 | excluded (EIA forecast caveat) |

## Effect of gaps

- **Start:** every BA misses its first 5-8 hours (about 0.1% of 2021). Counted as missing.
- **End:** local Oct 24, 2026 has no demand for any BA. It is outside the window.
- **Other gaps:** the 10 selected have no absent rows after the start, but some hours are missing or <= 0
  (lowest yearly coverage 99.4%):

  | BA | Window-start hours | Invalid demand hours | Invalid forecast hours |
  |---|---:|---:|---:|
  | PJM | 5 | 142 | 144 |
  | MISO | 5 | 66 | 72 |
  | ERCO | 6 | 48 | 48 |
  | SOCO | 6 | 0 | 5 |
  | CISO | 8 | 136 | 120 |
  | TVA | 6 | 5 | 21 |
  | NYIS | 5 | 11 | 115 |
  | ISNE | 5 | 5 | 0 |
  | DUK | 5 | 25 | 50 |
  | BPAT | 8 | 0 | 0 |

- **Duplicates:** none. (The loader stops on any duplicate, which is stricter than the protocol.)

## Full coverage table

Valid demand % / valid forecast % per year. Reasons are written by hand. Full data:
`data/derived/ba_selection/coverage.csv` (rebuild with the command above).

| BA | Region | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Status | Reason |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| PJM | MIDA | 99.9 / 99.9 | 99.7 / 99.7 | 99.7 / 99.7 | 99.5 / 99.5 | 99.7 / 99.7 | 99.7 / 99.7 | selected (rank 1) |  |
| MISO | MIDW | 99.9 / 99.7 | 100.0 / 100.0 | 100.0 / 100.0 | 99.7 / 99.7 | 99.7 / 100.0 | 99.8 / 99.7 | selected (rank 2) |  |
| ERCO | TEX | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 99.5 / 99.5 | 100.0 / 100.0 | selected (rank 3) |  |
| SOCO | SE | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | selected (rank 4) |  |
| CISO | CAL | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 99.5 / 99.4 | 99.5 / 99.5 | 99.6 / 99.7 | selected (rank 5) |  |
| TVA | TEN | 99.9 / 99.9 | 100.0 / 99.8 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | selected (rank 6) |  |
| NYIS | NY | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 99.5 | 100.0 / 99.5 | 99.9 / 99.7 | selected (rank 7) |  |
| ISNE | NE | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | selected (rank 8) |  |
| DUK | CAR | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 99.7 / 99.7 | 100.0 / 99.7 | selected (rank 9) |  |
| BPAT | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | selected (rank 10) |  |
| PACE | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 98.7 | eligible (rank 11) |  |
| PSCO | NW | 99.9 / 99.9 | 100.0 / 100.0 | 99.6 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 12) |  |
| NEVP | NW | 99.9 / 99.6 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 99.8 / 100.0 | 99.9 / 100.0 | eligible (rank 13) |  |
| AZPS | SW | 99.9 / 99.6 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 99.8 / 100.0 | eligible (rank 14) |  |
| SC | CAR | 99.7 / 99.7 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 99.7 | 99.9 / 100.0 | 98.6 / 98.6 | eligible (rank 15) |  |
| SCEG | CAR | 99.9 / 98.6 | 100.0 / 100.0 | 99.4 / 99.4 | 99.5 / 99.4 | 99.2 / 95.6 | 95.9 / 95.9 | eligible (rank 16) |  |
| LDWP | CAL | 99.7 / 98.3 | 100.0 / 100.0 | 99.4 / 99.2 | 100.0 / 100.0 | 100.0 / 99.7 | 100.0 / 99.3 | eligible (rank 17) |  |
| AECI | MIDW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 18) |  |
| PGE | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 19) |  |
| TEC | FLA | 99.7 / 99.7 | 100.0 / 100.0 | 99.9 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 20) |  |
| PACW | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 21) |  |
| IPCO | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 22) |  |
| BANC | CAL | 99.9 / 99.4 | 100.0 / 99.5 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 99.5 | 100.0 / 99.4 | eligible (rank 23) |  |
| PNM | SW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 24) |  |
| JEA | FLA | 99.9 / 98.8 | 100.0 / 100.0 | 100.0 / 100.0 | 99.8 / 96.9 | 99.9 / 100.0 | 100.0 / 100.0 | eligible (rank 25) |  |
| NWMT | NW | 99.9 / 96.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 26) |  |
| SCL | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 99.7 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 27) |  |
| WALC | SW | 99.6 / 99.6 | 100.0 / 100.0 | 100.0 / 99.9 | 99.7 / 99.6 | 100.0 / 100.0 | 99.8 / 99.8 | eligible (rank 28) |  |
| EPE | SW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 99.3 / 99.3 | eligible (rank 29) |  |
| GCPD | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 99.5 | eligible (rank 30) |  |
| TPWR | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 31) |  |
| IID | CAL | 99.9 / 99.6 | 100.0 / 99.7 | 99.4 / 99.2 | 97.7 / 98.9 | 98.1 / 98.6 | 99.3 / 99.6 | eligible (rank 32) |  |
| TIDC | CAL | 98.7 / 99.1 | 99.8 / 100.0 | 100.0 / 100.0 | 99.9 / 100.0 | 99.7 / 100.0 | 99.8 / 100.0 | eligible (rank 33) |  |
| TAL | FLA | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 34) |  |
| DOPD | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 35) |  |
| CHPD | NW | 99.6 / 99.6 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | eligible (rank 36) |  |
| HST | FLA | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 99.7 | 100.0 / 99.4 | 100.0 / 99.3 | eligible (rank 37) |  |
| AEC | SE | 66.6 / 66.5 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | retired 2021-09 |
| AVA | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 99.7 | no | excluded (EIA forecast caveat) |
| AVRN | NW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
| BHBA | NW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 48.6 / 48.6 | no | started 2026-04 |
| CPLE | CAR | 99.9 / 99.9 | 99.7 / 99.7 | 100.0 / 100.0 | 100.0 / 100.0 | 99.7 / 99.7 | 100.0 / 93.2 | no | forecast < 95% in 2026 |
| CPLW | CAR | 99.9 / 99.7 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 99.7 / 99.7 | 100.0 / 91.6 | no | forecast < 95% in 2026 |
| DEAA | SW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
| FMPP | FLA | 99.9 / 99.9 | 99.8 / 100.0 | 99.7 / 100.0 | 99.7 / 100.0 | 99.9 / 94.1 | 99.9 / 100.0 | no | forecast < 95% in 2025 |
| FPC | FLA | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 99.7 / 99.7 | 100.0 / 99.7 | no | excluded (EIA forecast caveat) |
| FPL | FLA | 99.9 / 99.6 | 93.7 / 100.0 | 98.9 / 99.2 | 99.1 / 99.7 | 100.0 / 99.7 | 100.0 / 100.0 | no | demand < 95% in 2022 |
| GLHB | MIDW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
| GRID | NW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
| GRIF | SW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
| GVL | FLA | 99.8 / 97.3 | 99.8 / 100.0 | 100.0 / 100.0 | 99.9 / 100.0 | 98.6 / 99.2 | 97.0 / 99.0 | no | excluded (EIA forecast caveat) |
| GWA | NW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
| HGMA | SW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
| LGEE | MIDW | 99.3 / 99.1 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 99.8 / 100.0 | no | excluded (EIA forecast caveat) |
| PSEI | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | no | excluded (EIA forecast caveat) |
| SEC | FLA | 93.9 / 99.7 | 99.1 / 99.7 | 98.3 / 99.7 | 99.1 / 99.4 | 98.0 / 99.4 | 98.2 / 99.0 | no | excluded (EIA forecast caveat) |
| SEPA | SE | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
| SIKE | MIDW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
| SPA | CENT | 99.9 / 99.9 | 98.0 / 98.1 | 99.8 / 100.0 | 99.9 / 96.7 | 99.9 / 93.7 | 99.4 / 80.7 | no | excluded (EIA forecast caveat) |
| SRP | SW | 99.6 / 99.9 | 100.0 / 53.6 | 100.0 / 95.8 | 99.5 / 99.5 | 100.0 / 100.0 | 100.0 / 100.0 | no | forecast < 95% in 2022 |
| SWPP | CENT | 99.9 / 99.7 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 99.7 | 99.7 / 93.2 | no | forecast < 95% in 2026 |
| SWPW | NW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 69.5 / 63.1 | no | started 2026-04 |
| TEPC | SW | 91.2 / 99.9 | 100.0 / 100.0 | 99.2 / 99.1 | 99.7 / 99.7 | 100.0 / 100.0 | 99.7 / 99.7 | no | excluded (EIA forecast caveat) |
| WACM | NW | 99.8 / 97.8 | 99.9 / 99.9 | 99.9 / 99.2 | 100.0 / 100.0 | 99.9 / 100.0 | 28.5 / 28.5 | no | retired 2026-04 |
| WAUW | NW | 99.9 / 99.9 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 100.0 / 100.0 | 30.5 / 30.5 | no | retired 2026-04 |
| WWA | NW | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
| YAD | CAR | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | no | reports no demand (generation-only) |
