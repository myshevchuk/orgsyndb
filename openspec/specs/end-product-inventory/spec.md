# end-product-inventory Specification

## Purpose
Count the lab's end products in the lab application: items in containers of one size, changed only by movements, delivery notes current and historical, consumption per quarter with its means and coverage, stock levels, bulk lots and filling from them, their lists, pages and forms, and the admin.
## Requirements
### Requirement: Items
The `inventory` package SHALL keep items, each with a change history:

- `inventory`, `end-products` for every item this capability creates;
- `article_number`, required, at most 30 characters;
- `name`, required, at most 200 characters;
- `category`, optional, at most 100 characters;
- `size`, a decimal greater than zero with up to three places, and `unit`, one of `mg`, `umol` (shown `µmol`), `g` and `mmol`;
- `quantity`, the whole number of containers left, at least zero, changed only by movements;
- `note`, optional text.

No two items of an inventory share article number, size and unit. The article number, size and unit are fixed once the item is created, in the views and the admin alike. An item's compound is `compound_for(article_number)`, shown through the compound links, so every size of an article has the same compound and molar mass.

#### Scenario: Compound through the article number
- **WHEN** the index is the demo collection's and an item has the article number `CH-0012`
- **THEN** its compound is `cinnamic-acid`, and its name links to `/compounds/cinnamic-acid/` wherever the compound shows

#### Scenario: One article in two sizes
- **WHEN** a signed-in user creates an item `CH-0012` of 10 µmol and another of 50 µmol, then a third of 10 µmol
- **THEN** the first two are saved and the third is refused with an error at the size

### Requirement: Item movements
Every change of an item's quantity SHALL be a movement holding `kind`, `count`, `quantity_after`, `date`, `booked_at`, `user`, `note`, and `delivery_note`, `bulk_movement` and `reverses` where they apply:

- `opening` (`Anfangsbestand`, `Opening count`): the first movement of every item, its `count` the quantity entered on creation;
- `delivery` (`Abgabe`, `Delivery`): `count` containers out, more than zero and at most the quantity, booked by a line of the current delivery note `delivery_note` and dated as the note;
- `filling` (`Abfüllung`, `Filling`): `count` containers in, more than zero; `bulk_movement` the lot's movement when a lot was named;
- `correction` (`Korrektur`, `Correction`): `count` the quantity counted, at least zero; a note is required;
- `reversal` (`Storno`, `Reversal`): undoes one delivery or filling, named by `reverses`, adding back a delivery's count or taking back a filling's, and returning a filling's amount to its lot with a lot reversal; a movement is reversed at most once, a reversal of a filling whose containers are no longer there is refused, and a note is required.

`date` is the day the movement took place, today by default and never after today; `booked_at` is the time it was booked. The quantity changes by one atomic conditional update in the transaction that stores the movement, so two bookings prepared from the same quantity can never take more than it holds, on PostgreSQL and SQLite alike, and `quantity_after` is the quantity after that update. A refused movement changes nothing. Movements are never edited or deleted, in the views or the admin, except that deleting an item in the admin deletes its opening movement with it.

#### Scenario: Delivery
- **WHEN** user `KL` books a delivery note `LS-2026-117` to `Produktion` with one line of 2 containers of an item with 5
- **THEN** the item has 3, and its newest movement is a delivery of 2 with `quantity_after` 3, by `KL`, naming that note

#### Scenario: Concurrent deliveries
- **WHEN** two deliveries of 4 are validated against an item with 5 and then stored one after the other
- **THEN** the first is stored, the second is refused, and the item has 1

#### Scenario: Correction needs a note
- **WHEN** a signed-in user posts a correction to 4 without a note
- **THEN** the form shows an error at the note and nothing changes

#### Scenario: Reversing a delivery
- **WHEN** a signed-in user reverses a delivery of 2 dated in the third quarter of 2026, with the note `falsch gebucht`
- **THEN** the item has 2 containers more, the delivery no longer counts in that quarter's consumption, and a second reversal of it is refused

