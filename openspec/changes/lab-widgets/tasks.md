## 1. Tests

- [ ] 1.1 Sorting: the pure function of `lab.js` under Node — numbers
  with decimal comma and units, dates, German text, `–` and empty
  cells last in both directions, stable order, `data-sort` keys
- [ ] 1.2 History widget: item, batch, vessel, delivery note and task
  pages hold a collapsible `section.widget` with the history table, one
  row per changed field, `Angelegt` for a creation, newest first, and
  no `ul.lab-history`; existing tests that read `ul.lab-history` moved
  to the table
- [ ] 1.3 Item page: the figures strip, the widgets with their titles
  and counts, the movements table marked `data-sortable` in booking
  order without `aria-sort`, the forecast's figures each with its
  parameters on the line under it, and every figure the page showed
  before still present

## 2. Widget machinery

- [ ] 2.1 Widget classes in `site/assets/css/screen.css`, print rules
  in `print.css` (collapsible widgets print open)
- [ ] 2.2 Sorting in `lab.js`: the pure function, header activation,
  `aria-sort`, and keeping the sort and open state across a refresh
  after a dialog

## 3. History

- [ ] 3.1 `inventory/history.html` as a collapsible widget with the
  table

## 4. Item page

- [ ] 4.1 `inventory/item_page.html` as the chosen mockup: figures
  strip, two columns of widgets, `lab.css` grid
- [ ] 4.2 `planning/item_forecast.html` as key–value widgets; German
  catalogue updated
- [ ] 4.3 Help pages brought in line where they show or describe the
  item page or the history (doc writer)

## 5. Verification

- [ ] 5.1 Area tests, then both suites once; CI green on the branch
- [ ] 5.2 Screenshot of the item page beside the mockup; owner checks
  it on the test server
