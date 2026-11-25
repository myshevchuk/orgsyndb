## ADDED Requirements
### Requirement: End product layers
The item list, the bulk list and the delivery list SHALL be the three layers of the end products, `Gebinde` (`Containers`), `Bulk` (`Bulk`) and `Lieferungen` (`Deliveries`), in this order: each has the heading `Endprodukte` (`End products`) and offers the three layers as links, to `/lab/inventory/end-products/`, `/lab/inventory/end-products/bulk/` and `/lab/inventory/deliveries/`, each with its count, the number of all items, of the vessels the bulk list lists without filters and of all delivery notes, and marks its own as current. In the section tabs, `Endprodukte` is current on all three.

#### Scenario: Three layers
- **WHEN** the database holds 2 items, one open vessel of their substance and 3 delivery notes, and a test client requests the bulk list
- **THEN** its heading is `Endprodukte`, it offers `Gebinde` with 2, `Bulk` with 1 and `Lieferungen` with 3, marks `Bulk` as current, and the section tab `Endprodukte` is current

### Requirement: Bulk list
`/lab/inventory/end-products/bulk/` SHALL list the open vessels of every substance that has an article, flasks and vessels of bought batches among them, with the columns `Artikel`, `Gefäß`, `Charge`, `Herkunft`, `Menge`, `Ort`, `Datum` and `Reicht für` (`Article`, `Vessel`, `Batch`, `Source`, `Amount`, `Location`, `Date`, `Fills`): the article number, `ohne Nr.` (`no number`) for an article without one, and the substance's name, linking to the substance's page; `#<id>`, linking to the vessel's page; the batch, linking to its page; the batch's source as the batch list shows it; the amount; the location, or `Kolben` (`Flask`) for a flask; the batch's date; and, for each item of the article, by size, the number of its containers the vessel would fill as Filling from bulk counts it, shown as `<number> × <size>` and joined by `oder` (`or`), or `Molmasse fehlt` (`Molar mass missing`) for an item the vessel does not convert into. For a signed-in user each such alternative links to that item's filling form with the vessel chosen. The vessels are ordered by article number, articles without one last and by name regardless of case, then by their batch's date, oldest first and vessels without one last, then by id.

GET parameters select the vessels listed and keep their values: `q` those in whose article number, or in whose substance's key, name or German name, or batch number or supplier's batch, the text is found regardless of case; `location` those at that location; `source`, `made` or `bought`, those of batches of that source; and `flask=1` the flasks alone. The page offers each location in use. The list shows its vessels in the views `Tabelle` and `Details`, remembered in the cookie `bulk-list-view`, with one vessel selected by `selected=<id>`, as the item list does with its items. The details view shows beside the table the selected vessel: its batch, source, amount, location, the containers it would fill, and its five newest movements as the vessel page shows them, with a link to the vessel's page. A signed-in user sees a link `Neue Charge` (`New batch`).

#### Scenario: Vessels of end products
- **WHEN** the database holds an item `CH-0012` of 100 mg and one of 1 g of `cinnamic-acid`, whose substance has the molar mass 148.16, a stored vessel of a made batch of it holding `2,5` g, its task's flask holding `4` g, a vessel of a bought batch of it holding `50` g, and a vessel of a made batch of `acetophenone`, which has no article, and a test client requests the bulk list
- **THEN** it lists the three vessels of `cinnamic-acid` and not the vessel of `acetophenone`, the flask with `Kolben`, the bought vessel with `gekauft`, and the stored vessel with `25 × 100 mg oder 2 × 1 g`

#### Scenario: A vessel that does not convert
- **WHEN** an item of 10 µmol of a substance without a molar mass has an open vessel of `600` mg
- **THEN** the bulk list shows `Molmasse fehlt` for that item in the vessel's row

#### Scenario: Filling from the bulk list
- **WHEN** a signed-in user requests the bulk list holding a vessel of `cinnamic-acid` and follows the alternative of its item of 100 mg
- **THEN** the filling form of that item opens with that vessel chosen

