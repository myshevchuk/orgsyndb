## ADDED Requirements

### Requirement: Live inventory lists
All six inventory lists—`/lab/inventory/end-products/`, `/lab/inventory/intermediates/`, `/lab/inventory/chemicals/`, `/lab/inventory/end-products/bulk/`, `/lab/inventory/deliveries/`, `/lab/inventory/batches/`, and `/lab/inventory/vessels/`—SHALL implement live list updates (web-app "Live lists"):

- Each list's filter form updates its table body in place with `morph:outerHTML` and updates its count (and, on split-view lists, `#item-detail` and `#filter-selected`) out of band with disjoint `:morph` selectors, using triggers scoped exclusively to its own controls (`submit`, a single `change` clause — `change target:select` when only selects are inside `#filters`, or `change target:(select, input[type=checkbox])` when both selects and checkboxes are inside `#filters` — and `search from:#filter-q` / `input delay:200ms from:#filter-q` where present) and synchronizing with split-view row requests on `#main:replace`.
- On `/lab/inventory/end-products/`, `#filters` also triggers on `change from:#filter-container`, `change from:#filter-compartment`, and `change from:#filter-box`; the sortable column header links (`#item-head`), stock-status menu links (`#stock-entries`), and `Reset` link in `#list-summary` ALSO update `#item-rows` and dependent regions in place via HTMX with `hx-sync="#main:replace"`, using disjoint OOB targets that morph `#filters:morph` and `#more-filters:morph` (without separately targeting their children `#filter-selected` or `#filter-hidden`) so visible filter controls stay synchronized with the applied response and URL, while keeping their `href` / `method="get"` fallbacks.
- Each list's non-restore HTMX GET response sets `HX-Push-Url` to its canonical path and cleaned query:
  - `/lab/inventory/end-products/`: nonempty `q`, `category`, `stock`, `container`, `compartment`, `box`, effective `sort` (default `category`), `dir=desc` only when descending, and resolved `selected` (omitted when empty);
  - `/lab/inventory/intermediates/`: nonempty `q`, `location`, `class`, `flask=1`, `old=1`, and resolved `selected` substance key (omitted when empty);
  - `/lab/inventory/chemicals/`: nonempty `q`, `location`, `group`, `supplier`, `sealed=1`, and resolved `selected` substance key (omitted when empty);
  - `/lab/inventory/end-products/bulk/`: trimmed `q`, trimmed `location`, valid `source`, `flask=1`, and resolved `selected` vessel ID (omitted when empty);
  - `/lab/inventory/deliveries/`: trimmed `q`, numeric `item`, and resolved `selected` note ID (omitted when empty);
  - `/lab/inventory/batches/`: trimmed `q`;
  - `/lab/inventory/vessels/`: valid `kind` and `empty=1`.
- The split-view detail endpoints (`/lab/inventory/items/<id>/detail/`, `/lab/inventory/intermediates/<key>/`, `/lab/inventory/chemicals/<key>/`, `/lab/inventory/end-products/bulk/<id>/`, and `/lab/inventory/deliveries/<id>/detail/`) set `HX-Replace-Url` to their list URL with the active filters and `selected` naming the requested record.

#### Scenario: Live filtering on category lists
- **WHEN** a test client requests `/lab/inventory/intermediates/?location=Regal+1&sealed=1&selected=missing`, `/lab/inventory/intermediates/?location=nowhere`, and `/lab/inventory/chemicals/?sealed=1&flask=1` with `HX-Request: true`
- **THEN** each page's filter form carries `hx-get`, `hx-push-url="true"`, `hx-sync="#main:replace"`, scoped triggers, `hx-target="#item-rows"`, `hx-select="#item-rows"`, `hx-swap="morph:outerHTML"`, and `hx-select-oob` naming `#category-count:morph`, `#item-detail:morph`, and `#filter-selected:morph`; the first sets `HX-Push-Url` to `/lab/inventory/intermediates/?location=Regal+1&selected=<resolved>` dropping `sealed`; the second sets `/lab/inventory/intermediates/?location=nowhere` with no `selected`; and the third sets `/lab/inventory/chemicals/?sealed=1&selected=<resolved>` dropping `flask`

#### Scenario: Live filtering, sorting, stock status, and reset on the item list
- **WHEN** a test client requests `/lab/inventory/end-products/?category=Ester&stock=bogus&sort=stock&dir=desc&q=` with `HX-Request: true`
- **THEN** `#filters`, `#item-head` sort links, `#stock-entries` links, and the `#list-summary` reset link carry HTMX live attributes targeting `#item-rows` with `morph:outerHTML` and `hx-sync="#main:replace"`, `#filters` triggers on `#filter-container`, `#filter-compartment`, and `#filter-box`, the sort, stock, and Reset links' `hx-select-oob` morph `#filters:morph` and `#more-filters:morph` without overlapping `#filter-selected` or `#filter-hidden`, and `HX-Push-Url` equals `/lab/inventory/end-products/?category=Ester&sort=stock&dir=desc&selected=<resolved>`

#### Scenario: Live filtering on bulk, delivery, batch, and vessel lists
- **WHEN** a test client requests `/lab/inventory/end-products/bulk/?flask=1&source=bogus&q=+CH+`, `/lab/inventory/deliveries/?q=+LS+&item=abc`, `/lab/inventory/batches/?q=+B-1+`, and `/lab/inventory/vessels/?kind=bogus&empty=1` with `HX-Request: true`
- **THEN** each list's filter form carries scoped HTMX live attributes targeting its table body with `morph:outerHTML`, `hx-sync="#main:replace"`, and `:morph` OOB targets for its count (plus `#item-detail:morph,#filter-selected:morph` on bulk and deliveries), and their `HX-Push-Url` headers drop invalid values, trim `q`, and resolve `selected` on split lists

#### Scenario: Inventory detail endpoints replace the list URL
- **WHEN** a test client requests `/lab/inventory/items/<id>/detail/` with `HX-Request: true` and `HX-Current-URL: http://testserver/lab/inventory/end-products/?category=Ester&selected=999`, `/lab/inventory/intermediates/<key>/?location=Regal+1` with `HX-Request: true`, and `/lab/inventory/items/<id>/detail/` with a foreign-host `HX-Current-URL`
- **THEN** the first sets `HX-Replace-Url` to `/lab/inventory/end-products/?category=Ester&selected=<id>`, the second to `/lab/inventory/intermediates/?location=Regal+1&selected=<key>`, and the third to `/lab/inventory/end-products/?selected=<id>`, and all three return only `#item-detail`
