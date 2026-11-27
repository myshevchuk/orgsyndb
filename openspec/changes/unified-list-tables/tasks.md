# Tasks: Unified list tables

## 1. Tests (red-first)

- [ ] 1.1 Shared sorting (`web-app` "Main lists", column values): unit
  tests for the column model in `orgsyndb_web/lists.py`:
  - parsing `sort` / `dir` against a list's columns and default;
  - the header-link toggle;
  - `aria-sort`;
  - the canonical query pairs omitting the default order;
  - `sort_value`: numbers and amounts across mg/g and µmol/mmol, masses
    before amounts of substance, dates, text regardless of case, numbers
    and dates before text, empty and `–` last in either direction,
    equal values keeping the default order.

  Extend `webapp/tests/test_lists_support.py`.
- [ ] 1.2 Main lists, per list (`web-app` "Main lists" scenarios): for
  each of the ten lists, cover:
  - `table.main-table`, `#item-rows`, and rows with `data-item`,
    `hx-get` to the details endpoint and `hx-trigger="item-select"`;
  - `aria-sort` on the default column without `sort`, and on the
    requested column with `sort` / `dir`;
  - header links (toggle, filters and `selected` kept, none on
    unsortable columns);
  - an unknown key falling back to the default order;
  - the selection marked with `aria-current`;
  - the view cookie, with the planning list defaulting to details.

  Put the tests in the list's area test file. New files:
  `test_main_lists.py` for the cross-list scenarios and the table-class
  sweep, `test_inventory_batch_details.py`,
  `test_inventory_vessel_details.py`, `test_task_details.py` and
  `test_registry_details.py`.
- [ ] 1.3 Details endpoints (`end-product-inventory` "Batch details",
  "Vessel details"; `task-tracker` "Task details"; `lab-registry`
  "Substance details"; `production-planning` "Planning list" details):
  cover content, signed-in links, the HTMX fragment, the redirect
  without HTMX, 404 for an unknown key, `HX-Replace-Url`, and a POST to
  `/lab/tasks/<number>/detail/` leaving the task unchanged.
- [ ] 1.4 Live lists (`end-product-inventory` "Live inventory lists",
  `task-tracker` "Live task list", `lab-registry` "Live substance
  list", the planning list's filter form): update the existing
  assertions in `test_inventory_live_lists.py` and
  `test_live_tasks_registry.py` to `#item-rows`, the new OOB targets,
  `selected` and `sort` in `HX-Push-Url`, and the item list no longer
  pushing the default `sort=category`. Add the planning list's live
  form and canonical address.
- [ ] 1.5 Planning list (`production-planning` "Planning list"): rewrite
  `test_planning_list.py` and `test_planning_inspector.py` for:
  - server-side `show` and `all`;
  - the count;
  - the empty-list messages;
  - the details endpoint;
  - the `Artikel` link to the substance's page;
  - no `data-sortable`, `data-priority`, `data-action` or `data-late`
    on the main table.
- [ ] 1.6 Client-sortable auxiliary tables (`web-app` "Widgets", "Widget
  and pane tables sort in the browser"): cover `data-sortable`, unique
  `id`s and ISO `data-sort` keys on the item page, the substance page,
  the overview and every list's details pane, and their absence on
  `kv-table`s, the consumption quarter tables and the change history.
  Use `test_widgets_item_page.py`, `test_widgets_substance_page.py`,
  `test_widgets_overview.py`, `test_widgets_history.py` and the details
  test files.
- [ ] 1.7 Table classes (`web-app` "Main lists", "Two table classes"):
  a sweep over the pages the scenario names, asserting every `table`
  carries exactly one of `main-table` and `aux-table`.
- [ ] 1.8 Script (`test_lab_script.py`, `test_stimulus_controllers.py`):
  - `split-list` has no local mode;
  - `planFilterShows` is no longer exported;
  - htmx-mode selection works on `.main-table tbody tr[data-item]`.

  Remove the tests of the removed helpers.

## 2. Shared sorting

- [ ] 2.1 Add the column model, `Order`, the header links, the canonical
  pairs and `sort_value` to `webapp/orgsyndb_web/lists.py`.
- [ ] 2.2 Move the item list (`inventory/views/items.py`) onto it, keeping
  its columns, its default `category` and its order text, and dropping
  the default order from its canonical URL.
- [ ] 2.3 Render the header row of every main table from the column model
  with `c-sort-th`, with live `hx-get` attributes like `#item-head`.

## 3. Lists

- [ ] 3.1 Bulk, delivery, intermediate and commercial chemical lists:
  columns, sorting and canonical URLs (`inventory/views/{bulk,notes,
  categories}.py` and their templates).
- [ ] 3.2 Batch and vessel lists: split layout, view switch and cookies,
  sorting, details endpoints and templates, and URL routes
  (`inventory/views/{batches,vessels}.py`, `inventory/urls.py`).
- [ ] 3.3 Task list: split layout, sorting, the details endpoint routed
  before `<number>/<action>/`, and templates (`tasks/views.py`,
  `tasks/urls.py`, `tasks/templates/tasks/`).
- [ ] 3.4 Substance list: split layout, sorting, the details endpoint and
  templates (`registry/views.py`, `registry/urls.py`,
  `registry/templates/registry/`).
- [ ] 3.5 Planning list: the filter form (`show`, `all`), sorting, the
  split layout, the details endpoint and templates, and the removal of
  the list widget, the inspector blocks and the filter buttons
  (`planning/views.py`, `planning/urls.py`,
  `planning/templates/planning/`).

## 4. Tables, styles and script

- [ ] 4.1 Give every table under `webapp/*/templates/` exactly one of
  `main-table` and `aux-table`, and `kv-table` as the key–value
  modifier.
- [ ] 4.2 Mark the client-sortable auxiliary tables with `data-sortable`,
  unique `id`s and `data-sort` keys (design decision 7).
- [ ] 4.3 `lab.css`: define `.main-table` and `.aux-table` with a single
  sort-indicator style. Remove the rules of `inventory-table`,
  `item-table`, `task-table`, `widget-table`, `detail-table`,
  `planning-table`, `planning-*` and `#movements`.
- [ ] 4.4 `lab.js`: remove `split-list`'s local mode, `planFilterShows`
  and any helper only that mode used (`planStep` stays, `stepIndex` uses
  it). Widen the row selector to
  `.main-table`, and update the header comment.
- [ ] 4.5 German catalogues: translate the new strings and compile.

## 5. Verification

- [ ] 5.1 Run the area tests serially (`test_lists_support.py`,
  `test_main_lists.py`, the details files, `test_inventory_*` lists and
  live lists, `test_live_tasks_registry.py`, `test_task_*`,
  `test_registry_*`, `test_planning_list.py`,
  `test_planning_inspector.py`, `test_widgets_*.py`,
  `test_lab_script.py`, `test_stimulus_controllers.py`,
  `test_back_links.py`)
  until green.
- [ ] 5.2 Manual check in a browser on the local demo database:
  - sort, select by click and by arrow keys, and switch views on each
    main list;
  - sort a widget table and a pane table;
  - compare the two table styles in light and dark mode.
