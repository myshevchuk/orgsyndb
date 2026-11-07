## Why

The item list is wide and loose: twelve columns, a filter row inside
the table that staff find does not work, a legend under the table, and
locations and consumption history that take a trip to the item's page.
The owner's mockups of a denser list put the category in view, keep
the stock colours, move the filters above the table, and open the
location and the consumption statistics in popups beside the row.
Popups that sit beside their row need a little script, which the lab's
pages do not allow yet.

## What Changes

- The item list shows `Artikelnr.`, `Name`, `Kategorie`, `Gebinde`,
  `Bestand`, `Ø Jahr`, `Abgegeben` (this year's consumption, renamed
  from `lfd. Jahr`), `Reichweite`, `Lagerort` and `Bulk verfügbar`,
  with compact rows, units under the number columns' labels, and the
  optional columns `Fach`, `Box` and `Bemerkung`.
- `Lagerort` holds a button `Ort` that opens the item's compartment and
  box and the locations of its open bulk lots. The number under
  `Abgegeben` opens the consumption of the current year by quarter, the
  two years before by quarter, and the means.
- The list is ordered by category, then article number, then container
  by default, with a rule between categories. Ties by container order
  their sizes by amount, 100 mg before 1 g. Sizes of one article are no
  longer folded together.
- **BREAKING** The filter row goes, and with it the parameters
  `number`, `name` and `note`. Above the table sit the search, the
  category, a `Bestandsstatus` menu that replaces the legend, with each
  level's colour, meaning and count, and `Weitere Filter` with the
  container, the compartment and the box. The `Bestandsstatus` counts
  follow the other filters in force.
- `Spalten` shows and hides columns, `Zeilenhöhe` chooses compact or
  very compact rows, and `Verbrauch einfärben` switches the consumption
  heat on and off. The browser remembers these choices.
- The item list loads one script, `lab.js`. It places popups beside
  their buttons, submits a filter when its choice changes, and
  remembers the view choices. Without it the list still works: popups
  open in the window's centre and a `Filtern` button submits.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: the item list's columns, order, filters,
  popups and view choices; the heat's switch.
- `web-app`: the page shell allows the item list's one script.
- `lab-demo`: the item without an article number now sits within its
  category instead of last.

## Impact

- Changed: `inventory` views, templates and template tags,
  `Item.sort_key`, `lab.css`, a new `lab.js`, the German translations,
  and their tests; the shared test helper that reads a table's headers.
- Docs: `README.md`, on the item list.
- Not included: the category sidebar of the second mockup.
