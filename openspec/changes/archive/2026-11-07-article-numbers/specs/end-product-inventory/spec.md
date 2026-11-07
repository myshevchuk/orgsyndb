## MODIFIED Requirements

### Requirement: Items
The `inventory` package SHALL keep items, each with a change history:

- `inventory`, `end-products` for every item this capability creates;
- `article_number`, the number the article's delivery notes carry, at most 30 characters, or none: an item has none until it is first delivered;
- `name`, required, at most 200 characters;
- `category`, optional, at most 100 characters;
- `size`, a decimal greater than zero with up to three places, and `unit`, one of `mg`, `umol` (shown `µmol`), `g` and `mmol`;
- `quantity`, the whole number of containers left, at least zero, changed only by movements;
- `note`, optional text.

No two items of an inventory share article number, size and unit; items without an article number are not compared. The size and unit are fixed once the item is created, in the views and the admin alike. An item without an article number may be given one once, which is refused when another item of the inventory has that number, size and unit; from then on the article number is fixed. An item's compound is `compound_for(article_number)`, shown through the compound links, so every size of an article has the same compound and molar mass; an item without an article number has no compound and no lots, cannot be delivered, and cannot have consumption entered. An item shows as its article number, container and name, or as its container and name when it has no article number.

#### Scenario: Compound through the article number
- **WHEN** the index is the demo collection's and an item has the article number `CH-0012`
- **THEN** its compound is `cinnamic-acid`, and its name links to `/compounds/cinnamic-acid/` wherever the compound shows

#### Scenario: One article in two sizes
- **WHEN** a signed-in user creates an item `CH-0012` of 10 µmol and another of 50 µmol, then a third of 10 µmol
- **THEN** the first two are saved and the third is refused with an error at the size

#### Scenario: Positions without an article number
- **WHEN** a signed-in user creates two items `Neuverbindung 9` of 10 mg without an article number
- **THEN** both are saved, each without a compound

#### Scenario: Article number entered once
- **WHEN** a signed-in user gives an item without an article number the number `CH-0021` in its edit form, and then posts its edit form with the number `CH-0022`
- **THEN** the item has the article number `CH-0021`, its history records the change, and the second post leaves it unchanged

#### Scenario: Article number taken
- **WHEN** an item `CH-0012` of 10 µmol exists and a signed-in user gives `CH-0012` to an item of 10 µmol without an article number
- **THEN** the form shows an error at the article number and the item keeps none

### Requirement: Delivery notes
The `inventory` package SHALL keep delivery notes (`Lieferscheine`), each with a change history: `number`, optional, at most 30 characters, unique among notes when given; `date`, never after today; `recipient`, optional, at most 100 characters; `note`; `historical`; `reversed` and `reversal_note`, the flag of a reversed historical note and the note it was reversed with; `created_by` and `created_at`; and one or more lines, each an item of the inventory `end-products` with an article number and a `count` above zero, no item twice in one note. A line of an item without an article number is refused, current or historical. A note shows as its number, or as `#<id>` when it has none.

A current note, `historical` off, books one `delivery` movement per line, dated as the note, all in one transaction: when one line's count exceeds its item's quantity, the whole note is refused and nothing changes. A historical note, `historical` on, records deliveries made before they could be booked, such as those of old paper delivery notes: its lines change no quantity. A historical note is refused when one of its lines' items has an entered consumption value for the quarter of the note's date, and an entered value is refused for a quarter in which the item has lines of a historical note that is not reversed. A signed-in user may mark a historical note reversed, with a required note; a current note's lines are reversed one by one through their movements, and the note shows as reversed when all its lines are, and as partly reversed when some are. A note's date, kind and lines are fixed once it is created, its number, recipient and note may be edited, and no note is deleted, in the views or the admin.

#### Scenario: Note with several lines
- **WHEN** a signed-in user books a current note with 2 containers of one item holding 5 and 3 of another holding 3
- **THEN** both items are reduced, to 3 and 0, and the note lists both lines

