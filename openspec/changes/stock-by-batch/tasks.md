## 1. Tests

- [ ] 1.1 Stock by batch: shares after opening, filling, delivery,
  assignment, correction and both reversals; the quantity equals the
  sum of the shares after each; refusals change nothing; concurrent
  deliveries of one batch
- [ ] 1.2 Delivery notes: lines with a batch, current and historical;
  one item in two batches; a batch twice, a missing batch and a batch
  of another substance refused; reversed and partly reversed notes
  leave assignments out
- [ ] 1.3 Forms: the new-item batch, the delivery rows' batch choice,
  the correction's shares
- [ ] 1.4 Pages: the item page's containers by batch and ledger batch
  column; the note page's and the delivery list's batch; the batch
  page's items and deliveries; the admin's shares and batch deletion
- [ ] 1.5 Demo and diagram: the demo inventory scenarios; the diagram
  boxes and movement keys
- [ ] 1.6 Existing tests that book notes, corrections or opening
  counts brought to the new signatures

## 2. Implementation

- [ ] 2.1 `BatchStock`, `Movement.batch`, `DeliveryLine.batch`, the
  `assignment` kind; a schema-only migration
- [ ] 2.2 Bookings: one share helper; `create_item`, `fill`,
  `book_note`, `correct`, `reverse` keep shares and quantity together
- [ ] 2.3 Forms, views and templates: new item, delivery note, correction,
  item page, note page, delivery list, batch page
- [ ] 2.4 Admin: shares read-only on the item, batch deletion rule
- [ ] 2.5 Demo data and seeding; schema diagram grid and regenerated
  `webapp/docs/database-schema.html`
- [ ] 2.6 German catalogue

## 3. Documentation

- [ ] 3.1 `README.md` inventory section, `docs/SCHEMA.md`,
  `docs/SCHEMA.de.md`, `docs/GLOSSARY.de.md`

## 4. Verification

- [ ] 4.1 Both suites pass on CI
- [ ] 4.2 On the test server after `demo_data --replace`: an item page's
  containers by batch; a delivery of unknown containers booking an
  assignment; its reversal; a correction of one share; the batch page's
  items and deliveries

## 5. Review and archive

- [ ] 5.1 Codex reviewer
- [ ] 5.2 Archive and squash-merge into `develop`
