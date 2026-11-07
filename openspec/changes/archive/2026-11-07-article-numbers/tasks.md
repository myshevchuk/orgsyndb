## 1. Tests

- [x] 1.1 Items: created without an article number, two of the same
  size, entered once through the edit form, refused when taken, fixed
  after; admin read-only once set
- [x] 1.2 Refusals: a delivery line and an entered value, zero
  included, of an item without an article number; the note form's
  choices; an admin change page loaded before the number was assigned
- [x] 1.3 Item list and page: order, links, search, heading, compound,
  actions, no new-lot link
- [x] 1.4 Datalist: unique field values, not keys, on the item and lot
  forms
- [x] 1.5 Planning: items without an article number in no article and
  matching no task
- [x] 1.6 Demo collection: `item_number` on exactly the six final
  products, not required; the test collection mirrors it; the beside
  scenarios and the Emacs new-compound scenario
- [x] 1.7 Lab demo: the position without an article number, its task's
  product and batch, the planning list on the seeding days

## 2. Implementation

- [x] 2.1 `Item.article_number` nullable, with a migration; display and
  ordering of items without one
- [x] 2.2 Bookings: create without a number, assign once, refuse
  delivery and entered consumption
- [x] 2.3 Forms, views, templates, admin and translations
- [x] 2.4 Planning: skip items without a number
- [x] 2.5 Demo collection, test collection, lab demo data and writer

## 3. Docs and archive

- [x] 3.1 `README.md`, `docs/SCHEMA*.md`, `docs/AUTHORING*`: the demo's
  compound link example and which compounds carry a number
- [x] 3.2 Review, then archive