#### Scenario: One line too many refuses the note
- **WHEN** a signed-in user books a current note with 2 containers of an item holding 5 and 4 of an item holding 3
- **THEN** the form shows an error at the second line, no note exists, and both items keep their quantities

#### Scenario: Historical note
- **WHEN** a signed-in user enters a historical note dated 2025-03-12 with 4 containers of an item holding 5 that has no entered value for the first quarter of 2025
- **THEN** the item still has 5, and its consumption in the first quarter of 2025 is 4

#### Scenario: Historical note in a quarter with an entered value
- **WHEN** an item has the entered value 6 for the first quarter of 2025 and a signed-in user enters a historical note dated 2025-03-12 with a line of that item
- **THEN** the form shows an error at that line and nothing is saved

#### Scenario: First delivery needs the article number
- **WHEN** an item without an article number holds 5 containers and a signed-in user posts a current note with a line of 2 of it
- **THEN** the form shows an error at that line, no note exists and the item keeps 5

### Requirement: Consumption
An item SHALL keep entered consumption per quarter, a whole number of containers of at least zero for a year and a quarter 1 to 4, at most one per quarter; entering a value replaces the quarter's earlier one, and entering none removes it. Entering a value for an item without an article number is refused, zero included. A quarter's consumption is its entered value, zero when there is none, plus the counts of the item's lines, in notes current or historical, dated in it, leaving out reversed movements and reversed historical notes. Quarters and years follow the calendar in `Europe/Berlin`.

The mean per year is the sum of the consumption of the complete calendar years before the current one, from the year of the item's first entered value, zero included, or delivery line that counts as consumption, divided by the number of those years; with none, there is no mean. The mean per quarter is a quarter of the mean per year. The current year's consumption is that of the current year so far, shown beside the mean for comparison. The coverage is the quantity divided by the mean per quarter, in quarters, and has no value without a mean above zero. Means and coverage show to one decimal place, rounded half up; levels compare the unrounded values.

#### Scenario: Means and coverage
- **WHEN** on 2026-11-04 an item with 3 containers has the entered value 4 for each quarter of 2024, 5 for each quarter of 2025 and 10 for the first quarter of 2026, and a delivery of 3 dated 2026-10-15
- **THEN** its mean per year is 18, its mean per quarter 4,5, its current year's consumption 13, its coverage 0,7 quarters, and its level low

#### Scenario: Years counted
- **WHEN** on 2026-11-04 one item has the entered value 0 for the third quarter of 2024 and 8 for each quarter of 2025, and another has entered values only in 2026
- **THEN** the first item's mean per year is 16 and the second has no mean and no level unless it is out

#### Scenario: A reversed note does not start the history
- **WHEN** on 2026-11-04 an item has the entered value 8 for each quarter of 2025 and a historical note dated 2024-05-02, which is then reversed
- **THEN** its mean per year is 32

#### Scenario: Entered value removed for old notes
- **WHEN** an item has the entered value 6 for the first quarter of 2025, a signed-in user removes it, and then enters a historical note dated 2025-03-12 with 4 of that item
- **THEN** the note is saved and the quarter's consumption is 4

#### Scenario: No consumption without an article number
- **WHEN** a signed-in user enters 3, and then 0, for the second quarter of 2026 on an item without an article number
- **THEN** the form shows an error each time and the item has no entered value

### Requirement: Item list
`/lab/inventory/end-products/` SHALL list the items of the inventory `end-products` in a table with the columns `Artikelnr.`, `Name`, `Kategorie`, `Gebinde`, `Bestand`, `Ø Quartal`, `Ø Jahr`, `lfd. Jahr`, `Reichweite`, `Bulk` and `Bemerkung` (`Article no.`, `Name`, `Category`, `Container`, `Stock`, `Mean per quarter`, `Mean per year`, `This year`, `Coverage`, `Bulk`, `Note`): the article number linking to the item's page; the name, linking to the compound when there is one, and to the item's page when the item has no article number; the category; the size with its unit; the quantity with its level; the means; the current year's consumption; the coverage; the bulk; and the note. Rows are ordered by article number, items without one after the others and by name, then unit, then size; with `sort=urgency`, by level, out first and items without a level last, then by coverage, smallest first and items without one last, then as without `sort`. GET parameters filter the list and keep their values in the form above it: `category`; `level`, one of `watch`, `low`, `critical` and `out`, listing the items at that level or a more urgent one; and `q`, text found regardless of case in the article number, name, category, note or the name of the item's compound. A line above the table counts the items listed, and a legend below it names the four levels with their thresholds. A signed-in user sees a link `Neuer Artikel` (`New item`). `/lab/inventory/` redirects to this list.

