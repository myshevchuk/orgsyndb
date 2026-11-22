## ADDED Requirements

### Requirement: Stock by batch
The `inventory` package SHALL keep an item's containers by batch: one share for each batch of the item's substance that has held containers of the item, and one share of unknown batch (`unbekannt`, `unknown`), each a whole number of containers at least zero. The item's quantity is the sum of its shares. Each movement changes one share, the one its `batch` names, or the share of unknown batch when it names none (Item movements). An assignment is the exception: it moves containers from the share of unknown batch into the batch it names.

- An opening count goes into the batch the new-item form names, or into the share of unknown batch when the form names none.
- A filling goes into its vessel's batch.
- A delivery takes from its line's batch. When a line of a current delivery note asks for more containers than that batch's share holds, the shortfall is first assigned from the share of unknown batch, by an `assignment` movement before the delivery. The line is refused when the two shares together hold fewer.
- A correction sets the share it names.
- Reversing a delivery returns its containers to its batch's share. Reversing a filling takes its containers from its batch's share, and is refused when that share holds fewer.

Shares change by atomic conditional updates, in the transaction of their movement and together with the quantity. Two bookings prepared from the same shares therefore never take more than a share holds, on PostgreSQL and SQLite alike.

#### Scenario: Fillings into their batches
- **WHEN** a signed-in user creates an item with an opening count of 0, fills 3 containers from a vessel of the batch `KL0412`, and fills 2 from a vessel of the batch `KL0413`
- **THEN** the item has 5 containers: 3 of `KL0412`, 2 of `KL0413` and none of unknown batch

#### Scenario: Opening count of unknown batch
- **WHEN** a signed-in user creates an item with an opening count of 4 and names no batch
- **THEN** it has 4 containers of unknown batch

#### Scenario: Delivery from containers of unknown batch
- **WHEN** an item holds 1 container of the batch `KL0412` and 5 of unknown batch, and a signed-in user books a current note with a line of 3 of `KL0412`
- **THEN** the item has 3 containers, all of unknown batch, and its newest movements, newest first, are a delivery of 3 of `KL0412` with `quantity_after` 3 and an assignment of 2 to `KL0412` with `quantity_after` 6, both naming the note

#### Scenario: Too few even with unknown batch
- **WHEN** an item holds 1 container of the batch `KL0412` and 1 of unknown batch, and a signed-in user books a current note with a line of 3 of `KL0412`
- **THEN** the form shows an error at that line's count, no note exists, and both shares are unchanged

#### Scenario: A reversed delivery returns to its batch
- **WHEN** the delivery of 3 of `KL0412` from that scenario is reversed
- **THEN** the item holds 3 containers of `KL0412` and 3 of unknown batch

#### Scenario: A filling's batch emptied
- **WHEN** an item holds 3 containers of unknown batch, 2 are filled from a vessel of `KL0412`, a current note delivers 2 of `KL0412`, and a signed-in user reverses the filling
- **THEN** the reversal is refused, and the item keeps 3 containers of unknown batch

#### Scenario: Concurrent deliveries of one batch
- **WHEN** an item holds 5 containers of `KL0412` and none of unknown batch, and two deliveries of 4 of `KL0412` are validated against it and then stored one after the other
- **THEN** the first is stored, the second is refused, and the item holds 1 container of `KL0412`

#### Scenario: Correction of one share
- **WHEN** an item holds 3 containers of `KL0412` and 2 of unknown batch, and a signed-in user corrects the share of unknown batch to 0 with a note
- **THEN** the item has 3 containers, all of `KL0412`, and the correction names no batch, with `count` 0 and `quantity_after` 3

## MODIFIED Requirements

### Requirement: Items
The `inventory` package SHALL keep items, each a container size of an article (Articles), with a change history:

- `article`, fixed once the item is created;
- `size`, a decimal greater than zero with up to three places, and `unit`, one of `mg`, `umol` (shown `µmol`), `g` and `mmol`;
- `quantity`, the whole number of containers left, at least zero, changed only by movements, the sum of the item's shares (Stock by batch);
- `note`, optional text;
- `status`, one of `active` (`aktiv`, `active`), the default, `not_needed` (`nicht benötigt`, `not needed`) and `discontinued` (`auslaufend`, `discontinued`), the state set by hand of a size that is set aside;
- `stocked_on` (`Im Bestand seit`, `In stock since`), the day the item entered stock, or none, never after today;
- `compartment` (`Fach`, `Compartment`) and `box` (`Box`, `Box`), where its containers are kept, each optional and at most 30 characters.

