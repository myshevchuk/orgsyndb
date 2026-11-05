## 0. Before implementation

- [x] 0.1 `task-tracker` is archived and merged into `develop`; rebase
  this branch onto it, and turn the navigation requirement into a
  MODIFIED delta of `web-app`'s page shell
- [x] 0.2 Settle the columns and the open questions in `design.md`:
  the owner's description governs

## 1. Tests

- [x] 1.1 Items: fields, units, identity of article, size and unit,
  fixed identity, compound through the article number, history
- [x] 1.2 Item movements: opening count, delivery and its refusal,
  concurrent deliveries, filling, correction with and without a note,
  reversals of deliveries and fillings, booking order
- [x] 1.3 Delivery notes: several lines, refusal of the whole note,
  historical notes and the quarter rule, reversal, numbers, list and
  page
- [x] 1.4 Consumption: entered values and delivery lines per quarter,
  reversed lines, complete past years from the first year with data,
  the current year, means, coverage, rounding half up, replacing an
  entered value
- [x] 1.5 Stock levels: thresholds, no consumption, classes and labels
- [x] 1.6 Bulk lots: base units and six places, movements, used-up
  lots, conversions by factor and by molar mass, the proposed amount,
  refusal above the lot or at zero, containers from bulk per lot
- [x] 1.7 Item list: columns, order, `sort=urgency`, filters, count,
  legend, redirect from `/lab/inventory/`; bulk and delivery lists
  and section tabs
- [x] 1.8 Item and lot pages: chart bars and table, ledgers, links,
  404
- [x] 1.9 Forms and permissions; admin read-only fields and
  deletion; navigation
- [x] 1.10 Level colours: contrast of 4.5:1 in both schemes

## 2. Implementation

- [x] 2.1 `webapp/inventory/`: models, migrations, history
- [x] 2.2 Movements and fillings in one transaction; conversions
- [x] 2.3 Consumption, means, coverage and levels
- [x] 2.4 Lists, pages, chart, forms, templates, translations,
  level tokens in `lab.css`
- [x] 2.5 Admin and navigation entry

## 3. Docs and archive

- [x] 3.1 `README.md`
- [x] 3.2 Review, then archive
