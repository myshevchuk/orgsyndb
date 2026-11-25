## Context

`webapp/planning/forecast.py` computes `z_of(certainty)` for every
per-item union-bound certainty `q_k`, so `Parameters.z` on
`webapp/planning/models.py` is unused outside
`webapp/tests/test_planning_parameters.py`.

## Goals / Non-Goals

- **Goals:** Remove `Parameters.z` and the superseded `z` sentence from
  `production-planning` ("Planning parameters"); preserve quantile test
  coverage on `forecast.z_of`.
- **Non-Goals:** Changing demand or runway calculations.

## Decisions

- Test `forecast.z_of` directly in `webapp/tests/test_planning_demand.py`
  for `0.5`, `0.9`, `0.95` (to four places `1.6449`), `0.975`, and
  `0.999`.
