# Demand Forecasting for Capacity Planning

**Question:** a planner must decide how much capacity to commit for each hour of tomorrow, before demand is
known. Running short costs more than having extra. Does a forecast that gives a *range* (not one number) lead
to cheaper decisions than the operator's own forecast?

The case study is the U.S. power grid (EIA-930 hourly data). The same problem appears in inventory,
staffing, and cloud capacity.

> **Status:** data, BA selection, dataset, baselines, and weather are done. No model has been fit yet.

## Why a range matters

When shortfalls cost more than surpluses, the best amount to commit is a high point of the demand range
(a quantile), not the average. So the forecast must get its ranges right, not just its average.

## What we test

1. **Accuracy:** does our model beat simple baselines and the operator's forecast?
2. **Ranges:** do 80% and 90% ranges contain the actual demand 80% and 90% of the time?
3. **Cost:** across many shortfall-to-surplus cost ratios, which way of committing capacity is cheapest?
4. **Robustness:** do the answers hold for each BA, season, and year?

"The operator is hard to beat" is a valid answer.

## How

- 10 large balancing authorities (BAs), chosen by fixed rules before any modeling.
- Train on 2021-2024, tune on the next year, test once on the final year.
- Only information available at 6 p.m. the day before (including weather *forecasts*, not actual weather).
- Simple models: regularized linear and gradient-boosted quantile regression.
- Costs are assumptions, so results are shown across a range of cost ratios, with bootstrap intervals.

## Repository

- `src/demand_forecasting/`: the code (`python -m demand_forecasting.<module>`), tests in `tests/`
- `docs/project_brief.md`: scope, decisions, and open questions
- `docs/ba_selection_protocol.md` and `docs/ba_selection_results.md`: how the 10 BAs were chosen
- `data/README.md` and `data/MANIFEST.md`: how to get the data, and what is in it (data is not committed)

## Limits

- Costs are assumed; results are shown as a function of the cost ratio.
- Results describe forecast and decision quality, not causes.

## Data and license

Code: MIT (`LICENSE`). Data: EIA-930 (U.S. Energy Information Administration, public domain) and NWS weather
forecasts archived by the Iowa Environmental Mesonet, Iowa State University (public domain).
