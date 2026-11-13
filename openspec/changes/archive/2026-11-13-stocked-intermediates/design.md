## Context

Since `step-lots` a task step records the lots it made and the
withdrawals it took, and a lot may name the step that made it. Since
`tasks-on-imports` a task that follows a sequence gets one step per
step of the sequence. Planning's `Synthese planen` links to the
new-task form with the substance only.

## Goals / Non-Goals

**Goals:**

- Planning says where a synthesis can start from stock, and the task
  form takes it over.
- A task records where it started, so its page and later edits know.

**Non-Goals:**

- Reserving a lot or checking that an open lot holds enough: the
  person confirms the step, and the amount stays their judgement.
- A shorter synthesis time for a task that skips steps.
- Moving a step to another entry (draft 07, for staff): a later
  change.

## Decisions

### The proposed step

For a sequence of `n` steps, the proposal is the largest `k` in
`2..n` such that the intermediate of step `k - 1`, as Sequence
continuity defines it (the first of its products that step `k` takes),
has an open lot; else 1. The latest such step skips the most
work. Any open lot counts, made or bought, since the lab may buy an
intermediate too.

### `start_step` is stored

Draft 07 left the start implicit in the task's steps. A stored
`start_step` keeps the task page and the edit form right when the
sequence later gains or loses steps in the collection, at the cost of
one column. The steps are planned from it under the existing rules:
set or changed only while no step is done, names a journal entry, made
a lot or took a withdrawal. The range and the target are checked only
when a save plans the steps anew, so a task whose sequence the
collection later shortened or retargeted stays editable.

### The target rule

A task that follows a sequence makes the sequence's target; the forms
refuse a sequence of another target when a save plans the steps anew,
and a substance changed away from the target, so planning's tasks
match their articles. The admin shows the sequence, the start step and
the steps read-only and refuses the same substance change, so no path
plans steps outside the task forms.

## Risks / Trade-offs

- [A proposal from a lot that holds too little] → The action names the
  substance in stock, so the person can check the lot before choosing
  the step.