The first movement that leaves an item holding containers while it has no `stocked_on` sets it to that movement's date; it may be edited. An item whose `stocked_on` lies in the current calendar year is new (`neu`, `new`).

No two items of one article share size and unit. The size and unit are fixed once the item is created, in the views and the admin alike. An item's substance, name, article number and category are its article's, so every size of an article has the same substance and molar mass. An item without an article number, one whose article has none, cannot be delivered and cannot have consumption entered. An item shows as its article number, container and name, or as its container and name when it has no article number. Containers compare by amount: units of mass before units of amount of substance, then by size in mg or µmol.

#### Scenario: Substance through the article
- **WHEN** the demo data set is written and an item has the article number `CH-0012`
- **THEN** its substance is `cinnamic-acid`, and its name `(E)-Zimtsäure` links to `/lab/registry/substances/cinnamic-acid/` wherever it shows

#### Scenario: One article in two sizes
- **WHEN** a signed-in user creates items of the substance `cinnamic-acid` of 10 µmol and of 50 µmol, then a third of 10 µmol
- **THEN** the first two are saved, as sizes of one article, and the third is refused with an error at the size

#### Scenario: Positions without an article number
- **WHEN** a signed-in user creates an item of 10 mg of a substance `new-compound-9` that has no article
- **THEN** the item is saved as the first size of a new article of that substance, without an article number

#### Scenario: Stock entry by the first filling
- **WHEN** on 2026-11-04 a signed-in user creates an item with an opening count of 0, fills 3 containers from a vessel of its substance dated 2026-10-20, and fills 2 more dated 2026-11-02
- **THEN** its `stocked_on` is 2026-10-20 and it is new

#### Scenario: Stock entry by the opening count
- **WHEN** on 2026-11-04 a signed-in user creates an item with an opening count of 5, and then gives it the `stocked_on` 2019-05-02 in its edit form
- **THEN** its `stocked_on` was 2026-11-04 and is 2019-05-02, its history records the change, and it is not new

### Requirement: Item movements
Every change of an item's quantity SHALL be a movement holding `kind`, `count`, `quantity_after`, `batch`, `date`, `booked_at`, `user`, `note`, and `delivery_note`, `vessel_movement` and `reverses` where they apply. `batch` is the batch whose share the movement changes, and none for the share of unknown batch (Stock by batch):

- `opening` (`Anfangsbestand`, `Opening count`): the first movement of every item, its `count` the quantity entered on creation, in the batch entered or of unknown batch;
- `delivery` (`Abgabe`, `Delivery`): `count` containers out of the share of the line's batch, more than zero and at most what that share holds after any assignment, booked by a line of the current delivery note `delivery_note` and dated as the note;
- `assignment` (`Zuordnung`, `Assignment`): `count` containers of unknown batch, more than zero, given the batch the movement names. It is booked by a line of the current delivery note `delivery_note`, before that line's delivery, and dated as the note. It leaves the quantity unchanged;
- `filling` (`Abfüllung`, `Filling`): `count` containers in, more than zero, taken from a vessel (Filling from bulk) into the share of the vessel's batch, `vessel_movement` the vessel's filling;
- `correction` (`Korrektur`, `Correction`): `count` the containers counted in the share the movement names, at least zero; the quantity changes by the difference, and a note is required;
- `reversal` (`Storno`, `Reversal`): undoes one delivery or filling, named by `reverses`, adding a delivery's count back to its batch's share or taking a filling's back from its batch's share, and returning a filling's amount to its vessel with a vessel reversal; a movement is reversed at most once, a reversal of a filling is refused when its batch's share holds fewer containers than it took in, and a note is required.

`date` is the day the movement took place, today by default and never after today; `booked_at` is the time it was booked. The quantity and the shares a movement changes are changed by atomic conditional updates in the transaction that stores the movement. Two bookings prepared from the same stock can therefore never take more than a share holds, on PostgreSQL and SQLite alike. `quantity_after` is the quantity after those updates. A refused movement changes nothing. Movements are never edited or deleted, in the views or the admin, except that deleting an item in the admin deletes its opening movement with it.

