# Tasks: HTMX live inventory lists

## 1. Tests (red-first)
- [x] 1.1 Create `webapp/tests/test_inventory_live_lists.py` covering every scenario in `web-app` (`Live lists`) and `end-product-inventory` (`Live inventory lists`):
  - Scoped HTMX live-filter attributes (`hx-get`, `hx-push-url="true"`, `hx-sync="#main:replace"`, scoped `hx-trigger` using `target:` / `from:#filter-q` / `from:#filter-container` etc., `hx-target`, `hx-select`, `hx-swap="morph:outerHTML"`, disjoint `hx-select-oob` with `:morph`) across all six inventory lists (`item_list`, `category_list`, `bulk_list`, `note_list`, `batch_list`, `vessel_list`), including disjoint Reset OOB targets on `item_list`.
  - Exact decoded canonical `HX-Push-Url` (path + query) on HTMX list GETs for all six lists, including invalid/empty filter params, cross-category params ignored, and empty split-view lists omitting `selected`.
  - Plain GET and `HX-History-Restore-Request: true` returning the complete page with no `HX-Push-Url` header, and `Vary` containing `HX-Request` and `HX-History-Restore-Request`.
  - `HX-Replace-Url` on all five split-view detail endpoints (`item_detail`, `intermediate_detail`, `chemical_detail`, `bulk_detail`, `note_detail`) for same-host `HX-Current-URL`, foreign-host `HX-Current-URL`, and absent `HX-Current-URL`, single-element `#item-detail` body preserved, and `Vary` containing `HX-Request` and `HX-Current-URL`.
  - CSP compliance (`assert_scripts` including allowed morph swaps) on every live inventory list page.
- [x] 1.2 Update `webapp/tests/test_shell.py` to assert `htmx-config` includes `"historyCacheSize": 0` and `"refreshOnHistoryMiss": true` alongside `"allowEval": false`.
- [x] 1.3 Update `webapp/tests/test_inventory_table.py` (`test_the_form_above_the_table` and `test_the_more_filters`) so the `item_list` filter assertions check `#filters`'s HTMX live triggers (`change target:select`, `from:#filter-container`, `from:#filter-compartment`, `from:#filter-box`) rather than `data-submit` on the controls.

## 2. Backend (`webapp/inventory/views/`)
- [x] 2.1 Add `htmx_list_push_url()` and update `htmx_detail_or_redirect()` (setting `HX-Replace-Url` from validated same-host `HX-Current-URL` or `request.GET` when `keep_query=True` with `selected` updated) in `webapp/inventory/views/common.py`.
- [x] 2.2 Add `@vary_on_headers("HX-Request", "HX-History-Restore-Request")` and exact canonical `HX-Push-Url` responses to `category_list_response` (`categories.py`), `item_list` (`items.py`), `bulk_list` (`bulk.py`), `note_list` (`notes.py`), `batch_list` (`batches.py`), and `vessel_list` (`vessels.py`), and add `"HX-Current-URL"` to `@vary_on_headers` on all five split-view detail views.

## 3. Shell, Components, Templates & Script
- [x] 3.1 Update `<meta name="htmx-config">` in `webapp/orgsyndb_web/templates/orgsyndb_web/base.html` to add `"historyCacheSize": 0` and `"refreshOnHistoryMiss": true`.
- [x] 3.2 Update `webapp/orgsyndb_web/templates/cotton/filter_bar.html` (`<span id="filter-selected">`) and `webapp/orgsyndb_web/templates/cotton/sort_th.html` (forwarding link attributes onto `<a>`).
- [x] 3.3 Wire HTMX live filtering with `hx-sync="#main:replace"` and scoped triggers (`id="filter-q"`, `target:select`, `target:input[type=checkbox]`, `from:#filter-container/compartment/box`) on `category_list.html`, `item_list.html` (including `#item-head`, `#stock-entries`, disjoint `#list-summary` Reset link, `#more-filters-button`, `#filter-hidden`, and stable row `id`s), `bulk_list.html`, `note_list.html`, `batch_list.html`, and `vessel_list.html`, removing `data-submit` from inventory controls.
- [x] 3.4 Update `webapp/orgsyndb_web/static/lab.js` to hide `button[type=submit]` on `form.lab-filters[hx-get]`, scope `follow()`'s `input[name=selected]` writes to `#filter-selected`, sync `hx-get` in `relink()` + `htmx:configRequest` for `OWN_LINKS`, preserve `ticked` checkboxes and `focusable()` across live `#item-rows` swaps, and close `#stock-menu` popover on stock-link click.

## 4. Verification
- [x] 4.1 Run the inventory, shell, and script area suites serially (`test_inventory_live_lists.py`, `test_inventory_categories.py`, `test_inventory_lists.py`, `test_inventory_table.py`, `test_inventory_detail.py`, `test_inventory_dialogs.py`, `test_inventory_bulk.py`, `test_inventory_notes.py`, `test_inventory_batches.py`, `test_inventory_vessels.py`, `test_shell.py`, `test_lab_script.py`, `test_lists_support.py`) until green.
