# Plan (about 10 hours/week, 8-12 weeks)

Each phase ends with something checkable. Dates are not fixed; hours are rough.

| Weeks | Focus | Output |
|---|---|---|
| 1 | Data loading and checks | Loader selecting common columns by name; header assertions; UTC index; DST checks; incomplete-final-day handling; tests |
| 2 | Coverage and BA selection | Completeness table per BA and year; BA list committed per the rule in `project_brief.md` |
| 3 | Baselines and metrics | Seasonal naive, hour-of-week mean, operator forecast; MAE, MAPE, pinball loss; rolling-origin split code |
| 4 | Operator forecast study | Issue time established; which demand variant it tracks; error by hour, season, BA |
| 5-6 | Models | Regularized linear and gradient-boosted quantile models; calendar features; lagged demand available at issue time; validation-only tuning |
| 7 | Weather | Source and mapping decided; forecast vs actual weather variants; leakage review |
| 8 | Calibration | Coverage, interval width, calibration plots, extreme days; optional conformal adjustment |
| 9 | Decision layer | Cost simulation; cost-ratio sweep; quantile vs point+margin vs operator+margin |
| 10 | Final test and uncertainty | One run on the untouched test period; block bootstrap; per-BA results |
| 11-12 | Write-up and polish | 5-8 page report, figures, README results section, reproducibility check from a clean clone |

## Stop rules

- If the operator forecast cannot be compared fairly for most selected BAs, say so and reduce the benchmark claim to the BAs where it can.
- If weather mapping stalls past week 7, ship the no-weather results and describe weather as future work.
- Do not add models to rescue a weak result; report it.
