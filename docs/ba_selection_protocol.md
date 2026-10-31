# BA selection protocol

**Status: frozen. Results recorded 2026-10-29** in [`ba_selection_results.md`](ba_selection_results.md).
These rules were fixed before any model was fit or compared, and may not change because of model results.
Reworded for clarity on 2026-10-30; the rules did not change.

## Inputs

1. **Window:** hours ending 2021-01-01 01:00 UTC to 2026-10-24 00:00 UTC (50,928 hours). An hour belongs to
   the year it *starts* in. The window ends before local Oct 24, 2026, which has no demand for any BA, so that
   day neither counts as missing nor enters evaluation. The 2021 start was set before the weather source was
   chosen.
2. **Expected hours per year** (the code must match): 2021-2023 and 2025 = 8,760; 2024 = 8,784;
   2026 = 7,104; total 50,928.
3. **Region:** the EIA `Region` column. Each BA must have exactly one in the window, or it is a conflict.
4. **Excluded BAs** (revision 1): AVA, FPC, GVL, LGEE, PSEI, SEC, SPA, TEPC. EIA says their forecasts don't
   compare well with actual demand. They still appear in the coverage table, with reason
   `excluded: EIA forecast caveat`.
5. **Files:** the 12 balance files, 2021 H1 to 2026 H2. Before loading, check every file has the columns used
   and log any overlaps or duplicates between files.

## Definitions

- **Expected hours:** every window hour that starts in the year. Absent rows count as missing.
- **Valid:** present and greater than 0. Imputed and adjusted demand are never used.
- **Demand coverage** and **forecast coverage:** valid hours / expected hours, for `Demand (MW)` and
  `Demand Forecast (MW)`.
- **Mean demand:** average of a BA's valid demand over the window.
- Values <= 0 count as invalid for coverage but stay in the raw data; count them per BA.
- Work in UTC. Duplicate or missing UTC hours are logged and counted as missing.

## Steps

1. Compute both coverages for each BA and year.
2. **Eligible:** not excluded, and both coverages >= 95% in every year.
3. Rank eligible BAs by mean demand, largest first; break ties by BA code (A to Z).
4. Take the top 10. Fewer than 10 eligible is a conflict.
5. If they span at least 4 regions, stop.
6. Otherwise swap until 4 regions are covered: bring in the highest-ranked unselected BA from a region not
   yet selected, and drop the lowest-ranked selected BA whose region has at least 2 selected. No such pair is a
   conflict.
7. The final list is in rank order.

## Outputs

**Coverage table:** one row per BA and year, for every BA in the files. Columns: `ba`, `region`, `year`,
`expected_hours`, `rows_present` (after logging duplicates), `valid_demand_hours`, `demand_coverage`, `valid_forecast_hours`,
`forecast_coverage`, `demand_pass`, `forecast_pass`.

Also per BA: hours with demand <= 0 and forecast <= 0, duplicate hours, and rows outside the window.
Log each swap with both BAs, their regions, and their ranks.

**Results file**, committed before any model is fit: the window, years used, and region source; the full
coverage table with reasons for exclusion; the 5 BAs on each side of the cutoff, with their coverage and mean
demand; the final list and any swaps; the effect of gaps (hours cut, hours counted missing); the commit hash
of the code.

## Conflicts

For example: fewer than 10 eligible, fewer than 4 regions, or a BA with two regions. Stop, report the
numbers, and propose a revision in its own commit before any model is examined. State that no model had
been fit.

## Revisions

1. **2026-10-29:** excluded the 8 BAs EIA flags (input 4, step 2). Based on EIA documentation only; no
   coverage table or model existed yet.
