## Why

`production-planning` ("Planning parameters") still defines a single
`z = statistics.NormalDist().inv_cdf(certainty)` on the parameters
record, left over from before multi-item union-bound certainties `q_k`
were introduced. The demand model already defines
`z_q = statistics.NormalDist().inv_cdf(q)` ("Demand models"), and
production code computes quantiles directly through `forecast.z_of(q)`.
`Parameters.z` has no production caller.

## What Changes

- Remove the redundant `z` definition and default assertion from
  `production-planning` ("Planning parameters").
- Remove `Parameters.z` from `webapp/planning/models.py`.
- Move the quantile test assertions from
  `webapp/tests/test_planning_parameters.py` to
  `webapp/tests/test_planning_demand.py` against `forecast.z_of`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `production-planning`: drop the redundant `z` definition under
  "Planning parameters" (keeping `z_q` under "Demand models").

## Impact

- `openspec/specs/production-planning/spec.md`
- `webapp/planning/models.py`
- `webapp/tests/test_planning_parameters.py`,
  `webapp/tests/test_planning_demand.py`
