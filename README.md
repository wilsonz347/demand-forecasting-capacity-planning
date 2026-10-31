# Demand Forecasting for Capacity Planning

**Question:** a planner must decide how much capacity to commit for each hour of tomorrow, before demand is
known. Running short costs more than having extra. Does a forecast that gives a *range* (not one number) lead
to cheaper decisions than the operator's own forecast?

The case study is the U.S. power grid (EIA-930 hourly data). The same problem appears in inventory,
staffing, and cloud capacity.

> **Status: done (without confidence intervals; see Limits in [`docs/results.md`](docs/results.md)).**
> On the untouched test year, the operator's forecast plus a margin was cheaper than our range
> forecast in 8 of 10 BAs at every cost ratio.

## Why a range matters

When shortfalls cost more than surpluses, the best amount to commit is a high point of the demand range
(a quantile), not the average. So the forecast must get its ranges right, not just its average.

## What we test

1. **Accuracy:** does our model beat simple baselines (same hour last week, 4-week average) and the operator?
2. **Ranges:** do 80% and 90% ranges contain the actual demand 80% and 90% of the time, even on extreme days?
3. **Cost:** across many shortfall-to-surplus cost ratios, which is cheapest: committing a quantile of our
   range, our forecast plus a fixed margin, or the operator's forecast plus a margin?
4. **Robustness:** do the answers hold for each BA, season, and year?

"The operator is hard to beat" is a valid answer.

## How

- 10 large balancing authorities (BAs), chosen by fixed rules before any modeling.
- Train on 2021 to Oct 2024, tune on the next 12 months, test once on the final 12 months.
- Only information available at 6 p.m. the day before (a provisional cutoff), including weather *forecasts*,
  not actual weather.
- Models: ridge regression and XGBoost for single-number forecasts; XGBoost with the quantile
  loss for ranges (5th to 95th percentile). One model per BA, refit monthly.
- Decision: for each cost ratio (1, 3, 9, 19), commit our matching percentile, or the operator's
  forecast plus a margin learned from its past errors. Compare the average cost per hour.

## Repository

- `src/demand_forecasting/`: the code (`python -m demand_forecasting.<module>`), tests in `tests/`
  (run `uv run pytest -q`)
- `docs/results.md`: the answer, with the test-year tables
- `docs/project_brief.md`: scope, decisions, and open questions
- `docs/ba_selection_protocol.md` and `docs/ba_selection_results.md`: how the 10 BAs were chosen
- `data/README.md` and `data/MANIFEST.md`: how to get the data, and what is in it (data is not committed)

## Limits

- Costs are assumed; results are shown as a function of the cost ratio.
- No confidence intervals, and the 8 a.m. cutoff check was not done.
- Some operators' forecasts may not be directly comparable with reported demand.
- Results describe forecast and decision quality, not causes.

## Data and license

Code: MIT (`LICENSE`). Data: EIA-930 (U.S. Energy Information Administration, public domain) and NWS weather
forecasts archived by the Iowa Environmental Mesonet, Iowa State University (public domain).