#### Scenario: Flasks alone
- **WHEN** the bulk list holds a flask and a stored vessel, and a test client requests it with `flask=1`
- **THEN** it lists the flask alone

## MODIFIED Requirements

### Requirement: Delivery list
`/lab/inventory/deliveries/` SHALL list the delivery notes, under the heading `Endprodukte` (End product layers), newest date first, then newest booking first, each with its number linking to its page, date, recipient, the mark `nachgetragen` (`entered later`) on a historical note and `storniert` (`reversed`) on a reversed one, and its lines with article number, name, size, batch and count; a current note shows `storniert` when all its lines are reversed and `teilweise storniert` (`partly reversed`) when some are. GET parameters filter it and keep their values: `q`, text found regardless of case in the number or recipient, and `item`, an item's id. The list shows its notes in the views `Tabelle` and `Details`, remembered in the cookie `delivery-list-view`, with one note selected by `selected=<id>`, as the item list does with its items: the table view shows each note with its lines; the details view shows beside a table of each note's number, date, recipient, number of lines and a short summary of them the selected note as its page shows it, with its marks, lines and a link to its page. `/lab/inventory/deliveries/<id>/` shows one note with its lines, each with the article number, name, size, batch, linking to its page, compartment, box and count, their movements and the change history, and an unknown id answers 404. A signed-in user sees a link `Neuer Lieferschein` (`New delivery note`).

#### Scenario: Deliveries of one item
- **WHEN** two notes have lines of an item and a third does not, and a test client requests the list with that item's id
- **THEN** it lists the two notes, the newer first

#### Scenario: A pick list
- **WHEN** a note has a line of an item kept in compartment `2`, box `7`, and a test client requests the note's page
- **THEN** the line shows `2` and `7` in the columns `Fach` and `Box`

#### Scenario: Lines name their batch
- **WHEN** a note has a line of 2 containers of the batch `KL0412`, and a test client requests the note's page and the delivery list
- **THEN** both show `KL0412` in that line, linking on the note's page to the batch's page

#### Scenario: A note in the details view
- **WHEN** a note `LS-2026-156` has lines of `CH-0013` and `CH-0016`, and a test client with the cookie `delivery-list-view` set to `details` requests the delivery list with `selected` naming it
- **THEN** the details show `LS-2026-156`, both lines with their batches and counts, and a link to the note's page

### Requirement: Batch list
`/lab/inventory/batches/` SHALL list the batches, of every substance, with the columns `Charge`, `Name`, `Artikelnr.`, `Herkunft`, `Laborjournal`, `Datum`, `Ausbeute` and `Bestand` (`Batch`, `Name`, `Article no.`, `Source`, `Lab notebook`, `Date`, `Yield`, `Stock`): the batch as it shows, linking to its page; its substance's name, linking to the substance's page; the article number of the substance's article, empty when there is none; the source, `hergestellt` followed for a batch made by a step by its task's number linking to the task's page, or `gekauft` followed by the supplier when there is one; the journal entry, linking to its notebook's page; the date; the yield; and the amount in its open vessels by unit, `–` when it has none. The batches are ordered by date, newest first and batches without one last, then newest first. The GET parameter `q` lists the batches in whose number, supplier's batch number or supplier, or in whose substance's key, name or German name, the text is found regardless of case; the form keeps its value. The item list, the bulk list, the delivery list, the batch list and the vessel list carry section tabs `Endprodukte`, `Chargen` and `Alle Gefäße` (`End products`, `Batches`, `All vessels`), linking to `/lab/inventory/end-products/`, `/lab/inventory/batches/` and `/lab/inventory/vessels/`, in the site's `nav.section-tabs` markup. A signed-in user sees a link `Neue Charge` (`New batch`).

#### Scenario: Batches of either source
- **WHEN** the database holds a made batch `KL0412` of `cinnamic-acid` dated 2026-10-30, made by a step of task `T-007` and naming the journal entry `AE-1/9`, with an open vessel of `2` g, and a batch of `acetophenone` bought from `Sigma` dated 2026-11-02 without vessels, and a test client requests the batch list
- **THEN** it lists the bought batch first, with an empty article number, `gekauft · Sigma` and `–`, and then `KL0412` with `CH-0012`, `hergestellt · T-007` linking to the task's page, `AE-1/9` linking to `/lab/journal/AE-1/` and `2 g`

