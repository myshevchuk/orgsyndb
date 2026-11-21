## MODIFIED Requirements

### Requirement: Consumption
An item SHALL keep entered consumption per quarter, with a change history (web-app "Change history"), a whole number of containers of at least zero for a year and a quarter 1 to 4, not after the current quarter, at most one per quarter; entering a value replaces the quarter's earlier one, and entering none removes it. Entering a value for an item without an article number is refused, zero included. A quarter's consumption is its entered value, zero when there is none, plus the counts of the item's lines, in notes current or historical, dated in it, leaving out reversed movements and reversed historical notes. Quarters and years follow the calendar in `Europe/Berlin`.

The mean per year is the sum of the consumption of the complete calendar years before the current one, from the year of the item's first entered value, zero included, or delivery line that counts as consumption, divided by the number of those years; with none, there is no mean. The mean per quarter is a quarter of the mean per year. An item whose consumption above zero all lies in the current year has projected means instead: the mean per quarter is the current year's consumption times 91.3125 divided by the number of days from the first day of the quarter of its first consumption above zero to today, today included, or by 91.3125 when that is fewer; the mean per year is four times that. Projected means, and a coverage computed from them, are marked `hochgerechnet aus dem laufenden Jahr` (`projected from the current year`) wherever they show. The current year's consumption is that of the current year so far, shown beside the mean for comparison. The coverage is the quantity divided by the mean per quarter, in quarters, and has no value without a mean above zero or for an item whose level is `dormant` or `undelivered`. Means and coverage show to one decimal place, rounded half up; levels compare the unrounded values.

#### Scenario: Means and coverage
- **WHEN** on 2026-11-04 an item with 3 containers has the entered value 4 for each quarter of 2024, 5 for each quarter of 2025 and 10 for the first quarter of 2026, and a delivery of 3 dated 2026-10-15
- **THEN** its mean per year is 18, its mean per quarter 4,5, its current year's consumption 13, its coverage 0,7 quarters, and its level low

#### Scenario: Years counted
- **WHEN** on 2026-11-04 one item has the entered value 0 for the third quarter of 2024 and 8 for each quarter of 2025, and another has entered values only in 2026
- **THEN** the first item's mean per year is 16, and the second's means are projected

#### Scenario: A reversed note does not start the history
- **WHEN** on 2026-11-04 an item has the entered value 8 for each quarter of 2025 and a historical note dated 2024-05-02, which is then reversed
- **THEN** its mean per year is 32

#### Scenario: Entered value removed for old notes
- **WHEN** an item has the entered value 6 for the first quarter of 2025, a signed-in user removes it, and then enters a historical note dated 2025-03-12 with 4 of that item
- **THEN** the note is saved and the quarter's consumption is 4

#### Scenario: No consumption without an article number
- **WHEN** a signed-in user enters 3, and then 0, for the second quarter of 2026 on an item without an article number
- **THEN** the form shows an error each time and the item has no entered value

#### Scenario: No value for a quarter to come
- **WHEN** on 2026-11-04 a signed-in user enters 3 for the first quarter of 2027, and then 3 for the fourth quarter of 2026
- **THEN** the first is refused with an error and the second is saved

#### Scenario: Projected means
- **WHEN** on 2026-11-04 an item with 3 containers has the entered value 6 for the second quarter of 2026 and no other consumption
- **THEN** its mean per quarter is 2,5, its mean per year 10,1 and its coverage 1,2 quarters, each marked as projected, and its level is watch

#### Scenario: One early delivery
- **WHEN** on 2026-11-04 an item with 2 containers has a delivery of 3 dated 2026-10-15 and no other consumption
- **THEN** its projected mean per quarter is 3,0, its coverage 0,7 quarters and its level low

#### Scenario: No coverage for a dormant item
- **WHEN** on 2026-11-04 an item with 6 containers has the entered value 8 for each quarter of 2024 and nothing since
- **THEN** its mean per year is 16, it has no coverage, and its level is dormant

### Requirement: Item page
`/lab/inventory/items/<id>/` SHALL show the article number and name as heading, or the name alone for an item without an article number, followed by the mark `neu` for a new item; the substance, linking to its page; the category, size and note; the `status` when it is not `active`; the `stocked_on`, `–` when there is none; the compartment and the box, `–` for each that is not set; the quantity with its level; the means and coverage; the current year's consumption; a chart of the consumption of each quarter of the two complete years before the current one and of the current year, an inline `svg` with one bar per quarter titled with the quarter and its value and, when the item has a mean, a line at the mean per quarter, followed by a table of each quarter's entered value, deliveries and total, in which a signed-in user sees beside each quarter's entered value a link to the consumption form for that quarter (Inventory forms), `Ändern` (`Change`) where the quarter has an entered value and `Nachtragen` (`Enter`) where it has none, except on the page of an item without an article number, beside a quarter that has not begun, and beside a quarter that holds lines of a historical note that is not reversed (Consumption), and each such link opens its form in a dialog over the page (web-app "Form dialogs"); the movements in booking order, newest first, with date, booking time, kind, count, quantity after, the user's initials, the delivery note with its number and recipient, the note, and the mark `storniert` (`reversed`) on a reversed movement; the open lots of its substance with the number of containers they would fill; under `Prognose` (`Forecast`), the item's forecast, as `production-planning` states under Item forecast; and the change history, which includes that of the item's entered consumption: each entry, change and removal of a quarter's value, headed `Verbrauch Q<quarter> <year>` (`Consumption Q<quarter> <year>`), with the old and new count. A signed-in user sees the links `Abgabe buchen` (`Book delivery`), to the new delivery note with the item in its first line, `Abfüllen` (`Fill`), `Bestand korrigieren` (`Correct count`), `Verbrauch nachtragen` (`Enter consumption`), `Bearbeiten` (`Edit`), and `Stornieren` (`Reverse`) beside each delivery and filling not yet reversed; for an item without an article number, `Artikelnr. eintragen` (`Enter article number`), to its edit form, takes the place of `Abgabe buchen`, and `Verbrauch nachtragen` is left out. An unknown id answers 404.

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
- **WHEN** a signed-in user requests the page of an item with an article number that has the entered value 40 for the third quarter of 2026, no value for its second quarter, and a historical note with a line of the item dated in its first quarter
- **THEN** the third quarter's row links `Ändern` to `/lab/inventory/items/<id>/consumption/?year=2026&quarter=3`, the second quarter's links `Nachtragen` to the same form for that quarter, the first quarter's has no such link, and each link opens in a dialog

