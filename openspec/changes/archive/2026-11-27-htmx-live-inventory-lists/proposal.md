# Change: HTMX live filtering, search, sorting, and URL sync for inventory lists

## Why

The six inventory list views (`item_list`, `category_list` for intermediates
and commercial chemicals, `bulk_list`, `note_list`, `batch_list`, and
`vessel_list`) currently reload the entire page on every filter change, search
submission, stock-status selection, or sort-header click, and rely on
`[data-submit]` form submission in `lab.js` plus client-side URL rewriting on
detail pane selection.

Wiring the shared `<c-filter-bar>` and `<c-sort-th>` components with HTMX
`hx-get`, `hx-push-url`, `hx-select`, `hx-select-oob`, and `morph:outerHTML`
swaps—together with server-driven canonical `HX-Push-Url` on list views,
`HX-Replace-Url` on split-view detail endpoints, unified `#main:replace`
request synchronization, and reload-on-history-miss Back/Forward restoration—
gives instant, zero-flicker list updates while preserving full no-JS
progressive enhancement and strict CSP compliance.

## What Changes

- **Specs (`web-app`, `end-product-inventory`)**:
  - Add `Live lists` requirement to `web-app` defining the shared HTMX
    live-list contract (GET form fallback, scoped form triggers, shared
    `#main:replace` request synchronization, `morph:outerHTML` + `:morph`
    disjoint OOB swaps, `historyCacheSize: 0` and `refreshOnHistoryMiss: true`
    in `htmx-config` for clean Back/Forward history restore, canonical
    `HX-Push-Url` on non-restore HTMX list requests, `Vary` on `HX-Request`
    and `HX-History-Restore-Request`, and `HX-Replace-Url` on split-view
    detail endpoints).
  - Add `Live inventory lists` requirement to `end-product-inventory` opting
    in all six inventory lists (`item_list`, `category_list`, `bulk_list`,
    `note_list`, `batch_list`, `vessel_list`), defining the exact canonical
    `HX-Push-Url` query rules for each list, live sort/stock/reset links on
    `item_list`, and `HX-Replace-Url` on split-view detail endpoints.
- **Backend (`webapp/inventory/views/`)**:
  - Add `htmx_list_push_url(request, response, canonical_url)` helper in
    `webapp/inventory/views/common.py` that sets `HX-Push-Url` for non-restore
    HTMX requests (`request.htmx and not request.htmx.history_restore_request`).
  - Update `htmx_detail_or_redirect()` in `webapp/inventory/views/common.py` to
    set `HX-Replace-Url` on HTMX detail responses, preserving active filter
    query parameters from validated same-host `HX-Current-URL` (or
    `request.GET` when `keep_query=True`) with `selected` updated to the
    chosen record while keeping the response body as the single `#item-detail`
    fragment.
  - Add `@vary_on_headers("HX-Request", "HX-History-Restore-Request")` and
    canonical `HX-Push-Url` responses to `category_list_response`, `item_list`,
    `bulk_list`, `note_list`, `batch_list`, and `vessel_list`, and include
    `HX-Current-URL` in `@vary_on_headers` on split-view detail views.
- **Page shell, Components & Templates**:
  - Update `<meta name="htmx-config">` in
    `webapp/orgsyndb_web/templates/orgsyndb_web/base.html` to include
    `"historyCacheSize": 0` and `"refreshOnHistoryMiss": true` alongside
    `"allowEval": false` and `"includeIndicatorStyles": false`.
  - Update `cotton/filter_bar.html` so the conditional hidden `selected` input
    lives inside `<span id="filter-selected">` (containing
    `<input type="hidden" name="selected">` only when `selected` is non-empty).
  - Update `cotton/sort_th.html` to forward extra link attributes (`hx-get`)
    onto the header `<a>` element.
  - Wire HTMX live-list attributes with scoped triggers and
    `hx-sync="#main:replace"` on `category_list.html`, `item_list.html`
    (including `#item-head`, `#stock-entries`, disjoint `#list-summary` Reset
    link, `#more-filters-button`, `#filter-hidden`, and stable row `id`s),
    `bulk_list.html`, `note_list.html`, `batch_list.html`, and
    `vessel_list.html`, removing `data-submit` from inventory controls.
- **Client script (`webapp/orgsyndb_web/static/lab.js`)**:
  - Hide `button[type=submit]` on `form.lab-filters[hx-get]` when JS runs.
  - Scope `follow()`'s creation/update/removal of `input[name=selected]` to
    `#filter-selected` (falling back to `#filters` if absent) so dialog
    refreshes and OOB morphs never produce duplicate `selected` inputs.
  - Update `relink()` to keep `hx-get` in sync with `href`, and add an
    `htmx:configRequest` listener for `OWN_LINKS` so live sort, stock, and
    Reset clicks always request the currently relinked URL (preserving the
    selected item after in-place detail selection).
  - Preserve `ticked` checkboxes and row `focusable()` across live
    `#item-rows` swaps, and close `#stock-menu` popover on stock-link click.
  - Keep `[data-submit]` handler in `lab.js` intact until Stage 3B completes
    the remaining non-inventory lists (`tasks/list`, `registry/list`).

## Impact

- Affected specs: `openspec/specs/web-app/spec.md`,
  `openspec/specs/end-product-inventory/spec.md`.
- Affected code: `webapp/inventory/views/{common,categories,items,bulk,notes,batches,vessels}.py`,
  `webapp/orgsyndb_web/templates/orgsyndb_web/base.html`,
  `webapp/orgsyndb_web/templates/cotton/{filter_bar,sort_th}.html`,
  `webapp/inventory/templates/inventory/{category_list,item_list,bulk_list,note_list,batch_list,vessel_list}.html`,
  `webapp/orgsyndb_web/static/lab.js`.
- Affected tests: `webapp/tests/test_inventory_table.py`,
  `webapp/tests/test_shell.py`, and new
  `webapp/tests/test_inventory_live_lists.py`.
- No database migrations, no URL path changes, and no user-facing documentation
  changes.
