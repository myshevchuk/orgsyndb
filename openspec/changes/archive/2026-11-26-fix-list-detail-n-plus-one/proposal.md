## Why

Four remaining read paths scale linearly in SQL queries with the number of
rendered rows or steps:

- `note_list` renders each line's `item.article_number` and `item.name`
  without prefetching `lines__item__article__substance`, and re-queries the
  selected note's lines and state inside `note_context()`.
- `vessel_ledger` selects `transfer__vessel` and `transferred__vessel` without
  their `batch`, triggering a query per transfer movement when formatting
  `Vessel.__str__()`.
- `task_page` fetches `step.batches`, each batch's `vessels`, and each step's
  withdrawals inside per-step loops (`made_by` and `shown_step`).
- `TaskAdmin.progress_shown` calls `task.step_counts` per row on the admin
  changelist instead of reading annotated counts from `get_queryset()`.

## What Changes

- `webapp/inventory/views.py`: prefetch `lines__item__article__substance` in
  `note_list`, pass the already-loaded state and lines for the selected note
  to `note_context()`, and add `transfer__vessel__batch` and
  `transferred__vessel__batch` to `vessel_ledger`'s `select_related()`.
- `webapp/tasks/views.py`: bulk-prefetch step batches (with `substance`,
  `journal_entry__notebook`, and ordered `vessels`) and step withdrawals in
  `task_page`, and read the prefetched collections in `made_by()` and
  `shown_step()`.
- `webapp/tasks/admin.py`: annotate total and done step counts in
  `TaskAdmin.get_queryset()` and use them in `progress_shown()`.
- `webapp/tests/test_query_counts.py`: add constant-query-count regression
  tests for `note_list`, `vessel_page`, `task_page`, and the `TaskAdmin`
  changelist.

## Why No Spec Changes

Every requirement under `openspec/specs/` stays true: rendered HTML, ordering,
admin output, and view behavior are unchanged. The closest capabilities are
`end-product-inventory` and `task-tracker`, neither of which prescribes
internal ORM prefetching or admin queryset annotations.

## Impact

- Code touched: `webapp/inventory/views.py`, `webapp/tasks/views.py`,
  `webapp/tasks/admin.py`, `webapp/tests/test_query_counts.py`.
- Risks: subtle ordering mismatch in prefetched relations (`batches`,
  `vessels`, `withdrawals`) or callers invoking `note_context()` /
  `made_by()` / `shown_step()` directly without prefetch. All helpers keep
  safe fallbacks and preserve exact `order_by("id")` ordering.

## Verification

1. Existing suites `test_inventory_notes.py`, `test_inventory_vessels.py`,
   `test_task_page.py`, and `test_admin.py` pass without edits.
2. New constant-query-count tests in `test_query_counts.py` pass for
   `note_list`, `vessel_page`, `task_page`, and `TaskAdmin` changelist.
3. CI workflows `Program` and `Lab application` pass on the pushed branch.