### Requirement: Delivery notes
The `inventory` package SHALL keep delivery notes (`Lieferscheine`), each with a change history: `number`, optional, at most 30 characters, unique among notes when given; `date`, never after today; `recipient`, optional, at most 100 characters; `note`; `historical`; `reversed` and `reversal_note`, the flag of a reversed historical note and the note it was reversed with; `created_by` and `created_at`; and one or more lines, each an item of the inventory `end-products` and a `count` above zero, no item twice in one note. A note shows as its number, or as `#<id>` when it has none.

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

### Requirement: Consumption
An item SHALL keep entered consumption per quarter, a whole number of containers of at least zero for a year and a quarter 1 to 4, at most one per quarter; entering a value replaces the quarter's earlier one, and entering none removes it. A quarter's consumption is its entered value, zero when there is none, plus the counts of the item's lines, in notes current or historical, dated in it, leaving out reversed movements and reversed historical notes. Quarters and years follow the calendar in `Europe/Berlin`.

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

### Requirement: Stock levels
An item's level SHALL be `out` (`aufgebraucht`, `out`) when its quantity is zero; otherwise, with a mean per quarter `Q` above zero, `critical` (`kritisch`, `critical`) below `Q/2`, `low` (`niedrig`, `low`) below `Q`, and `watch` (`beobachten`, `watch`) below `2Q`; otherwise it has none. Wherever a quantity shows with its level, its cell carries the class `level-<level>` and the level's label as text. `lab.css` gives the four classes red, orange, yellow and pale green backgrounds as colour tokens with a dark-scheme variant, each keeping the cell's text at a WCAG 2 contrast ratio of at least 4.5:1 against its background, unrounded, in both schemes.

#### Scenario: Thresholds
- **WHEN** items with a mean per quarter of 4 have 0, 1, 2, 3, 4, 7 and 8 containers
- **THEN** their levels are out, critical, low, low, watch, watch and none

#### Scenario: No consumption
- **WHEN** an item without entered values or deliveries has 2 containers
- **THEN** it has no level and no coverage

### Requirement: Bulk lots
The `inventory` package SHALL keep bulk lots, each with a change history: `inventory`; `article_number`, required; `unit`, one of `mg`, `g`, `umol` and `mmol`, in which the lot is entered and shown; `amount`, at least zero, kept in the lot's base unit, `mg` for `mg` and `g` and `µmol` for `µmol` and `mmol`, with six decimal places; `batch`, `location`, at most 100 characters, and `made_on`, each optional; and `note`. The article number and unit are fixed once the lot is created. A lot belongs to every item of its inventory with the same article number. Its amount shows in its unit to three decimal places, rounded half up.

Its amount changes only by its movements, each holding `kind`, `amount`, `amount_after`, `date`, `booked_at`, `user` and `note`, by one atomic conditional update in the transaction that stores the movement, as for items: `opening`, the amount entered on creation; `filling`, the amount taken, more than zero and at most the lot's amount; `correction`, the amount weighed, with a required note; `reversal`, the amount a reversed filling returns. A lot at zero is used up. Lot movements are never edited or deleted, except that deleting a lot in the admin deletes its opening movement with it.

#### Scenario: Correction of a lot
- **WHEN** a signed-in user corrects a lot of `50` mg to `47,5` mg with the note `nachgewogen`
- **THEN** the lot holds `47,5` mg and its newest movement is that correction

