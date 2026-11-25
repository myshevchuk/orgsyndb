## Why

Self-made intermediates and commercial chemicals have no view of their
own: they appear only as rows of the flat vessel list, mixed with end
products and flasks, one row per vessel. A chemist asks "do we have it,
how much, where, is a bottle open?" of a substance, not of a vessel.
The owner approved, in the second screenshot series and its
brainstorm, the views `Zwischenprodukte` and `Handelschemikalien` with
one row per substance and the selected substance's vessels in a
table below it. This is the last of four changes that split the
Bestand by category; the frame, the opening date of bottles and the
Endprodukte layers are in place.

## What Changes

- The stock category of a vessel is written down once: `Endprodukte`
  when its substance has an article, else `Zwischenprodukte` for a
  made batch and `Handelschemikalien` for a bought one; a flask is
  categorised like any vessel.
- New list `/lab/inventory/intermediates/` and
  `/lab/inventory/chemicals/`: one row per substance with honest
  summaries of its vessels of that category (amount by unit, number
  of vessels with flasks or sealed ones, locations, tasks or suppliers,
  age or opening date, a mark for stock in the other category); filters
  that narrow the summaries; table and details views.
- The details view shows the selected substance's vessels in a table
  with their origin and actions; withdrawal, transfer and correction
  open in a dialog; a substance with a single vessel shows its newest
  movements.
- The section tabs gain `Zwischenprodukte` and `Handelschemikalien`.
- The vessel kind `Reagenz` becomes `Handelschemikalie`, with the
  value `commercial` in place of `reagent`.
- The new-batch form takes `?source=bought`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: new requirements Stock categories and Lists
  by substance; Batch list (section tabs), Vessels and Vessel list
  (kind name), Inventory forms (`?source=bought`) change.

## Impact

- `webapp/inventory/` models (kind), a pure module of summaries and
  ages, views, URLs, forms (dialogs for vessel forms), templates,
  `lab.css`, German translations; tests, among them the demo test that
  lists the vessel kinds and the tests of the section tabs.
- `README.md` names the vessel kind `Reagenz`; the doc stage updates it
  and describes the two lists.
- The vessel list's `kind=reagent` becomes `kind=commercial`; no
  alias is kept.
