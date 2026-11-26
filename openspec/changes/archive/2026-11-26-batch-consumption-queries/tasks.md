## 1. Batch loaders in inventory.figures

- [x] 1.1 Add `entered_by_item()`, scoped `items` support in `counted_lines()`, `ConsumptionBatch`, and `vessels_by_substance()` in `webapp/inventory/figures.py`

## 2. Inventory views

- [x] 2.1 Preload `ConsumptionBatch` and grouped open vessels in `item_list`, and derive `compartments` and `boxes` from loaded `items`
- [x] 2.2 Scope `Plan` to the item's article in `item_page` and reuse its computed `Consumption` in `consumption_section()`

## 3. Production planning

- [x] 3.1 Support optional preloaded `ConsumptionBatch` and single-article scoping in `Plan`, eliminating double `consumption()` calls in `_forecast` / `_item`
- [x] 3.2 Index vessels, stocked substances, and tasks by substance once per `Plan`

## 4. Overview

- [x] 4.1 Share one preloaded `ConsumptionBatch` across `overview/views.py` and `overview/figures.py` (`delivered`, `stock_parts`, `summary`, `Plan`)

## 5. Verification

- [x] 5.1 Add constant-query-count regression tests (1 vs. 4 articles) for `/lab/inventory/end-products/`, `/lab/planning/`, `/lab/`, `/lab/summary/`, and `/lab/inventory/items/<pk>/`
- [x] 5.2 Run area test suites locally and verify green CI on the pushed branch