### Requirement: Filling from bulk
Filling an item SHALL optionally name an open lot of its article number and the amount taken from it, in the lot's unit. The proposed amount is the count times the item's size, converted into the lot's base unit and rounded half up to six places, shown in the lot's unit. The filling form has, besides its button to book, a button `Menge vorschlagen` (`Propose amount`), which books nothing and shows the form again with the values entered and the amount set to the proposal for the count and lot entered. When a lot is named and the amount is left empty, the proposed amount is booked. Units of the same kind convert by their factors: 1 g is 1000 mg, and 1 mmol is 1000 µmol. Mass and amount of substance convert through the molar mass of the item's compound in g/mol. Without that molar mass across kinds, nothing is proposed, the amount is required, and `Menge vorschlagen` shows an error at the amount. The item's filling and the lot's filling are stored in one transaction. An amount above the lot's, or one that rounds to zero, refuses both.

Wherever an item shows its bulk, it shows the amount of its open lots by unit and the number of its containers they would still fill. That number is, for each open lot that converts into the item's unit, its amount converted and divided by the size and rounded down, summed over the lots. A lot that does not convert is left out of that number and counted as not convertible.

#### Scenario: Filling with conversion
- **WHEN** the index is the demo collection's, an item `CH-0012` of 10 µmol has a lot of `50` mg, and a signed-in user fills 5 containers from it
- **THEN** `Menge vorschlagen` shows the form with the amount `7,408` and books nothing; booking it gives the item 5 more containers, the lot holds `42,592` mg, and the item's movement names the lot's movement

#### Scenario: Small filling from a lot in grams
- **WHEN** the index is the demo collection's, an item `CH-0012` of 10 µmol has a lot of `1` g, and a signed-in user fills 1 container from it, leaving the amount empty
- **THEN** the lot holds 998,5184 mg, shown as `0,999` g

#### Scenario: Containers from bulk
- **WHEN** the index is the demo collection's and an item `CH-0012` of 10 µmol has one open lot of `50` mg
- **THEN** it shows `50 mg` and 33 containers

#### Scenario: Lots are not pooled
- **WHEN** an item of 10 mg has two open lots of `6` mg
- **THEN** it shows 0 containers from bulk

### Requirement: Item list
`/lab/inventory/end-products/` SHALL list the items of the inventory `end-products` in a table with the columns `Artikelnr.`, `Name`, `Kategorie`, `Gebinde`, `Bestand`, `Ø Quartal`, `Ø Jahr`, `lfd. Jahr`, `Reichweite`, `Bulk` and `Bemerkung` (`Article no.`, `Name`, `Category`, `Container`, `Stock`, `Mean per quarter`, `Mean per year`, `This year`, `Coverage`, `Bulk`, `Note`): the article number linking to the item's page; the name, linking to the compound when there is one; the category; the size with its unit; the quantity with its level; the means; the current year's consumption; the coverage; the bulk; and the note. Rows are ordered by article number, then unit, then size; with `sort=urgency`, by level, out first and items without a level last, then by coverage, smallest first and items without one last, then as without `sort`. GET parameters filter the list and keep their values in the form above it: `category`; `level`, one of `watch`, `low`, `critical` and `out`, listing the items at that level or a more urgent one; and `q`, text found regardless of case in the article number, name, category, note or the name of the item's compound. A line above the table counts the items listed, and a legend below it names the four levels with their thresholds. A signed-in user sees a link `Neuer Artikel` (`New item`). `/lab/inventory/` redirects to this list.

#### Scenario: Urgent items first
- **WHEN** the database holds items at the levels watch, none, out and low, and a test client requests the list with `sort=urgency`
- **THEN** the rows show out, low, watch and then the item without a level

#### Scenario: Level filter
- **WHEN** a test client requests the list with `level=low`
- **THEN** it lists exactly the items at the levels low, critical and out

### Requirement: Bulk list
`/lab/inventory/end-products/bulk/` SHALL list the open bulk lots of the inventory `end-products` with the columns `Artikelnr.`, `Name`, `Charge`, `Menge`, `Ort`, `Datum` and `Bemerkung` (`Article no.`, `Name`, `Batch`, `Amount`, `Location`, `Date`, `Note`), the name being that of the article number's first item in the item list's order, empty when it has none, ordered by article number, then date, oldest first and lots without one last. `empty=1` adds the used-up lots. The item list, the bulk list and the delivery list carry section tabs `Artikel`, `Bulk` and `Lieferungen` (`Items`, `Bulk`, `Deliveries`) in the site's `nav.section-tabs` markup. A signed-in user sees a link `Neues Bulk` (`New bulk lot`).

