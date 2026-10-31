# Results

**Question:** does a range forecast lead to cheaper capacity decisions than the operator's
own forecast?

**Answer:** no, for most grids. On the untouched test year, the operator's forecast plus a
margin was cheaper in 7 of 10 BAs at every cost ratio.

Test year: local dates 2025-10-24 to 2026-10-23, run once with frozen models (commit `e3ff7f2`).

## Cost: range forecast vs operator + margin

Saving of our range forecast in % of the operator's cost (positive = ours cheaper).
Ratio = cost of 1 MW short vs 1 MW extra.

| BA | 1:1 | 3:1 | 9:1 | 19:1 |
|---|---:|---:|---:|---:|
| CISO | +52% | +66% | +76% | +76% |
| DUK | -3% | +12% | +35% | +42% |
| PJM | -1% | -9% | -13% | -32% |
| MISO | -57% | -60% | -63% | -98% |
| TVA | -60% | -71% | -80% | -119% |
| ISNE | -94% | -66% | -58% | -68% |
| NYIS | -94% | -78% | -68% | -105% |
| BPAT | -103% | -102% | -102% | -107% |
| ERCO | -116% | -129% | -135% | -158% |
| SOCO | -398% | -292% | -205% | -266% |

- **CISO** does not count as a win: its operator forecast misses midday demand by a growing amount.
- **DUK** wins when shortfalls are costly, but lost on the validation year. Unconfirmed.
- **PJM** won slightly on validation (+6 to +9%) but not on test.

## Ranges: share of hours inside the 10-90% range (target 80%)

| BA | Test | Validation |
|---|---:|---:|
| SOCO | 81% | 83% |
| DUK | 80% | 83% |
| MISO | 80% | 83% |
| TVA | 79% | 84% |
| PJM | 79% | 80% |
| CISO | 78% | 81% |
| ISNE | 74% | 76% |
| NYIS | 74% | 77% |
| BPAT | 71% | 80% |
| ERCO | 71% | 71% |

## Limits

- No confidence intervals, so small differences may be noise.
- The operator's forecast issue time is unknown; it may use more information than our
  6 p.m. cutoff allows. The 8 a.m. cutoff check was not done.
- Costs are relative and assumed; the operator's margin is one constant per BA.

## Reproduce

```
uv run python -m demand_forecasting.model_quantile test   # about 20 minutes
uv run python -m demand_forecasting.decision test
```
