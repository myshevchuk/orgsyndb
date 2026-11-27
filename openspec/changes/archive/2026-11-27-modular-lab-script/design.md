# Design: Modularize lab.js with vendored Stimulus

## Context

`lab.js` currently registers every feature in a single ~1,260-line IIFE with
shared mutable closure variables, duplicating row-selection/keyboard-stepping
logic between `.item-layout` and `.planning-grid` and relying on one-time
startup scans for `[data-remember]`, `select[data-batch-for]`, and
`table[data-sortable]`.

## Decisions

### 1. Vendored Stimulus 3.2.2 UMD bundle & CSP compliance

- Vendor `@hotwired/stimulus@3.2.2`'s `dist/stimulus.umd.js` (~16 KB gzipped,
  zero `eval` or `Function` calls; exposes `globalThis.Stimulus`) and its MIT
  `LICENSE.md` saved as `LICENSE` under `webapp/orgsyndb_web/static/stimulus/`.
- Load `/lab/static/stimulus/stimulus.umd.js` with `defer` in `base.html`
  after `idiomorph-ext.min.js` and before `lab.js`.
- Start Stimulus with a custom schema overriding `actionAttribute`:
  ```js
  const schema = {
    ...Stimulus.defaultSchema,
    actionAttribute: "data-lab-action",
  };
  const application = Stimulus.Application.start(
    document.documentElement, schema);
  ```
  `production-planning` (`openspec/specs/production-planning/spec.md`)
  explicitly requires `<tr data-action="1">` on planning rows. Overriding
  `actionAttribute` to `"data-lab-action"` prevents Stimulus's `BindingObserver`
  from binding `data-action` attributes while keeping all existing specs and
  tests untouched.

### 2. Native CSS Anchor Positioning with `OrgSynLab.place` fallback

- Feature detection checks all four CSS Anchor Positioning primitives required
  for edge-clamped fallback positioning:
  ```js
  const supportsAnchor = () =>
    typeof CSS !== "undefined"
    && typeof CSS.supports === "function"
    && CSS.supports("anchor-name", "--a")
    && CSS.supports("position-anchor", "--a")
    && CSS.supports("top", "anchor(bottom)")
    && CSS.supports("position-try-fallbacks", "flip-block");
  ```
- In `webapp/orgsyndb_web/static/lab.css`, an identical `@supports
  (anchor-name: --a) and (position-anchor: --a) and (top: anchor(bottom)) and
  (position-try-fallbacks: flip-block)` block wires each popover button to its
  popover (`#stock-menu`, `#more-filters`, `#columns-menu`) and includes a
  named `@position-try --popover-fit` rule for the neither-above-nor-below
  viewport case:
  - Base placement: `position: fixed; inset: auto; margin: 0; top:
    calc(anchor(bottom) + 8px); left: max(16px, anchor(left)); max-width:
    calc(100vw - 2rem); max-height: calc(100vh - 2rem); position-try-fallbacks:
    flip-block, flip-inline, flip-block flip-inline, --popover-below-inset,
    --popover-above-inset, --popover-fit;`.
  - `@position-try --popover-below-inset` / `--popover-above-inset`: clamp
    horizontally to `left: 16px; right: auto;` (keeping narrow-viewport menus
    like `#stock-menu` completely within the 16 px viewport edges while staying
    below or above the trigger).
  - `@position-try --popover-fit`: `top: auto; bottom: 16px; left: 16px;
    right: auto;` (pinning 16 px from the bottom and left edges overlapping the
    button when neither side fits vertically, matching `OrgSynLab.place`'s
    `EDGE = 16` viewport-fit policy).
- In `lab.js`, `PopoverAnchorController` (`data-controller="popover-anchor"`
  on each `.lab-popup[popover]`):
  - Always closes any open `details.lab-view-menu[open]` when the popover
    opens (`toggle` with `event.newState === "open"`).
  - When `supportsAnchor()` is true, sets neither `dataset.placed` nor inline
    `left`/`top`, and binds no `scroll`/`resize` listeners.
  - When `supportsAnchor()` is false (including partial browser support), sets
    `dataset.placed = ""`, positions the popover via `OrgSynLab.place(...)`,
    and attaches `scroll`/`resize` reposition listeners while open (removing
    them on close or `disconnect()`).
