# BA selection protocol

Status: **rules and study window frozen; region source and results pending.** The resulting BA list is filled in
`docs/ba_selection_results.md`. No model may be fit or compared until that file is committed.
The 95% thresholds are provisional until this protocol is finalized; after that they may not change in
response to model results. If the constraints cannot be met, stop, report the conflict, and propose a rule
revision before any model is examined.

## Frozen inputs

1. **Study window (UTC), inclusive of Jan 1, 2021 through Oct 23, 2026.** An hour is identified by its
   `UTC Time at End of Hour` stamp and belongs to the year its interval *starts* in. The window contains the
   hours ending 2021-01-01 01:00 UTC through 2026-10-24 00:00 UTC, 50,928 hours.
   - The last date with a complete day in the 2026 H2 file is Oct 23. On Oct 24 (local date), 53 BAs (every BA that reports demand) lack all
     24 demand hours; local Oct 24 begins no earlier than 04:00 UTC for any U.S. BA, so ending the window at
     2026-10-24 00:00 UTC keeps every BA's local Oct 24 out of it.
   - The incomplete final date is cut from the window, so it neither counts as missing nor enters evaluation.
   - Rationale for 2021: matches the Open-Meteo forecast archive start (to be re-checked when weather is chosen).
2. **Years used**: 2021, 2022, 2023, 2024, 2025, 2026 (partial). Expected hours per year, which the code must
   reproduce exactly (acceptance test): 2021 = 8,760; 2022 = 8,760; 2023 = 8,760; 2024 = 8,784; 2025 = 8,760;
   2026 = 7,104; total = 50,928.
3. **Region assignment**: the EIA `Region` value for each BA. Assert that each BA has exactly one in the window;
   if not, report it as a conflict. (Source file to be named in the results file.)

Files needed: the six-month balance files 2021 H1 through 2026 H2 (12 files). Only 2022 H1 and 2026 H2 headers have
been compared so far; check the other ten for the columns used (BA, UTC end-of-hour stamp, `Demand (MW)`,
`Demand Forecast (MW)`, `Region`) before loading, and log any file boundary overlaps or duplicates.

## Definitions

- **Expected hours** for a BA and year: every UTC hour of the window that starts inside that year. Missing rows count as
  missing, so coverage is computed against the calendar, not against the rows present.
- **Reported demand coverage**: share of expected hours with a non-missing `Demand (MW)` that is also valid
  (greater than zero). `Demand (MW) (Imputed)` and `(Adjusted)` are never used or counted.
- **Forecast coverage**: share of expected hours with a non-missing, greater-than-zero `Demand Forecast (MW)`.
- Non-positive demand is treated as invalid for coverage only; it is not dropped from the raw record.
  Count and report how many hours this affects per BA. (Provisional; revisit under the same freeze rule.)
- **Mean demand**: average of valid reported demand over the same window for all BAs, computed per BA from its
  own valid hours. Because every BA uses the identical window, rankings are comparable.
- Daylight saving: work on UTC hours. Duplicate or missing UTC hours in the source are logged and counted as
  missing.

## Algorithm (deterministic)

1. For each BA and each year used, compute reported demand coverage and forecast coverage.
2. **Eligible set** = BAs with both coverages >= 0.95 in **every** year used.
3. Sort eligible BAs by mean demand descending; break ties by BA code ascending. This is the ranking `R`.
4. Initial selection `S` = first 10 of `R`. (If fewer than 10 are eligible, stop: conflict.)
5. If `S` spans >= 4 distinct regions, finish.
6. Otherwise repair, repeating until 4 regions are spanned:
   - find the highest-ranked BA in `R` not in `S` whose region is **not** in `S`;
   - find the lowest-ranked BA in `S` whose region has at least two members in `S`;
   - swap them.
   If no such BA exists, stop: conflict.
7. Final list = `S` sorted by ranking.

## Coverage table the code must produce

One row per BA and calendar year (all BAs present in any file, including ones that fail), columns:

| Column | Meaning |
|---|---|
| `ba`, `region`, `year` | identifiers |
| `expected_hours` | calendar hours of the window in that year |
| `rows_present` | rows in the files for that BA and year (after logging duplicates) |
| `valid_demand_hours` | non-missing reported `Demand (MW)` > 0 |
| `demand_coverage` | `valid_demand_hours / expected_hours` |
| `valid_forecast_hours` | non-missing `Demand Forecast (MW)` > 0 |
| `forecast_coverage` | `valid_forecast_hours / expected_hours` |
| `demand_pass`, `forecast_pass` | coverage >= 0.95 |

Also report per BA: count of hours with demand <= 0 and forecast <= 0 (excluded as invalid), duplicate UTC
stamps, and rows outside the window. A BA is eligible only if all its yearly `demand_pass` and `forecast_pass` are
true. Every swap in step 6 is logged with both BAs, their regions, and their ranks.

## Records to commit before modeling

In `docs/ba_selection_results.md`:
- the frozen window, years used, and region assignment source;
- the full per-BA, per-year coverage table (all BAs, eligible or not, with the reason for exclusion);
- the 5 BAs closest to the cutoff on each side, with their coverage and mean demand;
- the final list, with swaps made in step 6 if any;
- the effect of incomplete dates and other reporting gaps on coverage (hours cut, hours counted missing);
- the commit hash of the code that produced the table.

## Conflicts

Conflict examples: fewer than 10 eligible BAs, fewer than 4 regions available, a BA with more than one region.
Report the numbers and propose a revision in a separate commit, before any model results exist. State
explicitly that no model had been fit at the time.
