# Design: HTMX live inventory lists

## Context

All six inventory lists share `<c-filter-bar>`, `<c-split-layout>`, and
`<c-sort-th>` (Stage 2), and the page shell loads `idiomorph-ext.min.js` with
`hx-ext="morph"` and a strict no-eval runtime `morph` handler (Stage 1).

## Decisions

### 1. Single endpoint per list using `hx-select` + disjoint `hx-select-oob`

- Every inventory list view continues rendering its full HTML page on GET.
  HTMX extracts the primary table body (`hx-target` + `hx-select`) and
  secondary regions (`hx-select-oob`) from that single HTML response.
- In HTMX 2.0.11, `hx-select-oob` splits each entry with `split(":", 2)` and
  removes each matched element from the response fragment in order. Every OOB
  entry therefore uses `#<id>:morph` (allowed by `web-app` `Scripts` and
  interpreted as outerHTML morph by the runtime `morph` handler), and no
  `hx-select-oob` list ever includes both an ancestor and a descendant.
- Specifically, on `item_list.html`:
  - `#filters` uses:
    `#item-count:morph,#list-summary:morph,#item-head:morph,#item-detail:morph,#stock-filter:morph,#stock-entries:morph,#more-filters-button:morph,#filter-selected:morph,#filter-hidden:morph`.
  - The click-driven link controls (`#item-head` sort links, `#stock-entries` links, and the Reset link in `#list-summary`) all use **disjoint** targets:
    `#item-count:morph,#list-summary:morph,#item-head:morph,#item-detail:morph,#stock-filter:morph,#stock-entries:morph,#more-filters-button:morph,#filters:morph,#more-filters:morph`
    (omitting `#filter-selected:morph` and `#filter-hidden:morph`, since both
    live inside `#filters` and are morphed as part of `#filters:morph`).
    Morphing `#filters` and `#more-filters` on sort and stock clicks as well
    as Reset ensures visible filter controls reconcile with the applied server
    response even when a click cancels an in-flight filter change.

### 2. Scoped triggers (zero global listeners, zero `handledFor` collisions, zero stale `lastValue`)

- In HTMX 2.0.11:
  - bare `from:select` and `from:input[type=search]` search the entire
    document (wrongly matching the shell's `.site-search` and `#row-height`);
  - ungrouped `from:#more-filters select` splits at whitespace;
  - `mt()` adds the element to `event.handledFor` **before** checking
    `u.target`, so two `change target:...` clauses on the same `<form>` cause
    the first clause to swallow the `change` event before the second clause
    runs;
  - `changed` caches `lastValue` in a WeakMap on `#filters`, which becomes
    stale when an Idiomorph OOB morph clears `#filter-q` on Reset (silently
    suppressing a repeat search for the same text).
- Therefore:
  - Search inputs in live filter forms carry `id="filter-q"`, and debounced
    search binds directly to that input without `changed` (the DOM `input`
    event already fires only on value changes):
    `search from:#filter-q, input delay:200ms from:#filter-q`.
  - In-form selects and checkboxes use a **single** `change` clause on
    `#filters`: `change target:select` when only selects live inside `#filters`
    (`item_list.html`), or HTMX's parenthesized selector syntax
    `change target:(select, input[type=checkbox])` when both selects and
    checkboxes live inside `#filters` (`category_list.html`, `bulk_list.html`,
    `vessel_list.html`).
  - On `item_list.html`, the three externally associated selects in
    `#more-filters` (`form="filters"`) bind by exact ID with no spaces:
    `change from:#filter-container, change from:#filter-compartment, change from:#filter-box`.

### 3. Unified request synchronization (`hx-sync="#main:replace"`)

- All live list controls (`#filters`, `#item-head`, `#stock-entries`, the
  Reset link) AND split-view `#item-rows` (whose rows trigger detail requests)
  share `hx-sync="#main:replace"`.
- Whichever user action is latest (filtering, sorting, choosing a stock level,
  resetting, or selecting a row) aborts any in-flight request from any of the
  others, preventing stale detail responses from overwriting newer list panes
  or applying outdated `HX-Replace-Url` headers.

### 4. Clean Back/Forward history restore (`historyCacheSize: 0`, `refreshOnHistoryMiss: true`)

- HTMX's default history cache (`historyCacheSize: 10`,
  `refreshOnHistoryMiss: false`) restores serialized HTML snapshots from
  `localStorage` or swaps `#main`/`<body>` without re-running `lab.js`'s
  startup listeners, which can leave form inputs out of sync with the URL or
  disconnect `.item-layout` view-switch radio bindings.
- Setting `"historyCacheSize": 0` and `"refreshOnHistoryMiss": true` in
  `base.html`'s `<meta name="htmx-config">` guarantees that Back/Forward
  always performs a clean full-page reload from the server, so filter
  controls, table rows, detail pane, and `lab.js` bindings always agree with
  the restored URL.
