## Why

`webapp/inventory/views.py` has grown to over 2,000 lines covering seven
distinct inventory surfaces (items, categories, bulk, delivery notes,
batches, vessels, and shared helpers), with repeated master-detail selection
lookups, HTMX detail-or-redirect boilerplate, oldest-first vessel sort keys,
and high-complexity category filtering/response functions. Splitting it into
a cohesive `webapp/inventory/views/` package and adding custom `QuerySet`
helpers in `inventory/models.py` prepares the codebase for upcoming HTMX list
enhancements without changing any external behavior.

## What Changes

- `webapp/inventory/models.py`: add `ItemQuerySet` (`.with_substance()`,
  `.numbered()`), `VesselQuerySet` (`.open()`, `.with_substance()`), and
  `MovementQuerySet` (`.reversed_deliveries()`), preserving `Article`'s
  `LockedQuerySet` untouched.
- `webapp/inventory/figures.py`: adopt the new `Movement` and `Vessel`
  QuerySet helpers where applicable.
- Replace `webapp/inventory/views.py` with the `webapp/inventory/views/`
  package:
  - `common.py`: shared paths, cookies, tabs/layers, vessel queries, unified
    `oldest_vessel_order()`, `pick_selected()`, `htmx_detail_or_redirect()`,
    dialog/form helpers, and URL/datalist helpers.
  - `items.py`: item list, detail, page, consumption section, and item forms.
  - `categories.py`: intermediate and commercial chemical lists/details,
    split via per-category `CategoryConfig` and predicate helpers.
  - `bulk.py`: bulk list and detail.
  - `notes.py`: delivery note list, detail, page, and forms.
  - `batches.py`: batch list, page, and forms.
  - `vessels.py`: vessel list, page, ledger, and forms.
  - `__init__.py`: re-export every URL entry point so `inventory/urls.py`
    stays unchanged.

## Why No Spec Changes

Every requirement under `openspec/specs/` stays true: URLs, HTTP status codes,
rendered HTML, headers, cookies, sorting, filtering, and database schema are
unchanged. The closest capability is `end-product-inventory`, which governs
user-visible pages and workflows rather than internal Python module layout or
custom Django `QuerySet` methods.

## Impact

- Code touched: `webapp/inventory/models.py`, `webapp/inventory/figures.py`,
  `webapp/inventory/views.py` (deleted) -> `webapp/inventory/views/*.py`.
- Risks: missed re-export in `inventory/views/__init__.py`, unintended
  migration diff from custom managers, or subtle divergence in refactored
  category predicates or HTMX detail redirects. Verified by
  `makemigrations --check`, all `test_inventory_*.py` tests, `test_shell.py`,
  `test_query_counts.py`, and CI.

## Verification

1. `uv run python manage.py makemigrations --check --dry-run` reports no
   migrations needed.
2. All existing tests in `webapp/tests/test_inventory_*.py`,
   `test_query_counts.py`, `test_shell.py`, and `test_widgets_item_page.py`
   pass with no test edited.
3. CI workflows `Program` and `Lab application` pass on the pushed branch.
