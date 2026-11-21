## Why

An entered quarterly value that is wrong, such as one with a typed
extra digit, can be corrected today: entering the same quarter again
replaces it, and an empty count removes it. Nothing in the interface
says so. `Verbrauch nachtragen` opens an empty form that never shows
the stored value, and the item page's table of quarters offers no way
from a wrong value to its correction, so the owner found no way to
correct one. A correction also leaves no trace: the value, who entered
it and when are overwritten, although web-app "Change history" asks
every model holding lab records to keep a history, and entered
consumption is the one that keeps none.

The owner decided on 2026-11-21: links per quarter on the item page
only, the history of entered values, and the item's consumption, its
chart and table, as one piece the item page and the consumption form
share, so that the form opened from the item list's details shows the
same table it corrects.

## What Changes

- Entered consumption keeps a change history. Values entered before
  the change get a creation record from their `entered_by` and
  `entered_at`.
- The item page's table of quarters links each quarter to the
  consumption form for it, `Ändern` where it has an entered value and
  `Nachtragen` where it has none, opening in a dialog; there is no link
  for an item without an article number or beside a quarter that holds
  a historical note's lines, since such quarters refuse a value.
- The item page's history includes the entered consumption's entries,
  changes and removals, headed `Verbrauch Q<n> <year>`.
- The consumption form takes `?year=&quarter=`, fills in that quarter's
  stored count and names the value a save replaces, and shows the
  item's chart and table of quarters beside its fields, whose links
  choose a quarter in the form.
- The item list's details keep their own compact consumption table,
  without links.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: "Consumption" (the history), "Item page"
  (the links and the history) and "Inventory forms" (the form for a
  quarter and the consumption beside it).

## Impact

- `webapp/inventory/models.py` and a migration: the history of
  `EnteredConsumption`, and creation records for the values already
  stored.
- `webapp/inventory/bookings.py`: `enter_consumption` records the user
  in the history, its removal included.
- `webapp/inventory/history.py`, `views.py`: the item's history with
  that of its entered consumption; one source of the consumption
  section for the item page and the form; the form's query.
- `webapp/inventory/templates/inventory/`: the consumption section as
  a template of its own, used by `item_page.html` and the consumption
  form; `form.html` or a template of the consumption form's own.
- German messages for new strings.
