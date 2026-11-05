## MODIFIED Requirements

### Requirement: Item page
`/lab/inventory/items/<id>/` SHALL show the article number and name as heading; the compound; the category, size and note; the quantity with its level; the means and coverage; the current year's consumption; a chart of the consumption of each quarter of the two complete years before the current one and of the current year, an inline `svg` with one bar per quarter titled with the quarter and its value and, when the item has a mean, a line at the mean per quarter, followed by a table of each quarter's entered value, deliveries and total; the movements in booking order, newest first, with date, booking time, kind, count, quantity after, the user's initials, the delivery note with its number and recipient, the note, and the mark `storniert` (`reversed`) on a reversed movement; the open lots of its article number with the number of containers they would fill; under `Prognose` (`Forecast`), the item's forecast, as `production-planning` states under Item forecast; and the change history. A signed-in user sees the links `Abgabe buchen` (`Book delivery`), to the new delivery note with the item in its first line, `Abfüllen` (`Fill`), `Bestand korrigieren` (`Correct count`), `Verbrauch nachtragen` (`Enter consumption`), `Bearbeiten` (`Edit`), and `Stornieren` (`Reverse`) beside each delivery and filling not yet reversed. An unknown id answers 404.

#### Scenario: Chart and ledger
- **WHEN** on 2026-11-04 a test client requests the page of an item with entered values for three quarters of 2025 and two deliveries in 2026
- **THEN** the `svg` has twelve bars, the table lists the same values, and the movements list the deliveries before the opening count

### Requirement: Bulk lot page
`/lab/inventory/bulk/<id>/` SHALL show the lot's article number, batch, amount, location, date and note, the mark `aufgebraucht` (`used up`) at zero, its movements in booking order, newest first, with date, booking time, kind, amount, amount after, the user's initials, note and, for a filling, the item filled, each task that belongs to the lot through its batch, linking to it, and its change history. A signed-in user sees the links `Korrigieren` (`Correct`) and `Bearbeiten` (`Edit`). An unknown id answers 404.

#### Scenario: Lot page after a filling
- **WHEN** a test client requests the page of a lot from which 5 containers of an item were filled
- **THEN** its newest movement is that filling, linking to the item

### Requirement: Inventory forms
For a signed-in user, the application SHALL offer:

- `/lab/inventory/end-products/new/`: a new item with its opening count, the article number with the compound `datalist`, and the category with a `datalist` of the categories in use;
- `/lab/inventory/items/<id>/edit/`: the item's name, category and note;
- `/lab/inventory/deliveries/new/`: a delivery note with ten rows for lines, rows left empty being ignored, and a check box `nachgetragen – Bestand bleibt unverändert` (`entered later – stock unchanged`) for a historical note; `?item=<id>` puts the item in the first row;
- `/lab/inventory/deliveries/<id>/reverse/`: marking a historical note reversed, with its note;
- `/lab/inventory/items/<id>/fill/` and `/correct/`: a movement;
- `/lab/inventory/items/<id>/movements/<movement id>/reverse/`: the reversal of a delivery or filling, with its note;
- `/lab/inventory/items/<id>/consumption/`: the entered value of a year and quarter, replacing an earlier one of that quarter, or removing it when left empty;
- `/lab/inventory/deliveries/<id>/edit/`: a note's number, recipient and note;
- `/lab/inventory/bulk/new/`: a new lot with its opening amount and the location with a `datalist` of the locations in use; `?article=<article number>`, `?batch=<batch>` and `?made_on=<date>` fill in those fields;
- `/lab/inventory/bulk/<id>/edit/`, for the batch, location, date and note, and `/correct/`.

Invalid input shows the form again with the errors beside their fields and saves nothing. A saved form leads, with a message naming the record, to the page of the delivery note for the forms of notes, and to the page of the item or lot for every other.

#### Scenario: New item
- **WHEN** user `KL` posts an item `CH-0012` named `Zimtsäure` of 10 µmol with an opening count of 12
- **THEN** the item exists with 12 containers, its only movement is the opening count by `KL`, and the response redirects to its page

#### Scenario: Entered consumption replaced
- **WHEN** a signed-in user enters 4 for the second quarter of 2026 and then 5 for the same quarter
- **THEN** the item has one entered value for that quarter, 5

#### Scenario: Fixed identity
- **WHEN** a signed-in user posts the edit form of an item with a different article number, size and unit
- **THEN** those fields are unchanged

#### Scenario: New lot from the query
- **WHEN** a signed-in user requests `/lab/inventory/bulk/new/?article=CH-0012&batch=B-2026-031&made_on=2026-10-30`
- **THEN** the form holds the article number `CH-0012`, the batch `B-2026-031` and the date 2026-10-30