- `OrgSynLab.place` remains exported unchanged on `globalThis.OrgSynLab`.

### 3. Controller decomposition & explicit listener scopes inside `lab.js`

All controllers live inside `webapp/orgsyndb_web/static/lab.js` (preserving
the single `/lab/static/lab.js` shell script and zero build chain). Every
controller binds listeners in `connect()` and removes every bound listener in
`disconnect()` so disconnecting and reconnecting never leaks or doubles
handlers:

1. **`split-list`** (`data-controller="split-list"`,
   `data-split-list-mode-value="htmx" | "local"`):
   - Attached to `.item-layout` in `cotton/split_layout.html` (`mode="htmx"`)
     and `.planning-grid` in `planning/list.html` (`mode="local"`).
   - Shared helpers: `makeFocusable(rows)` (`tabIndex = -1`),
     `markCurrent(rows, active)` (`aria-current="true"`),
     `replaceSelected(id)` (`OrgSynLab.paramSearch` + `history.replaceState`),
     and `stepIndex(rows, shown, from, key)` (`OrgSynLab.planStep`).
   - **Strict mode-specific selection timing**:
     - `local` mode (`.planning-grid`): all listeners bind strictly on
       `this.element` (table + `.planning-filters`). Plain click (including
       `a.planning-select` with `preventDefault()`) or `ArrowUp`/`ArrowDown`
       **immediately** marks `aria-current="true"`, switches `[data-article]`
       inspector blocks, focuses the row (`preventScroll: true` on click,
       normal focus on key), and updates `?selected=` via `replaceSelected`.
       Filter buttons filter rows via `OrgSynLab.planFilterShows` (reading
       `data-priority`, `data-action="1"`, `data-late="1"`), updating
       `[data-planning-count]`, `.planning-no-match`, and `.planning-status`.
     - `htmx` mode (`.item-layout`): plain click or `ArrowUp`/`ArrowDown`
       **only** triggers `htmx.trigger(row, "item-select")` (focusing the
       target row on Arrow keys) and does **not** alter `aria-current`,
       `location.search`, `#filter-selected`, or `OWN_LINKS` while the request
       is pending. `#item-detail.inert` is set `true` on `htmx:beforeRequest`
       and reset `false` on `htmx:afterRequest`; if the request fails or is
       aborted (no `htmx:afterSwap`), the previous pane, mark, URL, hidden
       `selected` field, and `OWN_LINKS` stay untouched. Only on
       `htmx:afterSwap` (and dialog refresh via `restoreAfterRefresh(ticked)`)
       does `follow(paneItem())` update `aria-current`, `replaceSelected`,
       `#filter-selected`, and `OWN_LINKS`.
     - Because view radios (`input[name=view]`), `[popovertarget=columns-menu]`,
       `#stock-menu a[hx-get]`, `#item-detail`, `#filters`, and `OWN_LINKS`
       live outside `.item-layout`, `htmx` mode registers its `document`-level
       listeners (`click`, `keydown`, `htmx:beforeRequest`, `htmx:afterRequest`,
       `htmx:configRequest`, `htmx:beforeSwap`, `htmx:afterSwap`) and radio
       `change` listeners in `connect()` and tears down every single one in
       `disconnect()`.
2. **`sortable-table`** (`data-controller="sortable-table"` on
   `table[data-sortable]` in `planning/list.html` and `inventory/item_page.html`):
   - Strictly element-scoped (`click` on `this.element` only). Wraps visible
     `thead` cells in `button.sort-header` on `connect()`, sorts rows via
     `OrgSynLab.sortOrder`, and manages `aria-sort`.
   - Uses shared `enhanceSortable` / `sortTable` helpers so `DialogController`'s
     in-place Idiomorph refresh re-enhances and re-applies active sort order on
     morphed tables without duplicating listeners.