#### Scenario: Delivery
- **WHEN** user `KL` books a delivery note `LS-2026-117` to `Produktion` with one line of 2 containers of the batch `KL0412` of an item holding 5 of that batch
- **THEN** the item has 3, and its newest movement is a delivery of 2 with `quantity_after` 3, by `KL`, naming that note and `KL0412`

#### Scenario: Concurrent deliveries
- **WHEN** two deliveries of 4 of one batch are validated against an item holding 5 of that batch and none of unknown batch, and then stored one after the other
- **THEN** the first is stored, the second is refused, and the item has 1

#### Scenario: Correction needs a note
- **WHEN** a signed-in user posts a correction to 4 without a note
- **THEN** the form shows an error at the note and nothing changes

#### Scenario: Reversing a delivery
- **WHEN** a signed-in user reverses a delivery of 2 dated in the third quarter of 2026, with the note `falsch gebucht`
- **THEN** the item has 2 containers more, in the delivery's batch, the delivery no longer counts in that quarter's consumption, and a second reversal of it is refused

### Requirement: Delivery notes
The `inventory` package SHALL keep delivery notes (`Lieferscheine`), each with a change history: `number`, optional, at most 30 characters, unique among notes when given; `date`, never after today; `recipient`, optional, at most 100 characters; `note`; `historical`; `reversed` and `reversal_note`, the flag of a reversed historical note and the note it was reversed with; `created_by` and `created_at`; and one or more lines, each an item with an article number, a `batch` of the item's substance and a `count` above zero, no item and batch twice in one note. A line of an item without an article number, a line without a batch, and a line whose batch is of another substance are refused, current or historical. A note shows as its number, or as `#<id>` when it has none.

A current note, `historical` off, books for each line an assignment where the line's batch holds too few containers, then one `delivery` movement (Stock by batch), all dated as the note and in one transaction. When one line's count exceeds what its batch and the item's share of unknown batch hold together, the whole note is refused and nothing changes. A historical note, `historical` on, records deliveries made before they could be booked, such as those of old paper delivery notes: its lines change no quantity. A historical note is refused when one of its lines' items has an entered consumption value for the quarter of the note's date, and an entered value is refused for a quarter in which the item has lines of a historical note that is not reversed. A signed-in user may mark a historical note reversed, with a required note; a current note's lines are reversed one by one through their movements, and the note shows as reversed when all its lines are, and as partly reversed when some are. A note's date, kind and lines are fixed once it is created, its number, recipient and note may be edited, and no note is deleted, in the views or the admin.

#### Scenario: Note with several lines
- **WHEN** a signed-in user books a current note with 2 containers of the batch `KL0412` of one item holding 5 of it, and 3 of the batch `KL0420` of another item holding 3 of it
- **THEN** both items are reduced, to 3 and 0, and the note lists both lines with their batches

#### Scenario: One line too many refuses the note
- **WHEN** a signed-in user books a current note with 2 containers of a batch of an item holding 5 of it, and 4 of a batch of an item holding 3 of it and none of unknown batch
- **THEN** the form shows an error at the second line, no note exists, and both items keep their quantities

#### Scenario: Historical note
- **WHEN** a signed-in user enters a historical note dated 2025-03-12 with 4 containers of the batch `KL0412` of an item holding 5 that has no entered value for the first quarter of 2025
- **THEN** the item still has 5, and its consumption in the first quarter of 2025 is 4

#### Scenario: Historical note in a quarter with an entered value
- **WHEN** an item has the entered value 6 for the first quarter of 2025 and a signed-in user enters a historical note dated 2025-03-12 with a line of that item
- **THEN** the form shows an error at that line and nothing is saved

#### Scenario: First delivery needs the article number
- **WHEN** an item without an article number holds 5 containers and a signed-in user posts a current note with a line of 2 of it
- **THEN** the form shows an error at that line, no note exists and the item keeps 5

#### Scenario: Two batches of one item
- **WHEN** a signed-in user books a current note with 2 containers of `KL0412` and 1 of `KL0413` of one item, and then posts another note with two lines of 1 of `KL0412` of that item
- **THEN** the first note has both lines, and the second form shows an error at its second line and saves nothing

