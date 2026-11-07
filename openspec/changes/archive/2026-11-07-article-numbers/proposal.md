## Why

An article number (`Artikelnr.`) in the lab is the company-wide number
that appears on delivery notes, and only end products have one: it is
assigned when a product is first delivered. The application treats it
as the identity of every item, required from the moment an item is
created, and the demo collection gives one to every compound, purchased
reagents and intermediates included. A position that has entered stock
but was never delivered therefore cannot be recorded as it is, and the
demo conflates the delivery-note number with a numbering of the
collection's own. The owner wants the two kept apart now; a numbering
scheme of the database's own is a separate question, deferred.

## What Changes

- An item's article number becomes optional: an item without one has
  never been delivered. It is entered once, in the item's edit form or
  the admin, and is fixed from then on.
- An item without an article number shows its container and name, has
  no compound and no bulk lots, belongs to no planning article, matches
  no task, and cannot be delivered or have consumption entered; its
  page offers `Artikelnr. eintragen` instead of booking a delivery.
- The item and lot forms suggest, for the article number, the numbers
  the collection records in its compounds' unique fields, and no longer
  the compound keys.
- The item list orders items without an article number last, by name;
  their names link to their pages.
- The demo collection gives `item_number` only to the six final
  products the lab demo delivers; the field is no longer required.
- The lab demo's never-delivered position, 1-phenylethanol, has no
  article number and no bulk lot, and its task names the compound key.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: an optional article number, entered once;
  what an item without one shows and refuses; the article number's
  `datalist`; the list's order.
- `production-planning`: items without an article number belong to no
  article and match no task.
- `sample-procedures`: which demo compounds set `item_number`, which is
  no longer required.
- `lab-demo`: the never-delivered position without an article number.
- `compound-fields`: two scenarios restated for the demo's numbers.
- `emacs-mode`: the new-compound scenario without an `item_number`
  prompt.

## Impact

- Changed: `inventory` models with a migration, bookings, forms, views,
  templates and admin; `planning.plan`; the demo data set and its
  writer; the German translations; `examples/demo/orgsyndb.toml` and
  its compounds, mirrored in `tests/fixtures/collection/`; their tests
  in `webapp/tests/`, `tests/` and `tests/el/`.
- Docs: `README.md`, `docs/SCHEMA*.md` and `docs/AUTHORING*`, which
  cite a demo compound link with a number it no longer has.
- Not included: a numbering of the database's own for synthesized
  compounds.
