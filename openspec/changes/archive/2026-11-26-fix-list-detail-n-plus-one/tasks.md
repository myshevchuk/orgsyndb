## 1. Inventory list and vessel ledger

- [x] 1.1 Prefetch `lines__item__article__substance` in `note_list` and pass precomputed `state` and `lines` into `note_context()`
- [x] 1.2 Add `transfer__vessel__batch` and `transferred__vessel__batch` to `vessel_ledger()`

## 2. Task page and admin

- [x] 2.1 Bulk-prefetch step batches, batch vessels, and step withdrawals in `task_page` and consume them in `made_by()` / `shown_step()`
- [x] 2.2 Annotate total and done step counts in `TaskAdmin.get_queryset()` and use them in `progress_shown()`

## 3. Verification

- [x] 3.1 Add constant-query-count regression tests for `note_list`, `vessel_page`, `task_page`, and `TaskAdmin` changelist
- [x] 3.2 Run area suites locally and verify green CI on the pushed branch
