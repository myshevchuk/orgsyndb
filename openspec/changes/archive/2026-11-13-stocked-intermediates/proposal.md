## Why

A synthesis sequence sets aside its intermediates as lots, but a task
that follows a sequence always plans every step of it, and planning
offers only `Synthese planen` for the article's substance. The owner
settled in draft 07 that intermediates are stocked, that planning
checks their stock and starts a synthesis from a stocked one where it
can, that a task lists the steps from the one it starts at, and that a
task that follows a sequence makes the sequence's target.

## What Changes

- Planning proposes, for each sequence that makes an article's
  substance, the step to start at: the latest step whose intermediate
  has an open lot. The `Synthese planen` action names the sequence and
  the step and links to the new-task form with both filled in; it
  reserves nothing.
- A task records `start_step`: its steps are the sequence's from that
  step on. Changing it follows the rules for changing the sequence.
- A task's sequence must make the task's substance.
- The new-task form takes `sequence` and `start_step` from the query;
  the task page shows `ab Stufe <k>`.
- The demo's planned `SEQ-0001` task starts at its second step, from a
  salicylic-acid lot an earlier task's first step made.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `production-planning`: Starting from stock; the synthesis action of
  the planning list.
- `task-tracker`: `start_step`, the target rule, the form fields and
  the task page.
- `lab-demo`: the demo's task from stock.

## Impact

- Changed: `webapp/planning/` (`plan.py`, the list template, `.po`),
  `webapp/tasks/` (model and migration, forms, `steps.py`, views,
  templates, `.po`), `webapp/demo/` (data, seed), the tests of each;
  `webapp/docs/database-schema.html`, regenerated.
- Docs: README (planning list, task form, task page, demo) and
  `docs/PLANNING.md` if it describes the synthesis action.
