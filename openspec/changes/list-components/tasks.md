# Tasks: Reusable list and widget components

## 1. Setup & Compatibility Pre-Check
- [x] 1.1 Add `django-cotton>=2.9` to `webapp/pyproject.toml` and `webapp/uv.lock`, and register `"django_cotton"` in `INSTALLED_APPS` in `webapp/orgsyndb_web/settings.py`.
- [x] 1.2 Create `webapp/orgsyndb_web/lists.py` (`clean_choice`, `sort_rows`) and adopt it in `inventory/views/{items,bulk,vessels}.py` and `tasks/views.py`.
- [x] 1.3 Create reusable Cotton components under `webapp/orgsyndb_web/templates/cotton/`: `widget.html`, `list_heading.html`, `filter_bar.html`, `filter_search.html`, `filter_select.html`, `filter_check.html`, `split_layout.html`, `sort_th.html`.
- [x] 1.4 Add `webapp/tests/test_lists_support.py` covering `orgsyndb_web/lists.py`, `<c-split-layout>` (`item-layout--split` and `category-table-scroll`), and `django-cotton` + Django 6.0 `{% partialdef detail inline %}` / `template.html#detail` lookup through the configured template backend.

## 2. Migrate Split-View Lists
- [x] 2.1 Migrate `webapp/inventory/templates/inventory/category_list.html` to Cotton components (preserving `item-layout--split` and `id="category-table-scroll"`) and verify `test_inventory_categories.py`.
- [x] 2.2 Migrate `webapp/inventory/templates/inventory/bulk_list.html`, `note_list.html`, and `item_list.html` to Cotton components and verify `test_inventory_*.py`.

## 3. Migrate Flat Lists & Widgets
- [x] 3.1 Migrate `batch_list.html`, `vessel_list.html`, `tasks/list.html`, `registry/list.html`, and `planning/list.html` to Cotton components.
- [x] 3.2 Migrate widget templates (`inventory/history.html`, `inventory/item_page.html`, `overview/overview.html`, `overview/_stock.html`, `registry/substance.html`, `planning/inspector.html`, `planning/item_forecast.html`, `planning/parameters.html`) to `<c-widget>`.

## 4. Verification
- [x] 4.1 Run `python3 -m pytest tests/test_webapp_layout.py`, `uv run python manage.py makemigrations --check --dry-run`, and the webapp area test suites (`test_shell.py`, `test_inventory_*.py`, `test_planning_*.py`, `test_task_list.py`, `test_registry_pages.py`, `test_overview.py`, `test_widgets_*.py`, `test_back_links.py`, `test_query_counts.py`, `test_lists_support.py`) serially until green with zero edits to existing tests.
