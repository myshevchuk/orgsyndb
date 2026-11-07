## 1. Tests

- [x] 1.1 Sorting: each column's order, `dir=desc`, empty values last in
  both directions, ties in the default order, unknown values, the
  header links and `aria-sort`
- [x] 1.2 Filters: the filter row's controls, their form and labels,
  the text and choice filters, the values kept, the reset link; `level`
  and `sort=urgency` no longer apply
- [x] 1.3 Heat: the fifths, ties, zero and no value, counted over the
  whole inventory; the legend's scale; contrast in both schemes
- [x] 1.4 Grouped sizes, the sticky box, `Ø Quartal` gone from the
  list's columns
- [x] 1.5 Existing tests that use `level`, `sort=urgency` or the list's
  columns

## 2. Implementation

- [x] 2.1 Sorting and filters in the item list's view
- [x] 2.2 The heat of each row's figures
- [x] 2.3 Template, legend, `lab.css` and translations
- [x] 2.4 `STATE.md`: heat by category and size

## 3. Docs and archive

- [x] 3.1 `README.md`: sorting, the filter row, the heat, grouped sizes,
  the sticky table
- [x] 3.2 In a browser, against the demo data: the header and first column
  stick while the list scrolls both ways, and a long list prints whole
- [x] 3.3 Review, then archive
