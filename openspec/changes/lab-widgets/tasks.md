## 1. Tests

- [ ] 1.1 Sorting: `sortOrder` of `lab.js` under Node — signs and
  decimal commas, dates with and without times, German text after
  numbers and dates, `–` and empty keys last in both directions,
  stable order
- [ ] 1.2 History widget: the item, batch, vessel, delivery note and
  task pages hold one closed `details.widget` titled `Änderungen` with
  the history table, one row per changed field, `Angelegt` for a
  creation, a removed step's empty change cell, newest first
- [ ] 1.3 Item page: the figures strip with its marks and `–` for a
  missing figure; the widgets with their titles; the movements table
  marked `data-sortable` with an `id`, in booking order without
  `aria-sort`, its amount and date cells with `data-sort`; the
  forecast widget holding every figure and parameter it held, the
  delivery rhythm included; the note and the `Neue Charge` link kept
- [ ] 1.4 Existing tests moved to the new markup: `ul.lab-history`
  (`test_inventory_locations.py`, `test_inventory_states.py`,
  `test_inventory_consumption_widget.py`), `dl.metadata` on the item
  page (`test_inventory_locations.py`, `test_inventory_states.py`),
  the `Prognose` section helper (`planning_support.py`,
  `test_planning_item.py`), the first table taken as the quarters
  table (`test_inventory_consumption_widget.py`), and `ledger()` and
  `vessel_ledger()` in `inventory_support.py` scoped to the movements
  table

## 2. Widget machinery

- [ ] 2.1 Widget classes in `site/assets/css/screen.css`
- [ ] 2.2 `sortOrder` and header activation in `lab.js`, `aria-sort`
- [ ] 2.3 `refreshPage` carries open state and sort by `id`
- [ ] 2.4 `beforeprint`/`afterprint` open and close collapsible
  widgets

## 3. History

- [ ] 3.1 `inventory/history.html` as the history widget; the task
  page includes it in place of its inline list
- [ ] 3.2 German catalogue entries for the new labels

## 4. Item page

- [ ] 4.1 `inventory/item_page.html` as the chosen mockup: figures
  strip, two columns of widgets, `lab.css` grid
- [ ] 4.2 `planning/item_forecast.html` as the forecast widget; German
  catalogue updated
- [ ] 4.3 Help pages brought in line where they show or describe the
  item page or the history

## 5. Verification

- [ ] 5.1 Area tests, then both suites once; CI green on the branch
- [ ] 5.2 Screenshot of the item page beside the mockup; a dialog save
  on the item page keeps the history open and the movements sorted;
  the owner checks it on the test server
