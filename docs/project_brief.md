# Project brief

## One-line pitch

Forecast hourly electricity demand with calibrated prediction intervals, and test whether the forecast beats the operators' own on the decision of how much capacity to commit.

## Why this project

- General: same structure as inventory, staffing, and cloud-capacity planning.
- Single, clean, free source with a built-in professional benchmark (the operators' day-ahead forecast).
- Substantive: time-series validation, probabilistic forecasting, calibration, and a decision layer, with several places where careless work produces wrong answers (leakage, time zones, imputed targets).

## Scope

**In scope (MVP)**
- About 5 to 10 balancing authorities (BAs), chosen by a completeness rule set before modeling.
- Time-ordered splits; baselines first; regularized linear and gradient-boosted quantile models.
- Cost simulation with a swept cost ratio; block-bootstrap uncertainty; short written report.

**Extensions (only if time allows)**
- More BAs; conformal or adaptive calibration; extreme-day and seasonal analysis; a window using archived forecast weather.

**Out of scope**
- Deep learning, LLMs, dashboards; interchange, subregion, or generator-level files; price, dispatch, or unit-commitment modeling; causal claims.

## Verified data facts

From the owner's manual inspection of `eia930-2026half2-balance.csv` (July 1 to Oct 24, 2026). Claude has not independently downloaded this file; the egress proxy blocks the host.

- 166,872 rows, 65 columns, about 30 MB, 60 BAs.
- Expected 60 x 2,784 hours = 167,040 rows; 168 BA-hours are absent.
- Columns include `Demand Forecast (MW)`, `Demand (MW)`, and `Demand (MW) (Imputed)` / `(Adjusted)` variants.
- Missing demand 12.49% overall; missing forecast 12.31% overall; very uneven by BA:

| BA | Demand missing | Forecast missing |
|---|---|---|
| PJM, ERCO, CISO, MISO | 24 of 2,784 (0.86%) | 0 |
| ISNE | 27 (0.97%) | 0 |
| SWPP | 24 | 432 (15.52%) |
| GVL | 103 (3.70%) | 24 |
| AVRN | 100% (2,760 rows) | 100% |

- EIA flat files start July 1, 2015; API and dashboard data start January 1, 2019.
- EIA changed some generation categories in 2025 (battery storage from January 1, 2025; solar and wind splits). Irrelevant for a demand target but relevant if generation columns are ever used.
- EIA warns about daylight-saving duplicates, missing, and mistimed values, and that demand forecasts are "not meaningfully comparable to actual demand for some BAs".

## Resolved by the owner's second inspection

Compared 2022 H1 and 2026 H2 balance files and read EIA's definitions (https://www.eia.gov/electricity/930-content/about.html). Not independently re-run by Claude.

- **Schema.** Balance: 44 columns in 2022 H1 vs 65 in 2026 H2; the first 20 match, and the difference is mostly finer generation-by-source fields. Subregion: identical 7-column header. Interchange 2022 H1 was not inspected (unverified, and not used). Decision: read only the common columns needed for demand forecasting, selected by name, and assert them on load.
- **Missing demand.** In 2026 H2, 48 BAs each miss exactly 24 actual-demand values: Hour Numbers 1-24 on 2026-10-24. This is a date-level reporting gap, not scattered missing hours. Decision: do not impute; exclude the incomplete final date from evaluation unless reliable values are recovered. Check whether similar trailing gaps exist in other files.
- **Field definitions (per EIA, as reported by the owner).**
  - `Demand (MW)`: reported demand.
  - `Demand (MW) (Imputed)`: EIA-filled values for missing or anomalous observations, using documented fallback procedures.
  - `Demand (MW) (Adjusted)`: demand adjusted for commercial arrangements such as pseudo-ties and dynamic scheduling.
  - `Demand Forecast (MW)`: the BA's day-ahead forecast, the benchmark.
- **Target decision (provisional).** Train and score on reported `Demand (MW)`, dropping rows where it is missing. Never score on imputed values. Whether the BA's forecast targets reported or adjusted demand is not established; check per BA by comparing forecast error against each demand variant, and record the result.

## Open questions (to resolve before modeling)

1. **Operator forecast issue time.** When is `Demand Forecast (MW)` produced relative to the hour it covers? Without this a fair information-set comparison is impossible. Also check which BAs have a usable forecast.
2. **Which demand variant the forecast tracks** (reported vs adjusted), per BA.
3. **Trailing gaps in older files.** Does the "last day missing" pattern recur elsewhere?
4. **Terms of use.** EIA's page states none; confirm. Confirm the Zenodo record and license if used.
5. **Weather.** Source, coverage (the Open-Meteo forecast archive starts in 2021, limiting an honest evaluation window), and BA-to-location mapping. Decide whether the headline uses forecast weather or actual weather as a labeled upper bound.
6. **Anomalous values.** Reported demand can contain spikes, zeros, or negatives. Define a screening rule before modeling and record how many rows it affects.

## BA selection rule (fixed before any modeling)

Computed from data availability only, never from model performance, over the full history planned for use (to be fixed once the year range is chosen):

1. Keep BAs whose reported demand is present for at least 95% of hours in every calendar year used.
2. Of those, keep BAs whose day-ahead forecast is present for at least 95% of hours, so the benchmark exists.
3. Rank by mean demand (largest first) and take the top 10, requiring a spread across at least 4 EIA regions where the eligible set allows it.
4. Write the resulting list and the completeness table into this file and commit them before any model is fit.

The thresholds are provisional; changing them after seeing model results is not allowed.

## Planned deliverables

- Reproducible pipeline in `src/` with tests.
- A short report (about 5 to 8 pages) stating the question, data, method, results with uncertainty, and limitations.
- Figures: calibration plot, cost versus cost ratio, per-BA comparison.
