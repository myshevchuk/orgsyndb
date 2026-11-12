## Why

The lab application records bulk lots and tasks, but not what a
synthesis made along the way or used: an intermediate set aside by one
step and taken by the next leaves no trace, and a synthesis that failed
looks like one that ended. The owner settled in draft 07 that a lot may
be made by a task step, that withdrawals book the material a step took,
that a failed synthesis is flagged and keeps no lot number, and that a
task that has not failed ends only with a batch and a product lot.
Planning from stocked intermediates (change 3) builds on these records.

## What Changes

- A made lot may name the task step that made it; the lot form takes it
  from `?step=<id>` and refuses a substance the step does not make.
- A new lot movement, `withdrawal`, books an amount taken into a task
  step; a withdrawal can be reversed once.
- **BREAKING** A task gains `failed` and the state `failed`; the
  action `fail` ends a running task as failed and empties its batch.
  `end`, and a form that sets an end date, need a batch and a product
  lot, a made lot of the task's substance with that batch.
- The task page lists, per step, the lots it made and the withdrawals
  into it, with links to record either; the lot page shows them.
- Failed tasks do not count towards an article's synthesis time.
- The demo's ended tasks have their product lots, one task failed, and
  one intermediate lot is made by a step and partly withdrawn into the
  next.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: lots made by a step, withdrawals and their
  reversal, the lot page and forms.
- `task-tracker`: `failed`, the product-lot rule, the actions, the
  page and the forms.
- `production-planning`: synthesis times without failed tasks; lots
  of a task through its steps.
- `lab-demo`: the demo's tasks and lots.

## Impact

- Changed: `webapp/inventory/` (models, migration, bookings, forms,
  views, templates), `webapp/tasks/` (models, migration, forms,
  views, templates), `webapp/planning/`, `webapp/demo/`, the strings
  and the tests of each; `webapp/docs/database-schema.html`,
  regenerated.
- Docs: `README.md` (bulk lots, tasks, the demo).
