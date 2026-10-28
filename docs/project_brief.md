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

## Open questions (to resolve before modeling)

1. **Schema stability.** Do older six-month files (for example 2022 half 1) have the same header as 2026? Compare before concatenating.
2. **The 24 missing hours.** Several BAs miss exactly 24 demand hours. Is it one trailing incomplete day? Check which dates.
3. **Imputed vs Adjusted.** Definitions are not yet verified. Decide the target (default: reported `Demand (MW)`) and document why.
4. **Operator forecast issue time.** When is `Demand Forecast (MW)` produced relative to the hour it covers? Without this, a fair information-set comparison is impossible. Check which BAs have a usable forecast (non-missing, comparable to actual).
5. **Terms of use.** EIA's page states none; confirm. Confirm the Zenodo record and license if used.
6. **BA selection rule.** Fix the completeness threshold and the list before looking at model performance.
7. **Weather.** Source, coverage (the Open-Meteo forecast archive starts in 2021, which limits an honest evaluation window), and BA-to-location mapping. Decide whether the headline uses forecast weather or actual weather as a labeled upper bound.

## Planned deliverables

- Reproducible pipeline in `src/` with tests.
- A short report (about 5 to 8 pages) stating the question, data, method, results with uncertainty, and limitations.
- Figures: calibration plot, cost versus cost ratio, per-BA comparison.
