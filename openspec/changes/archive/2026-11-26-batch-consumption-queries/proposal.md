## Why

The read paths of `/lab/inventory/end-products/`, `/lab/planning/`, `/lab/`,
`/lab/summary/`, and `/lab/inventory/items/<pk>/` execute per-item queries for
`EnteredConsumption`, `DeliveryLine`, and `Movement` reversals, rescan all
open vessels and tasks per article, and load all numbered articles on single-item
pages. On a baseline comparing 1 vs. 4 numbered articles, query counts grow by
+3/item on the item list, +6/item on planning, and +9/item on overview and
summary.

## What Changes

- `webapp/inventory/figures.py`: add `entered_by_item()`, extend
  `counted_lines()` with scoped `items` filtering, add `ConsumptionBatch`
  for preloaded consumption and delivery lines, and add `vessels_by_substance()`
  to eliminate O(N*V) vessel scans.
- `webapp/inventory/views.py`: preload `ConsumptionBatch` and grouped open
  vessels once in `item_list`; derive `compartments` and `boxes` from loaded
  items; scope `Plan` to a single article in `item_page` and reuse its
  computed `Consumption` in `consumption_section()`.
- `webapp/planning/plan.py`: support optional preloaded `ConsumptionBatch` and
  single-article scoping in `Plan`; compute each item's consumption once in
  `_forecast` / `_item`; index open vessels, stocked substances, and tasks by
  substance once per `Plan`. (`Plan.row()` keeps populating `Row.starts`
  unconditionally, since `test_planning_stock.py` reads `row.starts` even when
  `plan_synthesis` is false, and `self.sequences` / `self.stocked_substances`
  are cached once per `Plan`.)
- `webapp/overview/figures.py` and `webapp/overview/views.py`: load one
  `ConsumptionBatch` per request and share it across `delivered()`,
  `stock_parts()`, `summary()`, and `Plan`.
- `webapp/tests/`: add constant-query-count regression tests (1 vs. 4 articles)
  for `/lab/inventory/end-products/`, `/lab/planning/`, `/lab/`, `/lab/summary/`,
  and `/lab/inventory/items/<pk>/`.

## Why No Spec Changes

Every requirement under `openspec/specs/` stays true: rendered HTML, ordering,
calculations, URLs, status codes, and public interfaces are unchanged. The
closest capabilities are `end-product-inventory`, `production-planning`, and
`lab-overview`; all three specify observable figures, layout, and behavior,
none of which change when database reads are batched in constant query count.
Internal ORM query batching is not behavior a spec requirement should prescribe.

## Impact

- Code touched: `webapp/inventory/figures.py`, `webapp/inventory/views.py`,
  `webapp/planning/plan.py`, `webapp/overview/figures.py`,
  `webapp/overview/views.py`.
- Risks: mismatch between single-item and batched reversal filtering in
  `counted_lines()`, stale or unscoped data in single-article `Plan`, or a
  caller reading `Row.starts` when `plan_synthesis` is false. All are covered
  by existing tests plus new constant-query-count tests.

## Verification

1. All existing tests in `test_inventory_lists.py`, `test_inventory_pages.py`,
   `test_inventory_detail.py`, `test_overview.py`, and `test_planning_*.py`
   pass with no existing assertions modified.
2. New constant-query-count tests verify identical SQL query counts between
   1 and 4 numbered articles on `/lab/inventory/end-products/`,
   `/lab/planning/`, `/lab/`, `/lab/summary/`, and `/lab/inventory/items/<pk>/`.
3. CI workflows `Program` and `Lab application` pass on the pushed branch.
