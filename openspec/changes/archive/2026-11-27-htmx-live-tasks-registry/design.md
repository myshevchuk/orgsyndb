# Design: HTMX live task and registry lists

## Context

Both `/lab/tasks/` and `/lab/registry/` already use `<c-filter-bar>`,
`<c-filter-search>`, `<c-filter-select>`, and `<c-list-heading>` (Stage 2),
and the page shell already loads `idiomorph-ext.min.js` with `hx-ext="morph"`,
a no-eval `morph` override, `historyCacheSize: 0`, and
`refreshOnHistoryMiss: true` (Stages 1 and 3A).

## Decisions

### 1. Shared `htmx_list_push_url` in `orgsyndb_web.lists` (no re-export shim)

- Move `htmx_list_push_url(request, response, canonical_url)` from
  `webapp/inventory/views/common.py` to `webapp/orgsyndb_web/lists.py`,
  removing it from `inventory/views/common.py` and updating all six inventory
  view modules (`categories.py`, `items.py`, `bulk.py`, `notes.py`,
  `batches.py`, `vessels.py`) alongside `tasks/views.py` and
  `registry/views.py` to import it directly from `orgsyndb_web.lists`.

### 2. Canonical `HX-Push-Url` rules and unknown registry filter preservation

- **`/lab/tasks/`**: built from cleaned `Filters` (`Filters.from_query`):
  - `state`: omitted when equal to the default `"active"`; included otherwise
    (`planned`, `running`, `followup`, `ended`, `cancelled`, `all`).
  - `person`: included when non-empty (`none` or valid uppercase account
    initials; unknown dropped).
  - `priority`: included when non-empty (valid `Priority`; unknown dropped).
  - `q`: included when non-empty after `.strip()`.
  - If all parameters are omitted, `HX-Push-Url` is `/lab/tasks/`.
- **`/lab/registry/`**: built from trimmed `q`, `group`, and `class`:
  - Each parameter is included when non-empty after `.strip()`.
  - Unknown `group` or `class` keys are **kept** in both `HX-Push-Url` and
    the `<select>` element (rendered as a selected `<option value="{{ group }}"
    selected>{{ group }}</option>` when not among known vocabulary keys, and
    likewise for `class`), because `substance_list` intentionally returns zero
    rows for an unknown key (`lab-registry: Registry pages`, "a key that names
    no term lists none; the form keeps their values"). Keeping the unknown
    option selected guarantees that typing in `q` submits the unknown filter
    rather than silently resetting it to `All`, until the user explicitly picks
    `All` (`value=""`).
  - If all parameters are omitted, `HX-Push-Url` is `/lab/registry/`.

### 3. Markup, triggers, and disjoint `:morph` OOB targets

- **`tasks/list.html`**:
  - `<c-filter-bar id="filters" action="/lab/tasks/" :toolbar="False" hx-get="/lab/tasks/" hx-push-url="true" hx-sync="#main:replace" hx-trigger="submit, search from:#filter-q, input delay:200ms from:#filter-q, change target:select" hx-target="#task-rows" hx-select="#task-rows" hx-swap="morph:outerHTML" hx-select-oob="#task-counts:morph">`
  - `<c-filter-search id="filter-q" ... />`
  - `<p id="task-counts" class="count">...</p>`
  - `<tbody id="task-rows">` with `<tr id="task-row-{{ task.pk }}" ...>`
- **`registry/list.html`**:
  - `<c-list-heading :title="heading" count="{{ substances|length }}" count_id="substance-count">`
  - `<c-filter-bar id="filters" action="/lab/registry/" :toolbar="False" hx-get="/lab/registry/" hx-push-url="true" hx-sync="#main:replace" hx-trigger="submit, search from:#filter-q, input delay:200ms from:#filter-q, change target:select" hx-target="#substance-rows" hx-select="#substance-rows" hx-swap="morph:outerHTML" hx-select-oob="#substance-count:morph">`
  - `<c-filter-search id="filter-q" ... />`
  - `<tbody id="substance-rows">` with `<tr id="substance-row-{{ found.pk }}">`
- Neither form has checkboxes, so a single `change target:select` clause has
  no `handledFor` collision, and omitting `changed` on `input delay:200ms`
  avoids stale `lastValue` state.

### 4. Removing obsolete `[data-submit]` from `lab.js`

- No template in `webapp/` carries `data-submit` after Stage 3A. Remove the
  `[data-submit]` button-hiding loop, delegated `change` listener, and header
  bullet from `webapp/orgsyndb_web/static/lab.js`.
- Leave `snapshotFilters()` in `lab.js` scoped to inventory split-view lists,
  since only split-view `tr[data-item][hx-get]` row clicks consume saved
  filter snapshots.

## Alternatives Considered

- **Re-exporting `htmx_list_push_url` from `inventory.views.common`**:
  Rejected under pre-1.0 rules; all six callers live in-tree and import
  `orgsyndb_web.lists` directly.
- **Dropping unknown `group` / `class` keys from `/lab/registry/`**:
  Rejected because `substance_list` intentionally returns zero rows for
  unknown keys; keeping them selected in the `<select>` keeps URL, form, and
  empty table in sync across subsequent live search edits.
