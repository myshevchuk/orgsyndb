## 1. Tests

- [x] 1.1 Stock by batch: shares after opening, filling, delivery,
  assignment, correction and both reversals; the quantity equals the
  sum of the shares after each; refusals change nothing; concurrent
  deliveries of one batch; overlap tests with two connections of a
  delivery and a filling each against a correction
- [x] 1.2 Delivery notes: lines with a batch, current and historical;
  one item in two batches; a batch twice, a missing batch and a batch
  of another substance refused; reversed and partly reversed notes
  leave assignments out; one of two batch lines of an item reversed
  keeps the other in consumption and on the note page; a note of two
  batch lines counts once in the forecast's rhythm
- [x] 1.3 Forms: the new-item batch, the delivery rows' batch choice
  with its `data-substance` groups, the correction's shares; the
  narrowing function of `lab.js` under Node
- [x] 1.4 Pages: the item page's containers by batch and ledger batch
  column; the note page's and the delivery list's batch; the batch
  page's items and deliveries; the admin's shares and batch deletion
- [x] 1.5 Demo and diagram: the demo inventory scenarios; the diagram
  boxes and movement keys; `demo_data --replace` over a seeded
  database
- [x] 1.6 Existing tests that book notes, corrections or opening
  counts brought to the new signatures

## 2. Implementation

- [x] 2.1 `BatchStock`, `Movement.batch`, `DeliveryLine.batch`, the
  `assignment` kind; a schema-only migration
- [x] 2.2 Bookings: one share helper; `create_item`, `fill`,
  `book_note`, `correct`, `reverse` keep shares and quantity together,
  locking tasks, items and vessels in that order before reading
- [x] 2.3 Readers of lines: `counted_lines()`, the note page, the
  forecast's rhythm
- [x] 2.4 Forms, views and templates: new item, delivery note, correction,
  item page, note page, delivery list, batch page
- [x] 2.5 `lab.js`: narrowing a row's or the new-item form's batch
  choice to the chosen substance
- [x] 2.6 Admin: shares read-only on the item, batch deletion rule
- [x] 2.7 Demo data and seeding, the reset order; schema diagram grid and regenerated
  `webapp/docs/database-schema.html`
- [x] 2.8 German catalogue

## 3. Documentation

- [x] 3.1 `README.md`: overview, inventory sections, demo

## 4. Verification

- [ ] 4.1 Both suites pass on CI
- [x] 4.2 On the test server after `demo_data --replace`: an item page's
  containers by batch; a delivery of unknown containers booking an
  assignment; its reversal; a correction of one share; the batch page's
  items and deliveries; a row's batch choice narrowed to its item

## 5. Review and archive

- [x] 5.1 Codex reviewer
- [x] 5.2 Archive and squash-merge into `develop`
