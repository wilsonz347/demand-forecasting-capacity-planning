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

## Data facts

Measured facts for all 12 balance files (counts, coverage, gaps, duplicates, regions) are in
[`data/MANIFEST.md`](../data/MANIFEST.md). Notes from EIA's documentation
(https://www.eia.gov/electricity/930-content/about.html) and the Form EIA-930 instructions (version expiring 07/31/2026):

- EIA flat files start July 1, 2015; API and dashboard data start January 1, 2019.
- EIA changed some generation categories in 2025 (battery storage from January 1, 2025; solar and wind splits). Irrelevant for a demand target but relevant if generation columns are ever used.
- EIA warns about daylight-saving duplicates, missing, and mistimed values, and that demand forecasts are "not meaningfully comparable to actual demand for some BAs".
- EIA fills missing demand with the operator's forecast first, so imputed demand favors the operator. Another reason never to score on it.
- Forecasts must be positive per the form instructions, so values <= 0 are invalid.
- Field definitions:
  - `Demand (MW)`: reported demand.
  - `Demand (MW) (Imputed)`: EIA-filled values for missing or anomalous observations, using documented fallback procedures.
  - `Demand (MW) (Adjusted)`: demand adjusted for commercial arrangements such as pseudo-ties and dynamic scheduling.
  - `Demand Forecast (MW)`: the BA's day-ahead forecast, the benchmark.

## Data decisions

- **Columns.** Read only the columns needed, selected by name (position changes between files), and assert them on load.
- **Incomplete final date.** Do not impute local 2026-10-24 (no demand for any BA); it is outside the study window.
- **Target (provisional).** Train and score on reported `Demand (MW)`, dropping rows where it is missing. Never score on imputed values. Whether the BA's forecast targets reported or adjusted demand is not established; check per BA by comparing forecast error against each demand variant, and record the result.
- **Time splits (2026-10-29).** By each BA's local date (EIA's `Data Date`), so no day is split:

  | Split | Local dates | Use |
  |---|---|---|
  | Train | 2021-01-01 to 2024-10-23 | Fit models; grows with each validation origin |
  | Validation | 2024-10-24 to 2025-10-23 | Compare and tune; rolling monthly origins |
  | Test | 2025-10-24 to 2026-10-23 | Used once at the end; never tuned on |

  Why: 12-month validation and test periods each cover every season; the test is the most recent year.
  Each origin uses only data available at that time, with the 6 p.m. D-1 input cutoff.
  The dataset keeps whole local days: it starts at local 2021-01-01 hour 1 and includes the evening of
  local 2026-10-23 that the UTC selection window cut (4-7 hours per BA). BA selection keeps its frozen
  UTC window, so its coverage counts differ slightly from the dataset's row counts. Time zones per BA are in `build_dataset.py`; MISO is dated
  in Eastern Standard Time all year.

## Open questions (to resolve before modeling)

1. **Operator forecast issue time.** The forecast for day D is made on day D-1 and sent to EIA by 7 a.m. Eastern on day D. The hour on D-1 is not documented and differs by BA.
   **Provisional assumption (2026-10-29):** our model's inputs for day D use only data up to **6 p.m. local time (the BA's own time zone) on day D-1**.
   - Why: one simple, fixed rule for every BA, and it stays on the day before.
   - Risk: if an operator issues its forecast earlier in the day, our model sees a few more hours of data than it did, which favors us.
   - Check: before claiming a win, repeat the comparison with an earlier cutoff (e.g. 8 a.m. on D-1). If the result only holds at 6 p.m., report it that way.
2. **Which demand variant the forecast tracks** (reported vs adjusted), per BA.
3. **Window start.** Every BA lacks its first 5-8 window hours (local Dec 31, 2020, in the 2020 H2 file). **Decided (2026-10-29):** count them as missing.
4. **Terms of use.** Resolved for EIA: public domain; cite as "Source: U.S. Energy Information Administration (date)". The Zenodo copy is not used.
5. **Weather.** Source, coverage (the Open-Meteo forecast archive starts in 2021, limiting an honest evaluation window), and BA-to-location mapping. Decide whether the headline uses forecast weather or actual weather as a labeled upper bound.
6. **Anomalous values.** Reported demand can contain spikes, zeros, or negatives, and non-positive forecasts jumped in 2025 H2 and 2026 H1 (see manifest). Define a screening rule before modeling and record how many rows it affects.
   **Decided (2026-10-29):** a value is invalid if missing, <= 0, or above 1.5 x the BA's 99.9th percentile of
   valid train-period demand (`screening.py`; same rule for the forecast). Removed in train + validation:
   PJM 3 demand hours (2021-10-19, up to 2.1 billion MW), SOCO 3 (Feb 2025, 83-92k MW), TVA 1
   (2024-12-18, 9.97 million MW); no forecast values. All are clear recording errors, not real peaks.

7. **BAs with weak forecasts.** EIA says the forecast-vs-actual comparison is "not very meaningful" for AVA, FPC, GVL, LGEE, PSEI, SEC, SPA, and TEPC. **Decided (2026-10-29):** excluded from selection (protocol revision 1).

Resolved: trailing gaps at other file boundaries are BA-specific, not market-wide (see manifest).

## BA selection rule

Frozen as a protocol in [`ba_selection_protocol.md`](ba_selection_protocol.md): 95% valid reported-demand and forecast coverage in every year used, top 10 by mean reported demand over a common window, at least 4 EIA regions, deterministic tie-break and repair, imputed demand never counted. The thresholds are provisional until the protocol is finalized and cannot change in response to model results. Outputs go in `ba_selection_results.md` before any model is fit.

## Planned deliverables

- Reproducible pipeline (code in the repo) with tests where they protect a result.
- A short report (about 5 to 8 pages) stating the question, data, method, results with uncertainty, and limitations.
- Figures: calibration plot, cost versus cost ratio, per-BA comparison.
