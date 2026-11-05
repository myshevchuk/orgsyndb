## Why

The end products the lab synthesizes are kept as aliquoted containers,
ready to deliver, and counted in an Excel file: one row per item, with
article number, name, category, container size and unit, the number of
containers left, a note, and the consumption of past quarters, from
which the file computes the mean per quarter and per year and colours
the count by how long it will last. What is not aliquoted yet, the bulk
of a synthesis, appears only as free text in the note, so nobody can
count on it. Moving the file into the web application keeps every
change of a count with its author, computes consumption from the
deliveries booked, and gives bulk a record of its own: amount, batch,
location, and the aliquots filled from it. The Excel import waits for a
later change; items are entered in the application.

## What Changes

- Items with the file's columns: article number, name, category,
  container size in `mg`, `µmol`, `g` or `mmol`, containers left, note.
  An item links to its compound when its article number is an
  identifier of the collection. Article number, size and unit are
  fixed once the item exists.
- Movements of an item's containers, each with date, person and note:
  deliveries out, fillings in, corrections after counting, the opening
  count, and reversals of a mistaken delivery or filling; each keeps
  the count after it, and none is ever edited or deleted.
- Delivery notes (`Lieferscheine`) with number, date, recipient and
  one line per item, booking all their deliveries at once; old notes
  can be entered later without changing the counts.
- Consumption per quarter: entered for the time before the
  application, added up from delivery notes afterwards; the mean per
  year over all complete past years, as the file computes it, a
  quarter of it per quarter, and the current year beside them; the
  coverage in quarters.
- Stock levels as the file colours them: out (red), below half a
  quarter's consumption (orange), below a quarter's (yellow), below
  half a year's (pale green), each with a label, not colour alone.
- Bulk lots of an article number: amount and unit, batch, location,
  date, note, with their own movements. Filling aliquots takes the
  amount from a lot in the same step, converting between mass and
  amount of substance with the compound's molar mass. Each item shows
  how many containers its bulk would still fill.
- `/lab/inventory/end-products/` lists the items with levels, means,
  this year's consumption, coverage and bulk, filters by category and level and sorts by
  urgency; bulk and delivery lists, item, lot and note pages with a
  consumption chart and ledgers, and forms for every booking.
- `Bestand` (`Inventory`) joins the application's navigation, before
  `Aufgaben`.

## Capabilities

### New Capabilities

- `end-product-inventory`: items, movements, delivery notes,
  consumption, stock levels, bulk lots, their lists, pages and forms.

### Modified Capabilities

- `web-app`: the page shell's navigation lists `Bestand` before
  `Aufgaben`, and names for each view the path its pages lie under.

## Impact

- New: `webapp/inventory/` with its migrations and templates; its
  tests in `webapp/tests/`.
- Docs: `README.md` names the inventory view.
- Not included: Excel import or export, the QC file, the catalogue,
  intermediates, commercial reagents, a stock box on compound pages,
  priorities and replenishment (`production-planning`), removing
  `stock` from collections' compound declarations.
