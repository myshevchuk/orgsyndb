## 1. Tests

- [x] 1.1 Order: category first with `category-start`, sizes by amount,
  the order line in both directions, `Lagerort` without a link
- [x] 1.2 Filters: search and category in the form, the `Weitere
  Filter` choices and count, `Zurücksetzen` only while filtering, the
  filter row and `number`, `name` and `note` gone
- [x] 1.3 Stock menu: entries, colours, counts under the other
  filters, links, `aria-current`, the button's text
- [x] 1.4 Popups: location with compartment, box and lots; statistics
  with years, quarters, sums, bars, the running quarter, the entered
  years; both inside their cells, opened by `popovertarget`
- [x] 1.5 Statistics rows as a pure function of `Consumption`
- [x] 1.6 View controls: `Spalten`, `Zeilenhöhe`, `Verbrauch
  einfärben`, `data-remember`, `col-<key>` on every cell, their
  `lab.css` rules
- [x] 1.7 Shell: one deferred `lab.js` on the item list, none
  elsewhere
- [x] 1.8 `OrgSynLab.place` under Node
- [x] 1.9 Existing tests moved to the new columns and the default order

## 2. Implementation

- [x] 2.1 `Item.sort_key` by container order; default sort `category`
- [x] 2.2 Views: rows with popups' data, faceted counts, order line,
  filters
- [x] 2.3 Template, `lab.css`, `lab.js`
- [x] 2.4 German translations

## 3. Docs and archive

- [x] 3.1 `README.md`: the item list
- [x] 3.2 Review, then archive
