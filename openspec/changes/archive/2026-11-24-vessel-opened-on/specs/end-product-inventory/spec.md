## MODIFIED Requirements

### Requirement: Vessels
The `inventory` package SHALL keep vessels (`Gefäße`), each a weighed amount of one batch in one place, with a change history: `batch`; `unit`, one of `mg`, `g`, `umol` and `mmol`, in which the vessel is entered and shown; `amount`, at least zero, kept in the vessel's base unit, `mg` for `mg` and `g` and `µmol` for `µmol` and `mmol`, with six decimal places; `flask` (`Kolben`, `Flask`), whether it is its batch's reaction flask; `location` (`Ort`, `Location`), optional, at most 100 characters; `opened_on` (`Angebrochen am`, `Opened on`), for a vessel of a bought batch, the day it was first opened, or none while it is sealed (`versiegelt`, `sealed`), never after today, and none for a vessel of a made batch; and `note`. The batch, unit and `flask` are fixed once the vessel exists. A vessel's substance is its batch's, and a vessel belongs to every item of its substance's article, when the substance has one. Its amount shows in its unit to three decimal places, rounded half up. A vessel at zero is used up, and one above zero is open. A vessel of a bought batch opens sealed, unless a transfer makes it: a vessel a transfer makes is opened on the transfer's date. The first filling, withdrawal or transfer out of a sealed vessel sets its `opened_on` to that movement's date in the transaction that books it; a correction, and the reversal of the movement, leave it as it is. A vessel shows as its batch followed by `#<id>`.

A flask is made only by recording a batch from a task step with its yield and without a location (Inventory forms), and a batch has at most one; every other vessel is stored. A vessel's kind (`Art`, `Kind`) is `Kolben` (`Flask`) for a flask; for a stored vessel it is `Endprodukt` (`End product`) when its substance has an article, else `Zwischenprodukt` (`Intermediate`) when its batch is made and `Reagenz` (`Reagent`) when it is bought.

Its amount changes only by its movements, each holding `kind`, `amount`, `amount_after`, `date`, `booked_at`, `user`, `note`, and `task_step`, `transfer` and `reverses` where they apply, by one atomic conditional update in the transaction that stores the movement, as for items:

- `opening` (`Anfangsmenge`, `Opening amount`), the amount the vessel opens with: its batch's yield, or an amount entered;
- `filling` (`Abfüllung`, `Filling`), the amount taken into an item's containers, more than zero and at most the vessel's amount;
- `withdrawal` (`Entnahme`, `Withdrawal`), the amount taken into a task step, named by `task_step`, more than zero and at most the vessel's amount;
- `transfer_out` (`Umfüllung (Abgang)`, `Transfer out`) and `transfer_in` (`Umfüllung (Zugang)`, `Transfer in`), an amount passed from one vessel to another of the same batch, more than zero and at most the source's amount, booked together, the `transfer_in` naming the `transfer_out` as `transfer`; the target is a stored vessel, or a new stored vessel in the source's unit, whose first movement the `transfer_in` is; the `transfer_out` holds the amount in the source's base unit and the `transfer_in` that amount converted into the target's, rounded half up to six places, a transfer whose converted amount rounds to zero being refused whole, units converting as for a filling (Filling from bulk), and a transfer between a mass and an amount of substance is refused when the substance has no molar mass;
- `correction` (`Korrektur`, `Correction`), the amount weighed, with a required note;
- `remainder` (`Restausbuchung`, `Remainder written off`), a flask's whole amount, booked when the task of its batch's step ends, fails or is cancelled (task-tracker "Task record");
- `reversal` (`Storno`, `Reversal`), the amount a reversed filling or withdrawal returns, the withdrawal named by `reverses`, each withdrawal reversed at most once.

A flask whose task is ended, failed or cancelled stays at zero: a correction of it, and the reversal of a filling or withdrawal from it, are refused. Recording a batch from a step and every booking on a flask check the task's state in the transaction that books, so that one prepared while the task was open and stored after it closed is refused and changes nothing; on PostgreSQL this holds for bookings and closures that overlap. Vessel movements are never edited or deleted, except that deleting a vessel in the admin deletes its opening movement with it, and `demo_data --replace` deletes every vessel with its movements.

#### Scenario: Yield into the flask
- **WHEN** a signed-in user records from the last step of a running task of `cinnamic-acid` a batch `KL0412` with the amount `2` g and no location
- **THEN** the batch's yield is `2` g, and its one vessel is a flask holding `2` g whose only movement is the opening

#### Scenario: Yield stored at once
- **WHEN** a signed-in user records the same batch with the location `Kühlschrank 2`
- **THEN** its one vessel is stored in `Kühlschrank 2`, of the kind `Endprodukt`, holding `2` g, and the batch has no flask

#### Scenario: Transfer into a new vessel
- **WHEN** the flask of `KL0412` holds `2` g and a signed-in user transfers `1,5` g from it into a new vessel in `Kühlschrank 2`
- **THEN** the flask holds `0,5` g and the new vessel `1,5` g, whose only movement is a `transfer_in` naming the flask's `transfer_out`

#### Scenario: Transfer across units
- **WHEN** a batch of `cinnamic-acid`, whose molar mass is 148.16, has a flask in `mg` holding `1000` mg and a stored vessel in `µmol` holding `100` µmol, and a signed-in user transfers `148,16`, in the flask's unit, from the flask into that vessel
- **THEN** the flask holds `851,84` mg and the vessel `1100` µmol

#### Scenario: Transfer without a molar mass
- **WHEN** a batch of a substance without a molar mass has a flask in `mg` and a stored vessel in `µmol`, and a signed-in user posts a transfer from the flask into that vessel
- **THEN** the form shows an error at the target and neither vessel changes