#### Scenario: A batch of another substance
- **WHEN** a signed-in user posts a note with a line of an item of `cinnamic-acid` naming a batch of `acetophenone`, current or historical
- **THEN** the form shows an error at that line's batch and nothing is saved

### Requirement: Delivery list
`/lab/inventory/deliveries/` SHALL list the delivery notes, newest date first, then newest booking first, each with its number linking to its page, date, recipient, the mark `nachgetragen` (`entered later`) on a historical note and `storniert` (`reversed`) on a reversed one, and its lines with article number, name, size, batch and count; a current note shows `storniert` when all its lines are reversed and `teilweise storniert` (`partly reversed`) when some are. GET parameters filter it and keep their values: `q`, text found regardless of case in the number or recipient, and `item`, an item's id. `/lab/inventory/deliveries/<id>/` shows one note with its lines, each with the article number, name, size, batch, linking to its page, compartment, box and count, their movements and the change history, and an unknown id answers 404. A signed-in user sees a link `Neuer Lieferschein` (`New delivery note`).

#### Scenario: Deliveries of one item
- **WHEN** two notes have lines of an item and a third does not, and a test client requests the list with that item's id
- **THEN** it lists the two notes, the newer first

#### Scenario: A pick list
- **WHEN** a note has a line of an item kept in compartment `2`, box `7`, and a test client requests the note's page
- **THEN** the line shows `2` and `7` in the columns `Fach` and `Box`

#### Scenario: Lines name their batch
- **WHEN** a note has a line of 2 containers of the batch `KL0412`, and a test client requests the note's page and the delivery list
- **THEN** both show `KL0412` in that line, linking on the note's page to the batch's page

### Requirement: Item page
`/lab/inventory/items/<id>/` SHALL show the article number and name as heading, or the name alone for an item without an article number, followed by the mark `neu` for a new item; the substance, linking to its page; the category, size and note; the `status` when it is not `active`; the `stocked_on`, `–` when there is none; the compartment and the box, `–` for each that is not set; the quantity with its level; its containers by batch (Stock by batch): each batch holding containers of the item, linking to its page, with their count, then `unbekannt` (`unknown`) with the containers of unknown batch when there are any; the means and coverage; the current year's consumption; a chart of the consumption of each quarter of the two complete years before the current one and of the current year, an inline `svg` with one bar per quarter titled with the quarter and its value and, when the item has a mean, a line at the mean per quarter, followed by a table of each quarter's entered value, deliveries and total, in which a signed-in user sees beside each quarter's entered value a link to the consumption form for that quarter (Inventory forms), `Ändern` (`Change`) where the quarter has an entered value and `Nachtragen` (`Enter`) where it has none, except on the page of an item without an article number, beside a quarter that has not begun, and beside a quarter that holds lines of a historical note that is not reversed (Consumption), and each such link opens its form in a dialog over the page (web-app "Form dialogs"); the movements in booking order, newest first, with date, booking time, kind, count, quantity after, batch, linking to its page or `unbekannt` for the share of unknown batch, the user's initials, the delivery note with its number and recipient, the note, and the mark `storniert` (`reversed`) on a reversed movement; its bulk (Filling from bulk): the open vessels of its substance, each with its batch and amount and linking to its page, and the number of containers they would fill; under `Prognose` (`Forecast`), the item's forecast, as `production-planning` states under Item forecast; and the change history, which includes that of the item's entered consumption: each entry, change and removal of a quarter's value, headed `Verbrauch Q<quarter> <year>` (`Consumption Q<quarter> <year>`), with the old and new count, `–` standing for none; the entries of item and entered consumption are shown together, newest first, and of entries made at the same moment those of the entered consumption first. A signed-in user sees the links `Abgabe buchen` (`Book delivery`), to the new delivery note with the item in its first line, `Abfüllen` (`Fill`), `Bestand korrigieren` (`Correct count`), `Verbrauch nachtragen` (`Enter consumption`), `Bearbeiten` (`Edit`), and `Stornieren` (`Reverse`) beside each delivery and filling not yet reversed; for an item without an article number, `Artikelnr. eintragen` (`Enter article number`), to its edit form, takes the place of `Abgabe buchen`, and `Verbrauch nachtragen` is left out. An unknown id answers 404.

