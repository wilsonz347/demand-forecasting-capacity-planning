# BA selection protocol

Status: **rules frozen, inputs not yet frozen.** The study window and the resulting BA list are filled in
`docs/ba_selection_results.md`. No model may be fit or compared until that file is committed.
The 95% thresholds are provisional until this protocol is finalized; after that they may not change in
response to model results. If the constraints cannot be met, stop, report the conflict, and propose a rule
revision before any model is examined.

## Inputs to freeze first

1. **Study window**: first and last UTC hour used. The last day is the last date for which the downloaded
   files hold a complete day. Incomplete final dates (for example 2026-10-24, where 48 BAs lack all 24 hours of
   demand) are cut from the window, so they neither count as missing nor enter any evaluation.
2. **Years used**: every calendar year that overlaps the window. For a partial year, coverage is measured
   over the window hours inside that year.
3. **Region assignment**: the EIA `Region` value for each BA. Assert that each BA has exactly one in the window;
   if not, report it as a conflict.

## Definitions

- **Expected hours** for a BA and year: every UTC hour of the window inside that year. Missing rows count as
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
