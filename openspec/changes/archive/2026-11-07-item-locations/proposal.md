## Why

All end products sit in one freezer, found by compartment (`Fach`) and
box (`Box`), and the Excel list carries both. The application records
neither, so whoever fills a request looks up the location elsewhere. A
request usually names several articles, and booking it means picking
each one again from a drop-down of every item. The owner wants the two
locations as columns, a request turned into one delivery note straight
from the list, and the note to say where each line is fetched from.

## What Changes

- Items get two optional locations, `Fach` (compartment) and `Box`,
  edited on the new-item and edit forms with suggestions of the values
  in use, and shown on the item page and in two item-list columns.
- A signed-in user ticks rows of the item list and chooses `Lieferschein
  mit Auswahl` (`Delivery note from selection`): the new delivery note
  opens with the ticked items in its first rows. Only items that can be
  delivered, those with an article number, can be ticked.
- The delivery note form names each item with its location, and the
  note's page lists `Fach` and `Box` beside every line, so a printed
  note serves as a pick list.
- The demo data gives every item a compartment and a box.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: the locations on items, the list's columns
  and selection, the delivery note form's rows and the note page's
  lines.
- `lab-demo`: locations on every demo item.

## Impact

- Changed: `inventory` models with a migration, forms, views,
  templates, admin and `lab.css`; the demo data set; the German
  translations; their tests.
- Docs: `README.md`, on the item list and booking deliveries.
- Not included: sorting by location, which the table change brings;
  locations of bulk lots, which keep their free-text `location`.