#### Scenario: History of entered consumption
- **WHEN** user `KL` enters 400 for the third quarter of 2026 of an item, then 40 for the same quarter, then removes it, and a test client requests the item's page
- **THEN** its history holds, newest first, an entry headed `Verbrauch Q3 2026` removing the value 40, one changing the count from 400 to 40, and one entering 400, each naming `KL`

### Requirement: Inventory forms
For a signed-in user, the application SHALL offer:

- `/lab/inventory/end-products/new/`: a new item with its opening count, its substance by key, the article number, optional, and the category with a `datalist` of the categories in use, the `stocked_on`, optional, left empty for the opening count to set, and the compartment and the box, each with a `datalist` of the values in use;
- `/lab/inventory/items/<id>/edit/`: the item's note, `status`, `stocked_on`, compartment and box, the last two each with a `datalist` of the values in use, and its article's category and, while the article has none, its article number, both saved on the article for every size of it, as the form says beside them;
- `/lab/inventory/deliveries/new/`: a delivery note with ten rows for lines, each offering the items with an article number, each shown as its article number, container and name and, where they are set, `Fach <compartment>` and `Box <box>` (`Compartment <compartment>`, `Box <box>`), joined by ` · ` and the locations by ` / `, rows left empty being ignored, and a check box `nachgetragen – Bestand bleibt unverändert` (`entered later – stock unchanged`) for a historical note; `?item=<id>`, given once or several times, puts those items in the first rows in the order given, up to ten, leaving out ids of items it does not offer and ids given twice;
- `/lab/inventory/deliveries/<id>/reverse/`: marking a historical note reversed, with its note;
- `/lab/inventory/items/<id>/fill/` and `/correct/`: a movement;
- `/lab/inventory/items/<id>/movements/<movement id>/reverse/`: the reversal of a delivery or filling, with its note;
- `/lab/inventory/items/<id>/consumption/`: the entered value of a year and quarter, replacing an earlier one of that quarter, or removing it when left empty; `?year=<year>&quarter=<quarter>` chooses that quarter and fills in its entered value, and the form then names the value a save replaces; beside its fields the form shows the item's consumption as the item page does, its chart and its table of quarters with their links, a link choosing its quarter in the form;
- `/lab/inventory/deliveries/<id>/edit/`: a note's number, recipient and note;
- `/lab/inventory/bulk/new/`: a new lot with its opening amount, its substance by key, its source, `hergestellt` when none is chosen, and its supplier, and the location with a `datalist` of the locations in use; `?substance=<key>`, `?batch=<batch>` and `?made_on=<date>` fill in those fields, and `?step=<id>` makes the lot one made by that task step, filling in the first product of the step's entry, or the task's substance for a step without one, its task's batch when the substance is the task's, and today, and refusing a substance the step does not make;
- `/lab/inventory/bulk/<id>/withdraw/`: a withdrawal from an open lot into a step of a task that is planned or running, chosen among those tasks' steps or given as `?step=<id>`, with the amount in the lot's unit and the date; an amount above the lot's is refused;
- `/lab/inventory/bulk/movements/<id>/reverse/`, a POST: reverses a withdrawal not yet reversed;
- `/lab/inventory/bulk/<id>/edit/`, for the batch, location, date and note, refusing at the batch a change that would leave an ended task that has neither failed nor been cancelled without its product lot (task-tracker "Task record"), and `/correct/`.

A substance is named by its key, offered through a `datalist` of every substance's key labelled with its name; an unknown key is an error at the field. On the new-item form, the article number and the category make the substance's article when it has none, an empty number giving it none. When the substance has an article, a field left empty leaves the article's value as it is; a category entered replaces the article's; an article number entered gives the article that number when it has none, as the edit form does, and must otherwise be its number, or the form shows an error at it. On the edit form, the category field holds the article's category and saves what it holds, empty included, and the article number, offered only while the article has none, gives it one when entered and leaves it without one when empty. Invalid input shows the form again with the errors beside their fields and saves nothing. A saved form leads, with a message naming the record, to the page of the delivery note for the forms of notes, and to the page of the item or lot for every other; a form saved in a dialog leaves the page it was opened from in place instead. On an item's page and in the item list's details, the links to the item's edit form, its filling, its count correction and its consumption, and on its page each link `Stornieren` beside a movement, open those forms in a dialog over the page (web-app "Form dialogs"); `Abgabe buchen` leads to the new delivery note's form page.

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

#### Scenario: New lot from the query
- **WHEN** a signed-in user requests `/lab/inventory/bulk/new/?substance=cinnamic-acid&batch=B-2026-031&made_on=2026-10-30`
- **THEN** the form holds the substance `cinnamic-acid`, the source `hergestellt`, the batch `B-2026-031` and the date 2026-10-30

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
- **THEN** the form holds the year 2026, the quarter 3 and the count 400, names 400 as the value a save replaces, and shows the item's chart and its table of quarters, the third quarter's row linking `Ändern` to the form for that quarter
