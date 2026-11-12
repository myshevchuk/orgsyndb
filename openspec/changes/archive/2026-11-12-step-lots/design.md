## Context

`inventory.Lot` has substance, source, supplier, unit, amount, batch,
location, made_on and note; `LotMovement` has `opening`, `filling`,
`correction` and `reversal`, the last only through an item movement's
reversal of a filling. A task and a lot belong to each other through an
equal batch. Tasks have steps since `tasks-on-imports`. Draft 07 adds
`inventory_lot.task_step`, `inventory_lotmovement.task_step` and
`reverses`, the kind `withdrawal`, and `tasks_task.failed`.

## Goals / Non-Goals

**Goals:**

- What a step made and took is recorded where it happened.
- A task's end says whether it produced something.

**Non-Goals:**

- The journal (notebooks and entries) and `notebook` and `project` as
  built-in procedure keys: a later change, which changes the
  collection's format.
- Planning from stocked intermediates: change 3.
- Booking an amount automatically when a task ends (an idea the owner
  recorded for later).

## Decisions

### A product lot is matched by batch

Draft 07 says a finished task that has not failed has at least one
product lot carrying its batch. The rule matches by batch, as the
existing link between tasks and lots does, so a task without steps can
end too; a lot made by the task's last step is the usual way to make
one. `task_step` on a lot records which step made it, intermediates
included.

### Withdrawals are lot movements

A withdrawal is a lot movement of its own kind, naming the step; its
reversal is a `reversal` naming it through `reverses`, at most once.
Both go through the existing conditional amount update. A filling's
reversal keeps working through the item movement, as today.

### Failing a task

`fail` ends a running task without a product lot as failed and
empties its batch, since a failed synthesis keeps no lot number; its
steps keep what was done. A failed task needs no follow-up and is left
out of synthesis times as a cancelled one is.

## Risks / Trade-offs

- [Ending gets stricter] → A task that has not failed cannot end
  before its product lot is recorded; the task page offers the link on
  every step, and the lot form fills in the batch.
- [Unconfirmed default] → Failed tasks counting as cancelled ones do in
  synthesis times is my reading of draft 07; the owner may revisit it.
