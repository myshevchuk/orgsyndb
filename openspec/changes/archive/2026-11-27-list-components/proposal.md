## Why

List and widget templates across `inventory`, `planning`, `tasks`, `registry`,
and `overview` repeat the same HTML scaffolding for headings, filter toolbars,
split master-detail panes, sortable column headers, and widgets, while
`inventory/views/{items,bulk,vessels}.py` and `tasks/views.py` repeat small
query-choice validation and nullable-key sorting helpers.

Extracting reusable `django-cotton` components under
`webapp/orgsyndb_web/templates/cotton/` and shared Python list helpers in
`webapp/orgsyndb_web/lists.py` removes template boilerplate and prepares a
single set of filter-bar and split-layout components for HTMX live list
updates in the next changes, without altering rendered markup or behavior.

## What Changes

- **Configuration (`webapp/`)**:
  - Add `django-cotton>=2.9` to `webapp/pyproject.toml` and `webapp/uv.lock`.
  - Register `"django_cotton"` in `INSTALLED_APPS` in
    `webapp/orgsyndb_web/settings.py`.
- **Shared Python list helpers (`webapp/orgsyndb_web/lists.py`)**:
  - Add `clean_choice(value, allowed, default="")` and
    `sort_rows(rows, value, descending=False)` and adopt them across
    `inventory/views/{items,bulk,vessels}.py` and `tasks/views.py`.
- **Reusable Cotton components (`webapp/orgsyndb_web/templates/cotton/`)**:
  - `widget.html` (`<c-widget>`): renders `section.widget` or collapsible
    `details.widget` (`id`, `title`, `count`, `count_attr`, `note`,
    `note_class`, `collapsible`, `open`, `flush`, `extra_class`, plus optional
    `note_slot`, `head_extra`, and `before_body` slots).
  - `list_heading.html` (`<c-list-heading>`): renders `div.lab-heading` with
    `h1`, optional count (`count`, `count_id`, `count_refresh`, or
    `count_slot`), and optional `actions` slot (optionally wrapped in
    `div.lab-heading__actions`).
  - `filter_bar.html` (`<c-filter-bar>`), `filter_search.html`
    (`<c-filter-search>`), `filter_select.html` (`<c-filter-select>`), and
    `filter_check.html` (`<c-filter-check>`): standardize `.lab-toolbar`,
    `.lab-filters`, hidden `selected` input, submit button, and
    `.lab-toolbar__end` slot while forwarding arbitrary HTML/HTMX attributes.
  - `split_layout.html` (`<c-split-layout>`): encapsulates `.item-layout`
    (with optional `item-layout--split` via `split`), `data-view`, optional
    `data-cookie`, `.table-scroll.table-sticky` (with optional `id` via
    `scroll_id`, e.g. `category-table-scroll`), table slot, and `detail` slot
    (keeping Django 6.0 `{% partialdef detail inline %}` defined on the
    calling list template so `template.html#detail` resolves unchanged).
  - `sort_th.html` (`<c-sort-th>`): renders a sortable `<th scope="col">`
    with `class`, optional `aria-sort`, `<a href="...">`, and optional
    `<small>` unit.
- **Incremental template migration**:
  - Migrate split-view lists (`category_list.html`, `bulk_list.html`,
    `note_list.html`, `item_list.html`), flat lists (`batch_list.html`,
    `vessel_list.html`, `tasks/list.html`, `registry/list.html`,
    `planning/list.html`), and widgets (`history.html`, `item_page.html`,
    `overview.html`, `_stock.html`, `substance.html`, `inspector.html`,
    `item_forecast.html`, `parameters.html`).
- **Tests (`webapp/tests/test_lists_support.py`)**:
  - Add unit tests for `orgsyndb_web/lists.py`, `<c-split-layout>` hooks
    (`item-layout--split`, `category-table-scroll`), and `django-cotton` +
    Django 6.0 `{% partialdef %}` / `template.html#detail` lookup through the
    configured template backend.

## Why No Spec Changes

Every requirement under `openspec/specs/` stays true: all URLs, HTTP status
codes, response headers, cookies, i18n strings, print/screen CSS hooks
(`.widget`, `.item-layout`, `.item-layout--split`, `#category-table-scroll`,
`.item-table`, `#item-detail`, `data-refresh`, `data-sortable`, `aria-sort`),
and interactive behaviors remain unchanged. No existing test is edited. The
closest capabilities (`web-app`, `end-product-inventory`, `production-planning`,
`task-tracker`, `lab-registry`, `lab-overview`) govern rendered behavior and
semantics rather than template decomposition or internal Python list helpers.

## Impact

- Code touched: `webapp/pyproject.toml`, `webapp/uv.lock`,
  `webapp/orgsyndb_web/settings.py`, `webapp/orgsyndb_web/lists.py` (new),
  `webapp/orgsyndb_web/templates/cotton/*.html` (new),
  `webapp/inventory/views/{items,bulk,vessels}.py`, `webapp/tasks/views.py`,
  list and widget templates under
  `webapp/{inventory,tasks,registry,planning,overview}/templates/`, and
  `webapp/tests/test_lists_support.py` (new).
- Risks: `django-cotton`'s automatic template loader wrapping interacting with
  Django 6.0 `{% partialdef %}` / `#partial` lookups, whitespace or attribute
  differences breaking strict HTML assertions in existing tests, or losing
  page-specific hooks (`item-layout--split`, `category-table-scroll`).
  Verified via `test_lists_support.py` and across all existing list, widget,
  back-link, query-count, and shell suites unmodified.

## Verification

1. `webapp/tests/test_lists_support.py` passes, covering `orgsyndb_web/lists.py`,
   split-layout CSS/ID hooks, and `django-cotton` + Django 6.0 `{% partialdef %}`
   / `#detail` resolution through the configured template engine.
2. Root `python3 -m pytest tests/test_webapp_layout.py` passes.
3. All existing webapp list, widget, overview, planning, task, registry,
   back-link, query-count, and shell suites pass unmodified:
   `cd webapp && uv run pytest tests/test_shell.py tests/test_inventory_*.py tests/test_planning_*.py tests/test_task_list.py tests/test_registry_pages.py tests/test_overview.py tests/test_widgets_*.py tests/test_back_links.py tests/test_query_counts.py tests/test_lists_support.py`.
4. `uv run python manage.py makemigrations --check --dry-run` reports no
   migrations needed.
