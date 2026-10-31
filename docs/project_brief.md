# Project brief

## Goal

Forecast hourly electricity demand as a range, and test whether it leads to better capacity decisions than
the operator's own forecast. See the [README](../README.md) for the question.

## Scope

- **In:** about 10 BAs chosen by fixed rules; time-ordered splits; baselines first; regularized linear and
  gradient-boosted quantile models; cost simulation across cost ratios; bootstrap intervals; a short report.
- **Later, if time allows:** more BAs; other calibration methods; extreme-day and seasonal analysis.
- **Out:** deep learning, LLMs, dashboards; prices or dispatch; causal claims.

## Data facts

Measured facts about the files are in [`data/MANIFEST.md`](../data/MANIFEST.md). From EIA's documentation
(https://www.eia.gov/electricity/930-content/about.html) and the Form EIA-930 instructions:

- `Demand (MW)` is reported demand (our target). `Demand Forecast (MW)` is the BA's day-ahead forecast.
- `Demand (MW) (Imputed)` is filled in by EIA, using the operator's forecast first. Never score on it.
- `Demand (MW) (Adjusted)` corrects for commercial arrangements between BAs.
- Forecasts should always be positive, so values <= 0 are invalid.
- EIA warns that some BAs' forecasts don't compare well with actual demand.

## Decisions

| Topic | Decision | Why |
|---|---|---|
| BAs | 10 largest that pass the coverage rule ([protocol](ba_selection_protocol.md), [results](ba_selection_results.md)) | Most of the demand, few enough to report per BA |
| Excluded BAs | AVA, FPC, GVL, LGEE, PSEI, SEC, SPA, TEPC | EIA says their forecasts don't compare well with demand |
| Target | Reported `Demand (MW)`; drop invalid hours | Imputed values would favor the operator |
| Input cutoff (provisional) | Data up to 6 p.m. local time on the day before | One fixed rule for every BA |
| Splits (by local date) | Train 2021-01-01 to 2024-10-23 (grows with each validation restart); validation to 2025-10-23; test to 2026-10-23 | 12-month validation and test each cover every season; validation restarts monthly, using only data known at the time |
| Test year | Used once at the end, never tuned on | Keeps the final answer honest |
| Start of 2021 | First 5-8 hours (local Dec 31, 2020) count as missing | Not in our files; tiny effect |
| Bad values | Invalid if missing, <= 0, or above 1.5 x the BA's train 99.9th percentile (same rule for forecasts) | Removes recording errors, keeps real peaks |
| Weather | NWS airport forecasts (IEM archive), 12:00 UTC run of the day before, filled to hourly, 2-3 airports per BA weighted by 2020 population | Time-stamped forecasts, so no look-ahead; humidity for all years |

Details:
- **Bad values removed** (train + validation): PJM 3 hours (2021, up to 2.1 billion MW), SOCO 3 (Feb 2025),
  TVA 1 (Dec 2024, 9.97 million MW). Sudden drops that stay above 0 are not caught; their effect is negligible.
- **Cutoff risk:** if an operator makes its forecast earlier than 6 p.m., our model sees a few more hours of
  data. Before claiming a win, repeat the comparison with an earlier cutoff (e.g. 8 a.m.). If the win only
  holds at 6 p.m., say so.
- **Time zones:** each BA's in `build_dataset.py`. MISO uses Eastern Standard Time all year.
- **Weather caveats:** BPAT's city weights are rough. The publication time of each run is **not verified**:
  usually a few hours after the run, but one informal NWS note says about 10 hours, which would reach 6 p.m.
  Eastern daylight time. We kept the 12:00 UTC run anyway.
- **Whole local days:** the dataset keeps whole local days, so it has 4-7 more hours per BA at the end than the
  BA selection's UTC window.
- **Terms:** EIA and IEM data are public domain. Cite EIA as "Source: U.S. Energy Information Administration
  (date)" and credit IEM.

## Open questions

1. **Operator forecast time:** made the day before and sent to EIA by 7 a.m. Eastern on the day itself. The
   exact hour is unknown and differs by BA.
2. **Which demand the forecast targets** (reported or adjusted): compare forecast error against each, per BA.

## Deliverables

- Code in the repo that reproduces every number, with tests where they protect a result.
- A short report (5-8 pages): question, data, method, results with uncertainty, limits.
- Figures: range calibration, cost vs cost ratio, per-BA comparison.