3. **`dialog`** (`data-controller="dialog"` on `#lab-dialog` in `base.html`):
   - Because `a[data-dialog]` opener links live inside `<main>` (a sibling of
     `#lab-dialog`), `DialogController` registers document-level `click`,
     `htmx:responseError`, `htmx:sendError`, and `lab-saved` listeners plus
     element-level listeners on `#lab-dialog` and `#lab-dialog-body` in
     `connect()`, removing all of them in `disconnect()`.
   - Manages `htmx.ajax("GET", link.href, { target: dialogBody, swap:
     "innerHTML" })`, `showModal()`, `inert` on `#lab-dialog-body` while
     `posting || saving`, `.lab-field--error` focus, close/cancel guards, and
     `lab-saved` → `refreshPage()` (Idiomorph morph of `[data-refresh][id]`
     preserving `details.widget[open]`, `tableSort`, `boxScroll`, `ticked`,
     notifying any active `split-list` controller via
     `getControllerForElementAndIdentifier`), then closing and
     `focusAfterSave()`.
4. **`popover-anchor`** and **`view-menu`**:
   - `popover-anchor` on each `.lab-popup[popover]` (`item_list.html`):
     element-scoped `toggle`, plus `document` `scroll` / `window` `resize`
     only while open in fallback mode (cleaned up on close and `disconnect()`).
   - `view-menu` on `details.lab-view-menu` (`item_list.html`): document-level
     outside-click and `Escape` listeners bound in `connect()` and removed in
     `disconnect()`.
5. **`remember`** (`data-controller="remember"` alongside `data-remember="..."`
   in `item_list.html`):
   - Strictly element-scoped (`change` on `this.element`). Restores from
     `localStorage` on `connect()` and persists on `change`.
6. **`batch-narrow`** (`data-controller="batch-narrow"` added by `BatchField`
   alongside `data-batch-for="..."` in `webapp/inventory/forms.py`):
   - Scoped to `this.element.form` (`change` and `input` bound on
     `this.element.form` in `connect()`, removed in `disconnect()`). Only
     re-narrows when `event.target.name === this.element.dataset.batchFor`, so
     changing one delivery-note row's item select leaves every other row's
     batch select untouched. Handles both driver types: text substance inputs
     (new-item form) and `select` item dropdowns reading
     `selectedOptions[0].dataset.substance` (delivery-note rows), and connects
     automatically when inserted into `#lab-dialog`.

### 4. Preserved pure exports and document-level guards

- `globalThis.OrgSynLab` exports stay identical (`place`, `paramSearch`,
  `narrowBatches`, `sortOrder`, `planFilterShows`, `planStep`) so all existing
  Node `vm` pure-function tests run without a DOM.
- The no-eval `htmx.defineExtension("morph", ...)` override, `beforeprint`/
  `afterprint` collapsible-widget fallback, and live-list document guards
  (`hideLiveSubmits`, `actionSeq`/`lastInputSeq`/`htmx:confirm`,
  `htmx:oobBeforeSwap`/`htmx:oobAfterSwap`, `filterInFlight`/
  `snapshotFilters`/`restoreFilters`, modified-click passthrough on
  `a[href][hx-get]`) stay in named setup functions invoked whenever
  `typeof document !== "undefined"`, keeping existing Node `vm` live-list
  tests green even without Stimulus loaded.
- Stimulus registration runs inside `if (typeof Stimulus !== "undefined")`,
  allowing both full browser runtime and Node `vm` tests with the real
  vendored `stimulus.umd.js`.

## Alternatives Considered

- **Splitting controllers into multiple `<script>` files under `static/lab/`**:
  Rejected to avoid expanding the shell script list and HTTP requests without
  a bundler; `lab.js` stays a single deferred file with cleanly separated
  controller classes.
- **Native Light-DOM Web Components**: Rejected per operator decision in favor
  of vendored Stimulus (~16 KB gzipped, attaches directly to existing semantic
  elements without wrapper tags).
- **Dropping `OrgSynLab.place` altogether**: Rejected per operator decision;
  `OrgSynLab.place` stays active as a feature-detected JS fallback for
  browsers lacking full CSS Anchor Positioning support.