#### Scenario: Chart and ledger
- **WHEN** on 2026-11-04 a test client requests the page of an item with entered values for three quarters of 2025 and two deliveries in 2026
- **THEN** the `svg` has twelve bars, the table lists the same values, and the movements list the deliveries before the opening count

#### Scenario: Page of a position without an article number
- **WHEN** a signed-in user requests the page of an item of 10 mg of the substance `new-compound-9`, named `Neuverbindung 9`, without an article number
- **THEN** its heading is `Neuverbindung 9`, its substance links to `/lab/registry/substances/new-compound-9/`, and it links `Artikelnr. eintragen` to its edit form and has neither `Abgabe buchen` nor `Verbrauch nachtragen`

#### Scenario: A discontinued size
- **WHEN** a test client requests the page of an item with the `status` `discontinued`, 4 containers and the `stocked_on` 2024-03-01
- **THEN** it shows `auslaufend`, `01.03.2024`, and 4 with the class `level-dormant` and the text `ruhend`

#### Scenario: Changing a quarter's entered value
- **WHEN** on 2026-11-04 a signed-in user requests the page of an item with an article number that has the entered value 40 for the third quarter of 2026, the entered value 0 for the second quarter of 2025, no value for the second quarter of 2026, and a historical note with a line of the item dated in the first quarter of 2026
- **THEN** the row of the third quarter of 2026 links `Ändern` to `/lab/inventory/items/<id>/consumption/?year=2026&quarter=3`, the second quarter of 2025 links `Ändern` to the form for it, the second quarter of 2026 links `Nachtragen` to the form for it, the first quarter of 2026 has no such link, and each link opens in a dialog

#### Scenario: History of entered consumption
- **WHEN** user `KL` enters 400 for the third quarter of 2026 of an item, then changes the item's note, then enters 40 for the same quarter, then removes it, and a test client requests the item's page
- **THEN** its history holds, newest first, an entry headed `Verbrauch Q3 2026` changing the count from 40 to `–`, one changing it from 400 to 40, the item's change of its note, and one headed `Verbrauch Q3 2026` changing the count from `–` to 400, each naming `KL`

#### Scenario: Containers by batch
- **WHEN** an item holds 3 containers of `KL0412`, none of `KL0413` and 2 of unknown batch, and a test client requests its page
- **THEN** its containers by batch are `KL0412` with 3, linking to the batch's page, and `unbekannt` with 2, and `KL0413` is not among them

### Requirement: Inventory forms
For a signed-in user, the application SHALL offer:

