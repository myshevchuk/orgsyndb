# Change: HTMX live task and registry lists

## Why

Stage 3A (`htmx-live-inventory-lists`) brought live in-place HTMX filtering to
all six inventory lists, leaving the two remaining shared `<c-filter-bar>`
filter forms—`/lab/tasks/` and `/lab/registry/`—as full-page GET reloads, and
leaving the now-unused `[data-submit]` submit-on-change listener in `lab.js`.
Extending the `web-app` `Live lists` contract to both pages completes live
filtering across all shared filter forms and removes the obsolete
`[data-submit]` handler.

## What Changes

- Move `htmx_list_push_url()` from `webapp/inventory/views/common.py` into
  `webapp/orgsyndb_web/lists.py` and update all six inventory view modules
  (`categories.py`, `items.py`, `bulk.py`, `notes.py`, `batches.py`,
  `vessels.py`) plus `tasks/views.py` and `registry/views.py` to import it
  directly from `orgsyndb_web.lists` (no re-export shim).
- Wire `/lab/tasks/` (`tasks/views.py`, `tasks/list.html`) and
  `/lab/registry/` (`registry/views.py`, `registry/list.html`) to the
  `web-app: Live lists` contract: scoped HTMX triggers (`submit`,
  `search from:#filter-q`, `input delay:200ms from:#filter-q`,
  `change target:select`), `hx-sync="#main:replace"`, `morph:outerHTML` on
  `#task-rows` / `#substance-rows`, disjoint `:morph` OOB updates on
  `#task-counts` / `#substance-count`, canonical `HX-Push-Url` on non-restore
  HTMX GETs, and `Vary: HX-Request, HX-History-Restore-Request`.
- Preserve unknown `group` or `class` filter keys as a selected option in
  `registry/list.html` so subsequent live edits to `q` keep the unknown filter
  active until the user explicitly selects `All`.
- Remove the obsolete `[data-submit]` handler and header bullet from
  `webapp/orgsyndb_web/static/lab.js`.

## Impact

- Affected specs: `task-tracker` (`ADDED: Live task list`), `lab-registry`
  (`ADDED: Live substance list`).
- Affected code: `webapp/orgsyndb_web/lists.py`,
  `webapp/inventory/views/{common,categories,items,bulk,notes,batches,vessels}.py`,
  `webapp/tasks/views.py`, `webapp/tasks/templates/tasks/list.html`,
  `webapp/registry/views.py`, `webapp/registry/templates/registry/list.html`,
  `webapp/orgsyndb_web/static/lab.js`.
- Affected tests: new `webapp/tests/test_live_tasks_registry.py`, plus
  `webapp/tests/test_lab_script.py` (verifying no `[data-submit]` listener).