- List views still return the full HTML page without `HX-Push-Url` if an
  explicit `HX-History-Restore-Request: true` arrives, and vary on
  `HX-Request` and `HX-History-Restore-Request`.

### 5. Exact canonical `HX-Push-Url` rules and `HX-Replace-Url` on details

- `htmx_list_push_url(request, response, url)` in `inventory/views/common.py`
  sets `response["HX-Push-Url"] = url` only when
  `request.htmx and not request.htmx.history_restore_request`.
- Canonical URL per inventory list:
  - **`item_list`**: `LIST + filters.link(filters.sort, filters.descending, selected=selected)`
    — keeps nonempty `q`, `category`, `stock`, `container`, `compartment`,
    `box`; always includes effective `sort` (default `category`); includes
    `dir=desc` only when descending; includes resolved `selected` (omitted
    when empty).
  - **`category_list`** (intermediates / chemicals): `config.base_url` plus
    encoded active parameters applicable to that category (`q`, `location`,
    plus `class`/`flask=1`/`old=1` for intermediates or
    `group`/`supplier`/`sealed=1` for chemicals) and resolved `selected`
    substance key (omitted when empty).
  - **`bulk_list`**: `BULK` plus trimmed `q`, trimmed `location`, valid
    `source`, `flask=1` when active, and resolved `selected` vessel ID
    (omitted when empty).
  - **`note_list`**: `DELIVERIES` plus trimmed `q`, numeric `item` when
    valid, and resolved `selected` note ID (omitted when empty).
  - **`batch_list`**: `BATCHES` plus trimmed `q` when non-empty.
  - **`vessel_list`**: `VESSELS` plus valid `kind` and `empty=1` when active.
- `htmx_detail_or_redirect()` in `inventory/views/common.py`:
  - Preserves existing non-HTMX redirect behavior and single-element
    `#item-detail` HTMX response body.
  - Sets `HX-Replace-Url` to `f"{base_url}?{params.urlencode()}"` where
    `params` starts from the query of `request.htmx.current_url` when it
    passes `url_has_allowed_host_and_scheme` for `{request.get_host()}`, else
    `request.GET` when `keep_query=True`, else empty, with
    `params["selected"] = str(selected)`.
  - Split-view detail views vary on `HX-Request` and `HX-Current-URL`.

### 6. `lab.js` synchronization with live swaps and relinked `hx-get`

- Hide `button[type=submit]` on `form.lab-filters[hx-get]` at startup (leaving
  it visible without JS).
- Update `follow(id)` to create, update, or remove `input[name=selected]`
  inside `#filter-selected` (falling back to `#filters` if absent) so both
  dialog refreshes (`refreshPage`) and HTMX OOB morphs write to the exact same
  container and never create duplicate `selected` fields.
- Update `relink(link, id)` to update both `href` and `hx-get` (when present).
  Because HTMX 2.0.11 captures `hx-get` in a closure during element
  initialization, add an `htmx:configRequest` listener for links matching
  `OWN_LINKS` that sets `event.detail.path = elt.getAttribute("hx-get")` when
  present so live sort, stock, and Reset clicks always request the latest
  relinked URL carrying the currently selected item.
- Capture checked `input[name=item]` values on `htmx:beforeSwap` targeting
  `#item-rows` and restore them plus `focusable()` on `htmx:afterSwap`
  targeting `#item-rows`.
- Close `#stock-menu` popover on click of `#stock-menu a[hx-get]`.
- Track a monotonic sequence counter for `#filter-q` `input` events vs. newer
  `#main:replace` requests in `htmx:confirm`: if a delayed `input` trigger on
  `form.lab-filters[hx-get]` fires after a newer action has already started,
  cancel it via `event.preventDefault()` before `hx-sync="#main:replace"`
  aborts the newer request.
- Register a capturing `click` listener on `document` that stops propagation
  (without `preventDefault()`) when a modified or non-primary click
  (`ctrlKey || metaKey || shiftKey || altKey || button !== 0`) targets
  `a[href][hx-get]`, preserving native open-in-new-tab/window behavior.

## Alternatives Considered

- **Separate Django fragment endpoints per list**: Rejected in favor of
  `hx-select` + `hx-select-oob` over existing full-page views.
- **Relying on HTMX's built-in `localStorage` history cache**: Rejected
  because active filter inputs sit outside normal swaps and `lab.js` binds
  `.item-layout` view-switch listeners once at startup; setting
  `historyCacheSize: 0` + `refreshOnHistoryMiss: true` makes Back/Forward
  unconditionally clean.
- **Updating `hx-get` via `htmx.process(link)` after `relink()`**: Rejected
  because HTMX skips already-initialized elements; overriding
  `event.detail.path` in `htmx:configRequest` is exact and side-effect-free.