- `/lab/inventory/end-products/new/`: a new item with its opening count and the batch it is of, optional, chosen among the batches offered as on a delivery note's row, none standing for unknown batch; its substance by key; the article number, optional, and the category with a `datalist` of the categories in use, the `stocked_on`, optional, left empty for the opening count to set, and the compartment and the box, each with a `datalist` of the values in use;
- `/lab/inventory/items/<id>/edit/`: the item's note, `status`, `stocked_on`, compartment and box, the last two each with a `datalist` of the values in use, and its article's category and, while the article has none, its article number, both saved on the article for every size of it, as the form says beside them;
- `/lab/inventory/deliveries/new/`: a delivery note with ten rows for lines, each offering the items with an article number, each shown as its article number, container and name and, where they are set, `Fach <compartment>` and `Box <box>` (`Compartment <compartment>`, `Box <box>`), joined by ` · ` and the locations by ` / `, and the batches of the substances of the items it offers, grouped under their substance's name, each shown as the batch shows; a row with only some of item, batch and count is refused at the field missing, and rows left empty are ignored; and a check box `nachgetragen – Bestand bleibt unverändert` (`entered later – stock unchanged`) for a historical note; `?item=<id>`, given once or several times, puts those items in the first rows in the order given, up to ten, leaving out ids of items it does not offer and ids given twice;
- `/lab/inventory/deliveries/<id>/reverse/`: marking a historical note reversed, with its note;
- `/lab/inventory/items/<id>/fill/`: a filling, its vessel chosen among the open vessels of the item's substance, each offered as the vessel, its kind, its location where it has one, and its amount, joined by ` · `; and `/lab/inventory/items/<id>/correct/`: a correction of one share, chosen among the batches of the item's substance, each with the item's containers of it, and `unbekannt` (`unknown`) with its containers of unknown batch, the default;
- `/lab/inventory/items/<id>/movements/<movement id>/reverse/`: the reversal of a delivery or filling, with its note;
- `/lab/inventory/items/<id>/consumption/`: the entered value of a year and quarter, replacing an earlier one of that quarter, or removing it when left empty; `?year=<year>&quarter=<quarter>`, naming a quarter that has begun, fixes the form to that quarter, which it names in place of the fields for the year and the quarter, and fills in its entered value, zero included, naming it as the value a save replaces, or leaves the count empty where the quarter has none; other values of the two parameters are ignored, and the form opens as without them; beside its fields the form shows the item's consumption as the item page does, its chart and its table of quarters with their links, a link choosing its quarter in the form;
- `/lab/inventory/deliveries/<id>/edit/`: a note's number, recipient and note;
- `/lab/inventory/batches/new/`: a new batch with its substance by key; its source, `hergestellt` when none is chosen; for a made batch its number and its journal entry, given as `<code>/<number>` as a task step names one (task-tracker "Task page"); for a bought batch its supplier, the supplier's article number and the supplier's batch; its date, today by default; its note; and an amount, its unit and a location, with a `datalist` of the locations in use, that open the batch's first vessel, a stored one, when the amount is given. `?substance=<key>` fills in the substance. `?step=<id>` records a batch made by that task step: the source is `hergestellt`, the substance is filled in with the first product of the step's entry, or the task's substance for a step without one, and a substance the step does not make is refused; the journal entry is the step's, shown and not editable, when the step names one; and the amount is required and is the batch's yield, opening a flask when no location is given and a stored vessel at the location given. A step whose task is neither planned nor running, a number another made batch has regardless of case, a number on a bought batch, an amount without its unit, and a journal entry whose code is no notebook's are refused;
- `/lab/inventory/batches/<id>/edit/`: the number, journal entry and yield of a made batch, the supplier, supplier's article number and supplier's batch of a bought one, and the date and note;
- `/lab/inventory/batches/<id>/vessels/new/`: a new stored vessel of the batch with its opening amount, its unit, its location, with the `datalist` of the locations in use, and its note;
- `/lab/inventory/vessels/<id>/withdraw/`: a withdrawal from an open vessel into a step of a task that is planned or running, chosen among those tasks' steps or given as `?step=<id>`, with the amount in the vessel's unit and the date; an amount above the vessel's is refused;
- `/lab/inventory/vessels/<id>/transfer/`: a transfer from an open vessel, with the amount in the source vessel's unit, the date and a note, into a stored vessel of the same batch, chosen among them, or into a new vessel at the location given; an amount above the vessel's, and a target whose unit converts from the source's only through a molar mass the substance lacks, are refused, the latter with an error at the target;
- `/lab/inventory/vessels/movements/<id>/reverse/`, a POST: reverses a withdrawal not yet reversed;
- `/lab/inventory/vessels/<id>/edit/`, for the location and note, and `/lab/inventory/vessels/<id>/correct/`.

A batch of another substance than the item's is refused at the batch, on the new-item form and in a delivery note's row. A substance is named by its key, offered through a `datalist` of every substance's key labelled with its name; an unknown key is an error at the field. On the new-item form, the article number and the category make the substance's article when it has none, an empty number giving it none. When the substance has an article, a field left empty leaves the article's value as it is; a category entered replaces the article's; an article number entered gives the article that number when it has none, as the edit form does, and must otherwise be its number, or the form shows an error at it. On the edit form, the category field holds the article's category and saves what it holds, empty included, and the article number, offered only while the article has none, gives it one when entered and leaves it without one when empty. Invalid input shows the form again with the errors beside their fields and saves nothing. A saved form leads, with a message naming the record, to the page of the delivery note for the forms of notes, to the page of the batch for the new-batch form, and to the page of the item, batch or vessel for every other; a form saved in a dialog leaves the page it was opened from in place instead. On an item's page and in the item list's details, the links to the item's edit form, its filling, its count correction and its consumption, and on its page each link `Stornieren` beside a movement, open those forms in a dialog over the page (web-app "Form dialogs"); `Abgabe buchen` leads to the new delivery note's form page.

