# Tasks: HTMX live task and registry lists

## 1. Tests (red-first)
- [x] 1.1 Create `webapp/tests/test_live_tasks_registry.py` covering every scenario in `task-tracker` (`Live task list`) and `lab-registry` (`Live substance list`):
  - Scoped HTMX live-filter attributes (`hx-get`, `hx-push-url="true"`, `hx-sync="#main:replace"`, `hx-trigger` with `submit`, `search from:#filter-q`, `input delay:200ms from:#filter-q`, `change target:select`, `hx-target`, `hx-select`, `hx-swap="morph:outerHTML"`, unique disjoint `:morph` `hx-select-oob` targeting `#task-counts:morph` / `#substance-count:morph`), no-JS GET fallback (`method="get"`, `action`, submit button), stable row IDs (`#task-row-<pk>`, `#substance-row-<pk>`), and both populated and empty filtered responses (including task counts ignoring `state` and registry count reaching `0` with an empty `#substance-rows`).
  - Exact canonical `HX-Push-Url` on `/lab/tasks/` (omitting default `state=active`, ignoring unknown `state`/`person`/`priority`, normalizing uppercase `person` initials, preserving `person=none`, trimming `q`, bare `/lab/tasks/` when default) and `/lab/registry/` (trimming `q`/`group`/`class`, keeping unknown `group`/`class` keys in both `HX-Push-Url` and a selected `<option>` in the form across subsequent `q` edits until cleared to `All`, bare `/lab/registry/` when empty).
  - Ordinary HTMX GET (`HX-Request: true`), HTMX history restore (`HX-Request: true` + `HX-History-Restore-Request: true`), and plain GET all returning complete page markup (`html`, `main#main`, `table`, filter form), `Vary` containing `HX-Request` and `HX-History-Restore-Request`, `HX-Push-Url` present ONLY on the ordinary HTMX GET, and CSP compliance (`assert_scripts`).
- [x] 1.2 Add a test in `webapp/tests/test_lab_script.py` asserting that `lab.js` no longer attaches a `[data-submit]` auto-submit handler (confirming `change` on a `[data-submit]` control does not call `requestSubmit()`).

## 2. Backend & Shared Helper
- [x] 2.1 Move `htmx_list_push_url()` to `webapp/orgsyndb_web/lists.py`, remove it from `webapp/inventory/views/common.py`, and update all six inventory view modules (`categories.py`, `items.py`, `bulk.py`, `notes.py`, `batches.py`, `vessels.py`) to import it from `orgsyndb_web.lists`.
- [x] 2.2 Add `@vary_on_headers("HX-Request", "HX-History-Restore-Request")` and canonical `HX-Push-Url` to `task_list` in `webapp/tasks/views.py` and `substance_list` in `webapp/registry/views.py`, passing unknown-key flags (`group_unknown`, `class_unknown`) to `registry/list.html`.

## 3. Templates & Script
- [x] 3.1 Wire live HTMX filtering on `webapp/tasks/templates/tasks/list.html` (`#filters`, `#filter-q`, `#task-counts`, `#task-rows`, stable `#task-row-<pk>` IDs) and `webapp/registry/templates/registry/list.html` (`#substance-count`, `#filters`, `#filter-q`, unknown-key selected `<option>` fallback for `group`/`class`, `#substance-rows`, stable `#substance-row-<pk>` IDs).
- [x] 3.2 Remove the obsolete `[data-submit]` handler and header comment from `webapp/orgsyndb_web/static/lab.js`.

## 4. Verification
- [x] 4.1 Run the tasks, registry, shell, script, and live-list area suites serially (`test_live_tasks_registry.py`, `test_task_list.py`, `test_registry_pages.py`, `test_lists_support.py`, `test_shell.py`, `test_lab_script.py`, `test_inventory_live_lists.py`) until green.
