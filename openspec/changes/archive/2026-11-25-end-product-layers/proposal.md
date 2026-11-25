## Why

End products exist in the lab in three forms: counted containers,
the bulk they are filled from, and the containers delivered. Today
only the containers have a list of their own; the bulk is scattered
over the vessel list and the item details, and the deliveries are a
section tab beside batches and vessels although only end products are
delivered. The owner approved, in the second screenshot series, an
Endprodukte section with the layers Gebinde, Bulk and Lieferungen;
this change builds it ahead of the Zwischenprodukte and
Handelschemikalien views.

## What Changes

- The item list, a new bulk list and the delivery list become the
  layers `Gebinde`, `Bulk` and `Lieferungen` of `Endprodukte`, each
  offering the three with their counts.
- New bulk list `/lab/inventory/end-products/bulk/`: every open vessel
  of a substance with an article, flasks and bought bottles included,
  with how many containers of each size it would fill; each of those
  alternatives leads to the item's filling form with the vessel
  chosen. Filters by text, location, source and flasks; table and
  details views.
- The delivery list gets the heading `Endprodukte` and a details view
  showing the selected note.
- The section tabs become `Endprodukte`, `Chargen` and `Alle Gefäße`;
  `Lieferungen` leaves the tabs for the Endprodukte layers.
- The filling form takes `?vessel=<id>`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: new requirements End product layers and
  Bulk list; Delivery list, Batch list (section tabs) and Inventory
  forms (filling form) change.

## Impact

- `webapp/inventory/` views, URLs, forms, templates, `lab.css`,
  `lab.js` (selection in the new lists), German translations; tests.
- The back link of a delivery note keeps its list's heading, which is
  now `Endprodukte`.