#### Scenario: New item
- **WHEN** user `KL` posts an item of the substance `cinnamic-acid`, whose article is `CH-0012`, of 10 µmol with an opening count of 12
- **THEN** the item exists with 12 containers, its only movement is the opening count by `KL`, and the response redirects to its page

#### Scenario: New item without an article number
- **WHEN** a signed-in user posts an item of the substance `new-compound-9`, which has no article, of 10 mg with an empty article number and an opening count of 4
- **THEN** the item exists with 4 containers, and its new article has no article number

#### Scenario: Another size of a numbered article
- **WHEN** the article of `cinnamic-acid` is `CH-0012` in the category `Säuren`, and a signed-in user posts an item of `cinnamic-acid` of 50 µmol with the article number and the category left empty, then one of 100 µmol with the article number `CH-0099`
- **THEN** the first item is saved and the article is still `CH-0012` in `Säuren`, and the second form shows an error at the article number and saves nothing

#### Scenario: Unknown substance
- **WHEN** a signed-in user posts the new-item form naming the substance `no-such-substance`
- **THEN** the form shows an error at the substance and nothing is saved

#### Scenario: Entered consumption replaced
- **WHEN** a signed-in user enters 4 for the second quarter of 2026 and then 5 for the same quarter
- **THEN** the item has one entered value for that quarter, 5

#### Scenario: Fixed identity
- **WHEN** a signed-in user posts the edit form of an item with an article number with a different article number, size and unit
- **THEN** those fields are unchanged

#### Scenario: A batch from a step
- **WHEN** on 2026-11-04 a signed-in user requests `/lab/inventory/batches/new/?step=<id>` for the last step of a running task of `cinnamic-acid`, a step that names the journal entry `AE-1/9`
- **THEN** the form holds the substance `cinnamic-acid`, the source `hergestellt`, the date 2026-11-04 and the journal entry `AE-1/9`, not editable, and posting it without an amount shows an error at the amount

#### Scenario: Vessels offered for a filling
- **WHEN** an item of `CH-0012` has an open flask of the batch `KL0412` holding `2` g and a used-up vessel of another batch, and a signed-in user requests the item's filling form
- **THEN** it offers the flask alone, as `KL0412 #<id> · Kolben · 2 g`

#### Scenario: Substances offered
- **WHEN** the demo data set is written and a signed-in user requests the new-item form
- **THEN** its substances' `datalist` offers `cinnamic-acid` labelled `(E)-Zimtsäure`

#### Scenario: Delivery rows without positions lacking a number
- **WHEN** items `CH-0012` and `Neuverbindung 9` without an article number exist and a signed-in user requests the new delivery note form
- **THEN** each row offers `CH-0012` and not `Neuverbindung 9`

#### Scenario: Setting a size aside
- **WHEN** a signed-in user posts the edit form of an item with the `status` `not_needed`
- **THEN** the item has that status, its history records the change, and the list shows it as dormant

#### Scenario: Stock entry in the future
- **WHEN** on 2026-11-04 a signed-in user posts the edit form of an item with the `stocked_on` 2026-11-05
- **THEN** the form shows an error at it and the item is unchanged

#### Scenario: A note from the selection
- **WHEN** a signed-in user requests `/lab/inventory/deliveries/new/?item=<a>&item=<b>&item=<a>&item=<c>`, `<c>` the id of an item without an article number
- **THEN** the first row holds item `<a>`, the second `<b>`, and the other rows none

#### Scenario: Rows name the location
- **WHEN** an item `CH-0012` of 100 mg named `(E)-Zimtsäure` is kept in compartment `2`, box `7`, and a signed-in user requests the new delivery note form
- **THEN** its rows offer it as `CH-0012 · 100 mg · (E)-Zimtsäure · Fach 2 / Box 7`

#### Scenario: Item forms as dialogs
- **WHEN** a signed-in user requests the item list with an item's details and that item's page
- **THEN** in the details and on the page, the links `Abfüllen`, `Bestand korrigieren`, `Verbrauch nachtragen` and `Bearbeiten`, and on the page each `Stornieren`, open their forms in a dialog, and `Abgabe buchen` does not