#### Scenario: A closed task's flask stays empty
- **WHEN** 5 containers of an item were filled from the flask of a batch whose task has since ended, and a signed-in user reverses that filling, and then corrects the flask to `1` g with a note
- **THEN** both are refused with an error, the item keeps its containers and the flask holds nothing

#### Scenario: Correction of a vessel
- **WHEN** a signed-in user corrects a vessel of `50` mg to `47,5` mg with the note `nachgewogen`
- **THEN** the vessel holds `47,5` mg and its newest movement is that correction

#### Scenario: Withdrawal and its reversal
- **WHEN** a signed-in user withdraws `500` mg of a vessel holding `2` g into a step of a running task, and then reverses the withdrawal
- **THEN** the vessel holds `1,5` g after the withdrawal and `2` g after the reversal, the withdrawal names the step, the reversal names the withdrawal, and reversing it again is refused

#### Scenario: Kinds of vessels
- **WHEN** the database holds the flask of a made batch of `cinnamic-acid`, a stored vessel of the same batch, a stored vessel of a made batch of `acetophenone`, which has no article, and one of a bought batch of `acetophenone`
- **THEN** their kinds are `Kolben`, `Endprodukt`, `Zwischenprodukt` and `Reagenz`

#### Scenario: A bought bottle is opened by its first withdrawal
- **WHEN** a signed-in user records a batch of `acetophenone` bought from `Sigma` with `100` g in `Chemikalienschrank 1`, then on 2026-11-20 withdraws `5` g of its vessel into a step of a running task, and on 2026-11-22 another `5` g
- **THEN** the vessel was sealed after the receipt and has the `opened_on` 2026-11-20 after both withdrawals

#### Scenario: A made vessel is never sealed
- **WHEN** a signed-in user posts the edit form of a stored vessel of a made batch with the `opened_on` 2026-11-20
- **THEN** the vessel keeps no `opened_on`

### Requirement: Inventory forms
For a signed-in user, the application SHALL offer:

- `/lab/inventory/end-products/new/`: a new item with its opening count and the batch it is of, optional, chosen among the batches of every substance, grouped under their substance's name as on a delivery note's row, none standing for unknown batch; its substance by key; the article number, optional, and the category with a `datalist` of the categories in use, the `stocked_on`, optional, left empty for the opening count to set, and the compartment and the box, each with a `datalist` of the values in use;
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

### Requirement: Vessel list
`/lab/inventory/vessels/` SHALL list the open vessels, of every substance, with the columns `Gefäß`, `Name`, `Artikelnr.`, `Art`, `Charge`, `Herkunft`, `Menge`, `Ort`, `Datum`, `Angebrochen` and `Bemerkung` (`Vessel`, `Name`, `Article no.`, `Kind`, `Batch`, `Source`, `Amount`, `Location`, `Date`, `Opened`, `Note`): `#<id>`, linking to the vessel's page; its substance's name, linking to the substance's page; the article number of the substance's article, empty when there is none; its kind; its batch, linking to the batch's page; the batch's source as the batch list shows it; its amount; its location; its batch's date; for a vessel of a bought batch its `opened_on` or `versiegelt` (`sealed`), and nothing for one of a made batch; and its note. The vessels are ordered by name regardless of case, then by their batch's date, oldest first and vessels without one last, then by id. `empty=1` adds the used-up vessels. `kind=<kind>`, one of `flask`, `end-product`, `intermediate` and `reagent`, lists the vessels of that kind; another value lists every kind. The page offers each kind and shows the one in force. A signed-in user sees a link `Neue Charge` (`New batch`).

#### Scenario: Used-up vessels
- **WHEN** the database holds an open vessel and a used-up vessel, and a test client requests the vessel list with and without `empty=1`
- **THEN** it lists both with it and only the open vessel without

#### Scenario: Vessels by kind
- **WHEN** the database holds an open flask of a made batch of `cinnamic-acid`, an open vessel of a made batch of `acetophenone`, which has no article, and one of a batch of `acetophenone` bought from `Sigma`, and a test client requests the vessel list, and then with `kind=reagent`
- **THEN** the first lists the three with the kinds `Kolben`, `Zwischenprodukt` and `Reagenz`, the first with `CH-0012` and the others with an empty article number, the last with `gekauft · Sigma`; the second lists the bought vessel alone

### Requirement: Vessel page
`/lab/inventory/vessels/<id>/` SHALL show the vessel as heading; its batch, linking to its page; its substance, linking to its page, and the article number of the substance's article when there is one; its kind, amount, location and note, for a vessel of a bought batch `Angebrochen am <date>` (`Opened on <date>`) or `versiegelt` (`sealed`), and the mark `aufgebraucht` (`used up`) at zero; its movements in booking order, newest first, with date, booking time, kind, amount, amount after, the user's initials, note and, for a filling, the item filled, for a withdrawal, the task and step it went into, linking to the task, for a transfer, the other vessel, linking to its page, and for a reversal the movement it reverses; and its change history. A signed-in user sees the links `Korrigieren` (`Correct`), `Bearbeiten` (`Edit`) and, on an open vessel, `Entnahme` (`Withdraw`) and `Umfüllen` (`Transfer`), and beside each withdrawal not yet reversed a button `Stornieren` (`Reverse`). An unknown id answers 404.

#### Scenario: Vessel page after a filling
- **WHEN** a test client requests the page of a vessel from which 5 containers of an item were filled
- **THEN** its newest movement is that filling, linking to the item

#### Scenario: Vessel page after a transfer
- **WHEN** a test client requests the page of a flask from which an amount was transferred into a new vessel
- **THEN** its newest movement is the `transfer_out`, linking to the new vessel's page