#### Scenario: Searching batches
- **WHEN** the same database is listed with `q=kl04` and with `q=sigma`
- **THEN** the first lists `KL0412` alone and the second the bought batch alone

### Requirement: Inventory forms
For a signed-in user, the application SHALL offer:

- `/lab/inventory/end-products/new/`: a new item with its opening count and the batch it is of, optional, chosen among the batches of every substance, grouped under their substance's name as on a delivery note's row, none standing for unknown batch; its substance by key; the article number, optional, and the category with a `datalist` of the categories in use, the `stocked_on`, optional, left empty for the opening count to set, and the compartment and the box, each with a `datalist` of the values in use;
- `/lab/inventory/items/<id>/edit/`: the item's note, `status`, `stocked_on`, compartment and box, the last two each with a `datalist` of the values in use, and its article's category and, while the article has none, its article number, both saved on the article for every size of it, as the form says beside them;
- `/lab/inventory/deliveries/new/`: a delivery note with ten rows for lines, each offering the items with an article number, each shown as its article number, container and name and, where they are set, `Fach <compartment>` and `Box <box>` (`Compartment <compartment>`, `Box <box>`), joined by ` · ` and the locations by ` / `, and the batches of the substances of the items it offers, grouped under their substance's name, each shown as the batch shows; a row with only some of item, batch and count is refused at the field missing, and rows left empty are ignored; and a check box `nachgetragen – Bestand bleibt unverändert` (`entered later – stock unchanged`) for a historical note; `?item=<id>`, given once or several times, puts those items in the first rows in the order given, up to ten, leaving out ids of items it does not offer and ids given twice;
- `/lab/inventory/deliveries/<id>/reverse/`: marking a historical note reversed, with its note;
- `/lab/inventory/items/<id>/fill/`: a filling, its vessel chosen among the open vessels of the item's substance, or given as `?vessel=<id>`, which chooses that vessel when the form offers it, each offered as the vessel, its kind, its location where it has one, and its amount, joined by ` · `; and `/lab/inventory/items/<id>/correct/`: a correction of one share, chosen among the batches of the item's substance, each with the item's containers of it, and `unbekannt` (`unknown`) with its containers of unknown batch, the default;
- `/lab/inventory/items/<id>/movements/<movement id>/reverse/`: the reversal of a delivery or filling, with its note;
- `/lab/inventory/items/<id>/consumption/`: the entered value of a year and quarter, replacing an earlier one of that quarter, or removing it when left empty; `?year=<year>&quarter=<quarter>`, naming a quarter that has begun, fixes the form to that quarter, which it names in place of the fields for the year and the quarter, and fills in its entered value, zero included, naming it as the value a save replaces, or leaves the count empty where the quarter has none; other values of the two parameters are ignored, and the form opens as without them; beside its fields the form shows the item's consumption as the item page does, its chart and its table of quarters with their links, a link choosing its quarter in the form;
- `/lab/inventory/deliveries/<id>/edit/`: a note's number, recipient and note;
- `/lab/inventory/batches/new/`: a new batch with its substance by key; its source, `hergestellt` when none is chosen; for a made batch its number and its journal entry, given as `<code>/<number>` as a task step names one (task-tracker "Task page"); for a bought batch its supplier, the supplier's article number and the supplier's batch; its date, today by default; its note; and an amount, its unit and a location, with a `datalist` of the locations in use, that open the batch's first vessel, a stored one, when the amount is given. `?substance=<key>` fills in the substance. `?step=<id>` records a batch made by that task step: the source is `hergestellt`, the substance is filled in with the first product of the step's entry, or the task's substance for a step without one, and a substance the step does not make is refused; the journal entry is the step's, shown and not editable, when the step names one; and the amount is required and is the batch's yield, opening a flask when no location is given and a stored vessel at the location given. A step whose task is neither planned nor running, a number another made batch has regardless of case, a number on a bought batch, an amount without its unit, and a journal entry whose code is no notebook's are refused;
- `/lab/inventory/batches/<id>/edit/`: the number, journal entry and yield of a made batch, the supplier, supplier's article number and supplier's batch of a bought one, and the date and note;
- `/lab/inventory/batches/<id>/vessels/new/`: a new stored vessel of the batch with its opening amount, its unit, its location, with the `datalist` of the locations in use, and its note;
- `/lab/inventory/vessels/<id>/withdraw/`: a withdrawal from an open vessel into a step of a task that is planned or running, chosen among those tasks' steps or given as `?step=<id>`, with the amount in the vessel's unit and the date; an amount above the vessel's is refused;
- `/lab/inventory/vessels/<id>/transfer/`: a transfer from an open vessel, with the amount in the source vessel's unit, the date and a note, into a stored vessel of the same batch, chosen among them, or into a new vessel at the location given; an amount above the vessel's, and a target whose unit converts from the source's only through a molar mass the substance lacks, are refused, the latter with an error at the target;
- `/lab/inventory/vessels/movements/<id>/reverse/`, a POST: reverses a withdrawal not yet reversed;
- `/lab/inventory/vessels/<id>/edit/`, for the location and note and, for a vessel of a bought batch, its `opened_on`, which may be emptied to mark it sealed, and `/lab/inventory/vessels/<id>/correct/`.