#### Scenario: The form for a quarter
- **WHEN** an item has the entered value 400 for the third quarter of 2026, and a signed-in user requests its consumption form with `?year=2026&quarter=3`
- **THEN** the form names the quarter `Q3 2026` and has no field for the year or the quarter, holds the count 400, names 400 as the value a save replaces, and shows the item's chart and its table of quarters, the third quarter's row linking `Ändern` to the form for that quarter; the same request with `?year=2026&quarter=9` opens the form with fields for the year and the quarter and no value named

#### Scenario: Opening count of a batch
- **WHEN** a signed-in user posts an item of the substance `cinnamic-acid` with an opening count of 4 and the batch `KL0412` of `cinnamic-acid`, and then another of another size naming a batch of `acetophenone`
- **THEN** the first item holds 4 containers of `KL0412`, and the second form shows an error at the batch and saves nothing

#### Scenario: A row needs its batch
- **WHEN** a signed-in user posts a delivery note with a row holding an item and a count and no batch
- **THEN** the form shows an error at that row's batch and nothing is saved

#### Scenario: Shares offered for a correction
- **WHEN** an item holds 3 containers of `KL0412` and 2 of unknown batch, its substance has the batch `KL0413` too, and a signed-in user requests its correction form
- **THEN** it offers `unbekannt` with 2, chosen, `KL0412` with 3 and `KL0413` with 0

### Requirement: Inventory in the admin
The admin SHALL list articles, items, batches, vessels, delivery notes and the movements for staff, with search by article number and by the substance's key and names, and the change history of each record. It shows movements, delivery notes' dates, kinds and lines, an item's shares (Stock by batch), and the fixed fields read-only, an article's number among them once it has one; an article number entered there is given as the edit form gives it, only while the article has none. It deletes no movement or delivery note, deletes an article only while it has no items, deletes an item or vessel only while its one movement is the opening and, for an item, no delivery note has a line of it, and deletes a batch only while no vessel, share, delivery line or movement names it and no task step made it.

#### Scenario: Deleting a booked item
- **WHEN** a staff user deletes an item that has a delivery
- **THEN** the admin refuses and the item remains

#### Scenario: Article number in the admin
- **WHEN** a staff user opens the change page of an article without a number and of the article `CH-0012`
- **THEN** the first offers the article number as an input and the second shows it read-only

#### Scenario: A stale change page keeps the number
- **WHEN** a staff user loads the admin's change page of an article without a number, a signed-in user then gives it `CH-0021` in the edit form of one of its items, and the staff user saves the change page with the article number left empty and a new category
- **THEN** the article keeps `CH-0021` and has the new category

### Requirement: Batch page
`/lab/inventory/batches/<id>/` SHALL show the batch as heading; its substance, linking to its page, and the article number of the substance's article when there is one; its source; for a made batch, its journal entry linking to its notebook's page, the step that made it as its task's number and `Stufe <n>` (`Step <n>`) linking to the task's page, and its yield; for a bought batch, its supplier, the supplier's article number and the supplier's batch; its date and note; each field `–` when it has no value; its vessels, the open ones first, then by id, each as `#<id>` linking to its page, with its kind, location, amount and, at zero, the mark `aufgebraucht` (`used up`); the fillings from its vessels, newest first, each with its date, the item filled linking to its page, the count and the vessel, and the mark `storniert` (`reversed`) on a reversed one; the items holding containers of it, each linking to its page, with their count; its deliveries, newest first, each with its date, the delivery note linking to its page, the recipient, the item and the count, and the mark `storniert` on a reversed one; and its change history. A signed-in user sees the links `Bearbeiten` (`Edit`) and `Neues Gefäß` (`New vessel`). An unknown id answers 404.

#### Scenario: Where a batch went
- **WHEN** 5 containers of an item of `CH-0012` were filled from the flask of `KL0412`, its rest was transferred into a new vessel, a note `LS-2026-117` delivered 2 of those containers, and a test client requests the batch's page
- **THEN** it lists the stored vessel and then the flask, marked `aufgebraucht`; the filling of 5 linking to the item's page; the item with 3; and the delivery of 2 naming `LS-2026-117`, linking to its page