#### Scenario: Urgent items first
- **WHEN** the database holds items at the levels watch, none, out and low, and a test client requests the list with `sort=urgency`
- **THEN** the rows show out, low, watch and then the item without a level

#### Scenario: Level filter
- **WHEN** a test client requests the list with `level=low`
- **THEN** it lists exactly the items at the levels low, critical and out

#### Scenario: Items without an article number last
- **WHEN** the database holds items `CH-0012`, `Neuverbindung 9` without an article number, `CH-0001` and `Brücke 3` without an article number, and a test client requests the list
- **THEN** the rows show `CH-0001`, `CH-0012`, `Brücke 3` and `Neuverbindung 9`, and the names of the last two link to their items' pages

### Requirement: Item page
`/lab/inventory/items/<id>/` SHALL show the article number and name as heading, or the name alone for an item without an article number; the compound, or `–` for an item without an article number; the category, size and note; the quantity with its level; the means and coverage; the current year's consumption; a chart of the consumption of each quarter of the two complete years before the current one and of the current year, an inline `svg` with one bar per quarter titled with the quarter and its value and, when the item has a mean, a line at the mean per quarter, followed by a table of each quarter's entered value, deliveries and total; the movements in booking order, newest first, with date, booking time, kind, count, quantity after, the user's initials, the delivery note with its number and recipient, the note, and the mark `storniert` (`reversed`) on a reversed movement; the open lots of its article number with the number of containers they would fill; under `Prognose` (`Forecast`), the item's forecast, as `production-planning` states under Item forecast; and the change history. A signed-in user sees the links `Abgabe buchen` (`Book delivery`), to the new delivery note with the item in its first line, `Abfüllen` (`Fill`), `Bestand korrigieren` (`Correct count`), `Verbrauch nachtragen` (`Enter consumption`), `Bearbeiten` (`Edit`), and `Stornieren` (`Reverse`) beside each delivery and filling not yet reversed; for an item without an article number, `Artikelnr. eintragen` (`Enter article number`), to its edit form, takes the place of `Abgabe buchen`, and `Verbrauch nachtragen` and every link to a new bulk lot are left out. An unknown id answers 404.

#### Scenario: Chart and ledger
- **WHEN** on 2026-11-04 a test client requests the page of an item with entered values for three quarters of 2025 and two deliveries in 2026
- **THEN** the `svg` has twelve bars, the table lists the same values, and the movements list the deliveries before the opening count

#### Scenario: Page of a position without an article number
- **WHEN** a signed-in user requests the page of an item `Neuverbindung 9` of 10 mg without an article number
- **THEN** its heading is `Neuverbindung 9`, its compound shows `–`, and it links `Artikelnr. eintragen` to its edit form and has neither `Abgabe buchen`, `Verbrauch nachtragen` nor a link to `/lab/inventory/bulk/new/`

### Requirement: Inventory forms
For a signed-in user, the application SHALL offer:

- `/lab/inventory/end-products/new/`: a new item with its opening count, the article number, optional, with the article numbers' `datalist`, and the category with a `datalist` of the categories in use;
- `/lab/inventory/items/<id>/edit/`: the item's name, category and note, and its article number with the article numbers' `datalist` while it has none;
- `/lab/inventory/deliveries/new/`: a delivery note with ten rows for lines, each offering the items with an article number, rows left empty being ignored, and a check box `nachgetragen – Bestand bleibt unverändert` (`entered later – stock unchanged`) for a historical note; `?item=<id>` puts the item in the first row;
- `/lab/inventory/deliveries/<id>/reverse/`: marking a historical note reversed, with its note;
- `/lab/inventory/items/<id>/fill/` and `/correct/`: a movement;
- `/lab/inventory/items/<id>/movements/<movement id>/reverse/`: the reversal of a delivery or filling, with its note;
- `/lab/inventory/items/<id>/consumption/`: the entered value of a year and quarter, replacing an earlier one of that quarter, or removing it when left empty;
- `/lab/inventory/deliveries/<id>/edit/`: a note's number, recipient and note;
- `/lab/inventory/bulk/new/`: a new lot with its opening amount, the article number with the article numbers' `datalist`, and the location with a `datalist` of the locations in use; `?article=<article number>`, `?batch=<batch>` and `?made_on=<date>` fill in those fields;
- `/lab/inventory/bulk/<id>/edit/`, for the batch, location, date and note, and `/correct/`.

The article numbers' `datalist` offers each value of a unique text field of each compound of the index, labelled with the compound's name, and no compound key. An empty article number is none. Invalid input shows the form again with the errors beside their fields and saves nothing. A saved form leads, with a message naming the record, to the page of the delivery note for the forms of notes, and to the page of the item or lot for every other.

#### Scenario: New item
- **WHEN** user `KL` posts an item `CH-0012` named `Zimtsäure` of 10 µmol with an opening count of 12
- **THEN** the item exists with 12 containers, its only movement is the opening count by `KL`, and the response redirects to its page

#### Scenario: New item without an article number
- **WHEN** a signed-in user posts an item named `Neuverbindung 9` of 10 mg with an empty article number and an opening count of 4
- **THEN** the item exists with 4 containers and no article number

#### Scenario: Entered consumption replaced
- **WHEN** a signed-in user enters 4 for the second quarter of 2026 and then 5 for the same quarter
- **THEN** the item has one entered value for that quarter, 5

#### Scenario: Fixed identity
- **WHEN** a signed-in user posts the edit form of an item with an article number with a different article number, size and unit
- **THEN** those fields are unchanged

#### Scenario: New lot from the query
- **WHEN** a signed-in user requests `/lab/inventory/bulk/new/?article=CH-0012&batch=B-2026-031&made_on=2026-10-30`
- **THEN** the form holds the article number `CH-0012`, the batch `B-2026-031` and the date 2026-10-30

#### Scenario: Numbers, not keys
- **WHEN** the index is the demo collection's and a signed-in user requests the new-item form
- **THEN** its article numbers' `datalist` offers `CH-0012` labelled `(E)-Zimtsäure` and does not offer `cinnamic-acid`

#### Scenario: Delivery rows without positions lacking a number
- **WHEN** items `CH-0012` and `Neuverbindung 9` without an article number exist and a signed-in user requests the new delivery note form
- **THEN** each row offers `CH-0012` and not `Neuverbindung 9`

### Requirement: Inventory in the admin
The admin SHALL list items, bulk lots, delivery notes and the movements for staff, with search by article number and name and the change history of each record. It shows movements, delivery notes' dates, kinds and lines, and the fixed fields read-only, an item's article number among them once it has one; an article number entered there is given as the item's edit form gives it, only while the item has none. It deletes no movement or delivery note, and deletes an item or lot only while its one movement is the opening and, for an item, no delivery note has a line of it.

#### Scenario: Deleting a booked item
- **WHEN** a staff user deletes an item that has a delivery
- **THEN** the admin refuses and the item remains

#### Scenario: Article number in the admin
- **WHEN** a staff user opens the change page of an item without an article number and of one with `CH-0012`
- **THEN** the first offers the article number as an input and the second shows it read-only

#### Scenario: A stale change page keeps the number
- **WHEN** a staff user loads the admin's change page of an item without an article number, a signed-in user then gives it `CH-0021` in its edit form, and the staff user saves the change page with the article number left empty and a new note
- **THEN** the item keeps `CH-0021` and has the new note