A batch of another substance than the item's is refused at the batch, on the new-item form and in a delivery note's row. With the page's script, a delivery note's row offers only the batches of the substance of the item chosen in it, and the new-item form only those of the substance entered, and a batch chosen that is no longer offered is cleared; without the script, every batch stays offered. A substance is named by its key, offered through a `datalist` of every substance's key labelled with its name; an unknown key is an error at the field. On the new-item form, the article number and the category make the substance's article when it has none, an empty number giving it none. When the substance has an article, a field left empty leaves the article's value as it is; a category entered replaces the article's; an article number entered gives the article that number when it has none, as the edit form does, and must otherwise be its number, or the form shows an error at it. On the edit form, the category field holds the article's category and saves what it holds, empty included, and the article number, offered only while the article has none, gives it one when entered and leaves it without one when empty. Invalid input shows the form again with the errors beside their fields and saves nothing. A saved form leads, with a message naming the record, to the page of the delivery note for the forms of notes, to the page of the batch for the new-batch form, and to the page of the item, batch or vessel for every other; a form saved in a dialog leaves the page it was opened from in place instead. On an item's page and in the item list's details, the links to the item's edit form, its filling, its count correction and its consumption, and on its page each link `Stornieren` beside a movement, open those forms in a dialog over the page (web-app "Form dialogs"); `Abgabe buchen` leads to the new delivery note's form page.

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

#### Scenario: Batches narrowed to the item
- **WHEN** a signed-in user's browser runs the page's script on the new delivery note form, and the user chooses in a row an item of `cinnamic-acid` after choosing a batch of `acetophenone`
- **THEN** the row's batch choice offers the batches of `cinnamic-acid` alone, and no batch is chosen

#### Scenario: A row needs its batch
- **WHEN** a signed-in user posts a delivery note with a row holding an item and a count and no batch
- **THEN** the form shows an error at that row's batch and nothing is saved

#### Scenario: Shares offered for a correction
- **WHEN** an item holds 3 containers of `KL0412` and 2 of unknown batch, its substance has the batch `KL0413` too, and a signed-in user requests its correction form
- **THEN** it offers `unbekannt` with 2, chosen, `KL0412` with 3 and `KL0413` with 0

#### Scenario: Opening date entered and cleared
- **WHEN** on 2026-11-24 a signed-in user posts the edit form of a sealed vessel of a bought batch with the `opened_on` 2026-11-10, then with 2026-11-25, then with the field empty
- **THEN** the vessel has the `opened_on` 2026-11-10 after the first, the form shows an error at the field and the vessel keeps 2026-11-10 after the second, and the vessel is sealed after the third
