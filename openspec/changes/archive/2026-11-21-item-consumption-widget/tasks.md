## 1. Tests

- [x] 1.1 History: entering, replacing and removing a quarter's value
  each write a history record of `EnteredConsumption` naming the user;
  the migration gives each value stored before it a creation record
  with its `entered_by` and `entered_at`, and a later change of such a
  value shows its old count; the table diagram's expected history
  tables include the new one
- [x] 1.2 Item page: the history holds the consumption entries headed
  `Verbrauch Q3 2026` with their old and new counts, newest first,
  among the item's own; an item change between consumption entries,
  entries at the same moment, and a removed value; scenario "History
  of entered consumption"
- [x] 1.3 Item page links: `Ändern` and `Nachtragen` per quarter with
  `?year=&quarter=` and `data-dialog`, a stored zero linking `Ändern`;
  none for a quarter with a
  historical note's line, a quarter to come, an item without an
  article number, or a visitor; scenario "Changing a quarter's entered
  value"
- [x] 1.4 The form for a quarter: fixed to it, named as text, count
  the stored value or empty, the value it replaces named, also when
  shown again with errors; invalid or future `year` and `quarter`
  open the editable form with nothing named; scenario "The form for a
  quarter"
- [x] 1.5 The consumption section in the form, as a page and as the
  dialog's partial: the chart and the table of quarters with the item
  page's values; its links lead to the form for their quarter, with
  `hx-get` to the dialog's body in the partial and without in the page
- [x] 1.6 The item list's details keep their consumption table without
  links

## 2. Implementation

- [x] 2.1 `models.py`: history of `EnteredConsumption`; migrations for
  its table and the creation records
- [x] 2.2 `bookings.py`: attribute saves and removals; the test for a
  quarter that takes a value as a function of its own
- [x] 2.3 `history.py` and `history.html`: entries with a heading, the
  item's merged with its entered consumption's
- [x] 2.4 `views.py`: `consumption_section(item, today, links)`;
  `item_page`
  and `item_consumption` use it; the query of the form
- [x] 2.5 Templates: `consumption.html`; `item_page.html` renders it;
  the consumption form's own template with the section in its partial
- [x] 2.6 German messages for new strings
- [x] 2.7 `lab.js`: the dialog's body inert while its form is posted
  and the page refreshed
- [x] 2.8 `webapp/docs/database-schema.html` regenerated

## 3. Checks

- [x] 3.1 Area tests pass: `webapp/tests/test_inventory_*.py`,
  `test_schema_diagram.py`, `test_lab_script.py`
- [x] 3.2 In a browser: correct a value from the item page's table
  and from the dialog opened in the item list's details; switch
  quarters in the dialog, save, and click another quarter while the
  save is under way; the history shows the change
- [x] 3.3 On the test server, by the owner