#### Scenario: Used-up lots
- **WHEN** the database holds an open lot and a used-up lot, and a test client requests the bulk list with and without `empty=1`
- **THEN** it lists both with it and only the open lot without

### Requirement: Delivery list
`/lab/inventory/deliveries/` SHALL list the delivery notes, newest date first, then newest booking first, each with its number linking to its page, date, recipient, the mark `nachgetragen` (`entered later`) on a historical note and `storniert` (`reversed`) on a reversed one, and its lines with article number, name, size and count; a current note shows `storniert` when all its lines are reversed and `teilweise storniert` (`partly reversed`) when some are. GET parameters filter it and keep their values: `q`, text found regardless of case in the number or recipient, and `item`, an item's id. `/lab/inventory/deliveries/<id>/` shows one note with its lines, their movements and the change history, and an unknown id answers 404. A signed-in user sees a link `Neuer Lieferschein` (`New delivery note`).

#### Scenario: Deliveries of one item
- **WHEN** two notes have lines of an item and a third does not, and a test client requests the list with that item's id
- **THEN** it lists the two notes, the newer first

### Requirement: Item page
`/lab/inventory/items/<id>/` SHALL show the article number and name as heading; the compound; the category, size and note; the quantity with its level; the means and coverage; the current year's consumption; a chart of the consumption of each quarter of the two complete years before the current one and of the current year, an inline `svg` with one bar per quarter titled with the quarter and its value and, when the item has a mean, a line at the mean per quarter, followed by a table of each quarter's entered value, deliveries and total; the movements in booking order, newest first, with date, booking time, kind, count, quantity after, the user's initials, the delivery note with its number and recipient, the note, and the mark `storniert` (`reversed`) on a reversed movement; the open lots of its article number with the number of containers they would fill; and the change history. A signed-in user sees the links `Abgabe buchen` (`Book delivery`), to the new delivery note with the item in its first line, `Abfüllen` (`Fill`), `Bestand korrigieren` (`Correct count`), `Verbrauch nachtragen` (`Enter consumption`), `Bearbeiten` (`Edit`), and `Stornieren` (`Reverse`) beside each delivery and filling not yet reversed. An unknown id answers 404.

#### Scenario: Chart and ledger
- **WHEN** on 2026-11-04 a test client requests the page of an item with entered values for three quarters of 2025 and two deliveries in 2026
- **THEN** the `svg` has twelve bars, the table lists the same values, and the movements list the deliveries before the opening count

### Requirement: Bulk lot page
`/lab/inventory/bulk/<id>/` SHALL show the lot's article number, batch, amount, location, date and note, the mark `aufgebraucht` (`used up`) at zero, its movements in booking order, newest first, with date, booking time, kind, amount, amount after, the user's initials, note and, for a filling, the item filled, and its change history. A signed-in user sees the links `Korrigieren` (`Correct`) and `Bearbeiten` (`Edit`). An unknown id answers 404.

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
- `/lab/inventory/bulk/new/`: a new lot with its opening amount and the location with a `datalist` of the locations in use; `?article=<article number>` fills in the article number;
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

### Requirement: Inventory in the admin
The admin SHALL list items, bulk lots, delivery notes and the movements for staff, with search by article number and name and the change history of each record. It shows movements, delivery notes' dates, kinds and lines, and the fixed fields read-only, deletes no movement or delivery note, and deletes an item or lot only while its one movement is the opening and, for an item, no delivery note has a line of it.

#### Scenario: Deleting a booked item
- **WHEN** a staff user deletes an item that has a delivery
- **THEN** the admin refuses and the item remains

