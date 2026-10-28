# Demand Forecasting for Capacity Planning

Forecast hourly demand with **calibrated prediction intervals**, then test whether those forecasts lead to **cheaper capacity decisions** than simpler alternatives, including the operators' own day-ahead forecasts.

The case study is the U.S. electricity grid (EIA-930 hourly balancing-authority data). The structure is the same wherever someone must commit capacity before demand is known and a shortfall costs more than a surplus: retail inventory, call-center staffing, cloud capacity, hospital beds.

> **Status: project set up, analysis not started.** No results exist yet. Every number in this repo will come from code in this repo.

## The business question

> A planner must commit capacity for each hour of tomorrow before demand is known. Running short costs more than having a surplus. **How much should they commit, and does a probabilistic forecast beat the alternatives at that decision?**

Optimal commitment under asymmetric costs is a quantile of the demand distribution (the newsvendor result): commit the `c_short / (c_short + c_surplus)` quantile. Good decisions therefore need well-calibrated quantiles, not only a good point forecast.

## Research questions

1. **Accuracy.** Does a statistical model beat seasonal-naive, hour-of-week-mean, and the operator's published day-ahead forecast?
2. **Calibration.** Do the 80% and 90% intervals contain demand 80% and 90% of the time, including on extreme-weather days?
3. **Decision value.** Under a range of shortfall-to-surplus cost ratios, how does expected cost compare for (a) quantile-based commitment, (b) point forecast plus a fixed margin, (c) operator forecast plus a margin?
4. **Robustness.** Do the conclusions hold across balancing authorities, seasons, and years?

A result where the operators' forecast is hard to beat is a valid and useful finding.

## Method (planned)

- Data: EIA-930 balance files, a small set of balancing authorities chosen **in advance by a data-completeness rule, not by model performance**.
- Splits: time-ordered rolling-origin validation; the final test period is untouched until the end.
- Baselines first: seasonal naive, hour-of-week mean, operator forecast.
- Models: regularized linear and gradient-boosted quantile regression. No deep learning.
- Weather: only information that would be available at forecast time (see `docs/project_brief.md`).
- Decision evaluation: cost simulation with the cost ratio **swept**, since the costs are assumptions, not data.
- Uncertainty: block bootstrap over days or weeks.

## Repository layout

```
src/capacity_planning/   reusable code (loading, features, models, evaluation, decisions)
tests/                   unit tests
notebooks/               exploration only; conclusions must be reproducible from src/
docs/project_brief.md    scope, verified data facts, open questions
data/                    raw/derived data (git-ignored); see data/README.md
reports/figures/         figures used in the write-up
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest && ruff check .
```

Data download instructions are in [`data/README.md`](data/README.md).

## Limitations (known up front)

- Cost parameters are assumptions; conclusions are shown as a function of the cost ratio.
- Operator forecasts may not be comparable across all balancing authorities, and their issue time still needs to be established.
- Reported demand contains missing and imputed values; the target definition is documented in the brief.
- Findings describe forecast and decision performance. They are not causal claims.

## Data and licenses

Code: MIT (see `LICENSE`). Data: EIA-930 from the U.S. Energy Information Administration; weather from Open-Meteo (CC BY 4.0, attribution required). Check each source's current terms before redistributing anything.
