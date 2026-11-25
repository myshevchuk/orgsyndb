## ADDED Requirements

### Requirement: Stock categories
Every open vessel SHALL belong to one stock category, from two facts alone, whether its substance has an article and whether its batch is made or bought: `Endprodukte` (`End products`) when its substance has an article; else `Zwischenprodukte` (`Intermediates`) when its batch is made; else `Handelschemikalien` (`Commercial chemicals`). A flask belongs to the category of its batch like any other vessel. A substance can have vessels in more than one category; giving it an article moves all its vessels to `Endprodukte`.

#### Scenario: Categories of vessels
- **WHEN** the database holds a stored vessel and the flask of made batches of `cinnamic-acid`, which has an article, the flask of a made batch of `acetophenone`, which has none, a stored vessel of another made batch of `acetophenone` and a vessel of a bought batch of `acetophenone`
- **THEN** the two vessels of `cinnamic-acid` are `Endprodukte`, the flask and the stored made vessel of `acetophenone` `Zwischenprodukte`, and the bought one `Handelschemikalien`

### Requirement: Lists by substance
`/lab/inventory/intermediates/` and `/lab/inventory/chemicals/` SHALL list the substances that have an open vessel of the category `Zwischenprodukte` and of `Handelschemikalien` respectively (Stock categories), one row per substance, under the headings `Zwischenprodukte` (`Intermediates`) and `Handelschemikalien` (`Commercial chemicals`), each followed by the number of substances and of vessels listed, and ordered by the substance's name regardless of case. A signed-in user sees a link `Neue Charge` (`New batch`) to `/lab/inventory/batches/new/` on the intermediate list and `Wareneingang` (`Goods receipt`) to `/lab/inventory/batches/new/?source=bought` on the commercial chemical list.

A row's cells describe the substance's open vessels of the list's category that the filters admit, its vessels for short. Locations are ordered as the item list orders compartments, numbers in them by value; other texts regardless of case.

- `Substanz` (`Substance`): the substance's name, linking to its page, followed on the intermediate list by its chemical classes, by label, and on the commercial chemical list by its short name and CAS number where it has them; and the mark `+gekauft` (`+bought`) on the intermediate list, `+hergestellt` (`+made`) on the commercial chemical list, when the substance has an open vessel of the other of the two categories, whatever the filters;
- `Menge` (`Amount`): the amount in its vessels summed per unit, the units in the order `mg`, `g`, `µmol`, `mmol`;
- `Gefäße` (`Vessels`): their number, followed on the intermediate list by `<n> Kolben` (`<n> in flask`) when flasks are among them, and on the commercial chemical list by `(<n> versiegelt)` (`(<n> sealed)`) when sealed vessels are among them;
- `Ort` (`Location`): from the stored vessels, the location they all share, else the first followed by `+<n>`, the number of other locations, a stored vessel without a location counting as the location `nicht hinterlegt` (`not recorded`), placed last; then, on the intermediate list, `im Kolben` (`in flask`) when flasks are among them, alone when all are flasks; a flask's own location is not shown;
- on the intermediate list, `Herkunft` (`Source`): the numbers of the tasks whose steps made the batches, linking to the tasks' pages, in the order of the tasks' numbers by value, at most two followed by `+<n>`, then `ohne Auftrag` (`no task`) when a batch was made by no step, alone when none was; and `Alter` (`Age`): the age of the newest and of the oldest batch date among its vessels, joined by ` – `, or one when the two read alike, `–` when no batch has a date, and marked as old, in a `span.age-old`, when the oldest age is a year or more;
- on the commercial chemical list, `Gruppe` (`Group`): the substance's inventory group; `Lieferanten` (`Suppliers`): the suppliers of the batches, `unbekannt` (`unknown`) for a batch without one, the first followed by `+<n>`, the number of the others; and `Angebrochen` (`Opened`): the earliest `opened_on` among its vessels, or `versiegelt` (`sealed`) when all are sealed.

An age runs from a batch's date to today in whole calendar months, a month being complete on the same day of the month, or on a shorter month's last day: `heute` (`today`) for today, `1 Tag` (`1 day`) and `<n> Tage` (`<n> days`) below one month, `<n> Mon.` (`<n> mo.`) below twelve months, and `<y> J` (`<y> y`) or `<y> J <m> Mon.` (`<y> y <m> mo.`) from twelve months.

GET parameters filter the list and keep their values; a filter on vessels admits vessels, and a row is listed while it has at least one vessel the filters admit:

- on both lists, `q`: vessels in whose substance's key, name, German name, short name or CAS number, or in whose batch's number, supplier's batch or supplier, the text is found regardless of case, and on the intermediate list also in the number of the task that made the batch; and `location`: stored vessels at that location, flasks never;
- on the intermediate list, `class`: substances filed under the chemical class of that key or under a class filed below it, at any depth; `flask=1`: flasks; and `old=1`: vessels whose batch's age is a year or more;
- on the commercial chemical list, `group`: substances filed under the inventory group of that key or under a group filed below it, at any depth; `supplier`: vessels of batches bought from that supplier; and `sealed=1`: sealed vessels.

A `class` or `group` key that names no term lists none. The page offers each location of the category's open stored vessels and each supplier of its bought batches, and each term of the chemical classes or inventory groups in the order of the vocabulary's page; the value in force is offered even when no vessel has it any more. The list shows its substances in the views `Tabelle` and `Details`, remembered in the cookies `intermediate-list-view` and `chemical-list-view`, with one substance selected by `selected=<key>`, as the item list does with its items.

The details view shows, with the table, the selected substance and its vessels, the same vessels its row describes: its name, linking to its page, and for a signed-in user `Neue Charge` to `/lab/inventory/batches/new/?substance=<key>` on the intermediate list and `Wareneingang` to `/lab/inventory/batches/new/?substance=<key>&source=bought` on the commercial chemical list; and a table of its vessels, ordered by their batch's date, oldest first and vessels without one last, then by id, with the columns `Gefäß`, `Charge`, `Menge`, `Ort`, `Herkunft`, `Datum` and `Bemerkung` (`Vessel`, `Batch`, `Amount`, `Location`, `Source`, `Date`, `Note`), and on the commercial chemical list `Angebrochen am` (`Opened on`) before `Bemerkung`: `#<id>`, linking to the vessel's page; the batch, linking to its page; the amount; the location, `nicht hinterlegt` without one, or `Kolben` (`Flask`) for a flask; for a made batch the task's number linking to its page and the step's label, or `ohne Auftrag` when no step made it, followed by the journal entry linking to its notebook's page where the batch names one, and for a bought batch the supplier and the supplier's article number; the batch's date; the `opened_on` or `versiegelt`; and the vessel's note. For a signed-in user each vessel offers `Entnahme` (`Withdraw`), on an open vessel, `Umfüllen` (`Transfer`), `Korrigieren` (`Correct`) and `Bearbeiten` (`Edit`), which open the vessel's withdrawal, transfer, correction and edit forms in a dialog over the page (web-app "Form dialogs"). When the substance has a single vessel there, the details also show that vessel's five newest movements in booking order, newest first, as its page orders them, with date, kind, amount, amount after, the user's initials and note, and a link to the vessel's page. The list selects only among the substances it lists, so after a save that leaves the selected substance no vessel the filters admit, the first substance listed is selected, and none when the list is empty. Details requested directly for a substance that has open vessels of the category, none of which the filters admit, show `Keine Gefäße` (`No vessels`) in place of the table.

#### Scenario: Intermediates by substance
- **WHEN** `acetophenone`, which has no article, has a flask of a batch made by a step of task `T-021` holding `1` g, a stored vessel of the same batch holding `1,5` g in `Chemikalienschrank 3` and one of a batch made by a step of `T-008` holding `12` g there, and a bought vessel, and a test client requests the intermediate list
- **THEN** it shows one row of `acetophenone` with `14,5 g`, `3` and `1 Kolben`, `Chemikalienschrank 3` and `im Kolben`, `T-008` and `T-021`, and the mark `+gekauft`

#### Scenario: Commercial chemicals by substance
- **WHEN** `benzaldehyde`, which has no article, has a bottle bought from `Sigma-Aldrich` holding `41` g in `Kühlschrank 1`, opened on 2026-03-05, and one bought from `TCI` holding `100` g in `Kühlschrank 2`, sealed, and a test client requests the commercial chemical list
- **THEN** it shows one row of `benzaldehyde` with `141 g`, `2 (1 versiegelt)`, `Kühlschrank 1 +1`, `Sigma-Aldrich +1` and `05.03.2026`

#### Scenario: Filters narrow the sums
- **WHEN** the same database is listed with `supplier=TCI`, and then with `sealed=1`
- **THEN** both show the row of `benzaldehyde` with `100 g`, one vessel, `Kühlschrank 2`, `TCI` and `versiegelt`, and its details list that bottle alone

#### Scenario: Locations not recorded
- **WHEN** a substance has two bought bottles, one in `Regal 10` and one without a location, and another substance a flask alone on the intermediate list
- **THEN** the first row shows `Regal 10 +1`, its details `nicht hinterlegt` for the second bottle, and the second row `im Kolben`

#### Scenario: Containers of the selected substance
- **WHEN** a signed-in user with the cookie `intermediate-list-view` set to `details` requests the intermediate list with `selected=acetophenone`
- **THEN** the details show the three vessels of `acetophenone`, the flask with `Kolben` and `T-021`, each with `Entnahme`, `Umfüllen`, `Korrigieren` and `Bearbeiten` opening in a dialog, and a link `Neue Charge` to `/lab/inventory/batches/new/?substance=acetophenone`

#### Scenario: Booking in a dialog
- **WHEN** a signed-in user opens `Entnahme` of a vessel holding `12` g in the details and books `2` g into a step of a running task
- **THEN** the dialog closes, the row shows the substance's amount `2` g lower and the details show the vessel with `10 g`, the list's selection and view unchanged

#### Scenario: The last admitted bottle opened
- **WHEN** with `sealed=1` the commercial chemical list shows `benzaldehyde` and `toluene`, `benzaldehyde` selected with one sealed bottle, and a signed-in user books a withdrawal from that bottle in its dialog; and then, with `toluene` alone left and selected, books one from its only sealed bottle
- **THEN** after the first save the list shows `toluene` alone, selected, and the address names it; after the second the list shows no substance and the details none

#### Scenario: One bottle with its movements
- **WHEN** a substance has a single bought vessel, from which two withdrawals were booked, and a test client requests the commercial chemical list with `selected` naming it and the cookie `chemical-list-view` set to `details`
- **THEN** the details show that vessel and its opening and two withdrawals, the newest first, with their amounts after

#### Scenario: Ages
- **WHEN** on 2026-11-24 one substance has intermediates of batches dated 2026-11-20 and 2026-04-06, another has one of a batch dated 2025-05-01, and a third one of a batch dated 2025-11-24
- **THEN** the first row's age shows `4 Tage – 7 Mon.` with no `span.age-old`, the second row's `1 J 6 Mon.` and the third row's `1 J`, both in a `span.age-old`, and `old=1` lists the second and third substances alone

#### Scenario: Month ends
- **WHEN** on 2026-02-28 a batch is dated 2026-01-31, and on 2026-02-27 another is dated 2026-01-31
- **THEN** the first shows `1 Mon.` and the second `27 Tage`

#### Scenario: Classes below a class
- **WHEN** `acetophenone` has the chemical class `aryl-ketones`, filed under `ketones`, and a test client requests the intermediate list with `class=ketones`, and with `class=nothing`
- **THEN** the first lists `acetophenone` and the second lists no substance

## MODIFIED Requirements

### Requirement: Batch list
`/lab/inventory/batches/` SHALL list the batches, of every substance, with the columns `Charge`, `Name`, `Artikelnr.`, `Herkunft`, `Laborjournal`, `Datum`, `Ausbeute` and `Bestand` (`Batch`, `Name`, `Article no.`, `Source`, `Lab notebook`, `Date`, `Yield`, `Stock`): the batch as it shows, linking to its page; its substance's name, linking to the substance's page; the article number of the substance's article, empty when there is none; the source, `hergestellt` followed for a batch made by a step by its task's number linking to the task's page, or `gekauft` followed by the supplier when there is one; the journal entry, linking to its notebook's page; the date; the yield; and the amount in its open vessels by unit, `–` when it has none. The batches are ordered by date, newest first and batches without one last, then newest first. The GET parameter `q` lists the batches in whose number, supplier's batch number or supplier, or in whose substance's key, name or German name, the text is found regardless of case; the form keeps its value. The item list, the bulk list, the delivery list, the intermediate list, the commercial chemical list, the batch list and the vessel list carry section tabs `Endprodukte`, `Zwischenprodukte`, `Handelschemikalien`, `Chargen` and `Alle Gefäße` (`End products`, `Intermediates`, `Commercial chemicals`, `Batches`, `All vessels`), linking to `/lab/inventory/end-products/`, `/lab/inventory/intermediates/`, `/lab/inventory/chemicals/`, `/lab/inventory/batches/` and `/lab/inventory/vessels/`, in the site's `nav.section-tabs` markup. A signed-in user sees a link `Neue Charge` (`New batch`).

#### Scenario: Batches of either source
- **WHEN** the database holds a made batch `KL0412` of `cinnamic-acid` dated 2026-10-30, made by a step of task `T-007` and naming the journal entry `AE-1/9`, with an open vessel of `2` g, and a batch of `acetophenone` bought from `Sigma` dated 2026-11-02 without vessels, and a test client requests the batch list
- **THEN** it lists the bought batch first, with an empty article number, `gekauft · Sigma` and `–`, and then `KL0412` with `CH-0012`, `hergestellt · T-007` linking to the task's page, `AE-1/9` linking to `/lab/journal/AE-1/` and `2 g`

#### Scenario: Searching batches
- **WHEN** the same database is listed with `q=kl04` and with `q=sigma`
- **THEN** the first lists `KL0412` alone and the second the bought batch alone

### Requirement: Vessels
The `inventory` package SHALL keep vessels (`Gefäße`), each a weighed amount of one batch in one place, with a change history: `batch`; `unit`, one of `mg`, `g`, `umol` and `mmol`, in which the vessel is entered and shown; `amount`, at least zero, kept in the vessel's base unit, `mg` for `mg` and `g` and `µmol` for `µmol` and `mmol`, with six decimal places; `flask` (`Kolben`, `Flask`), whether it is its batch's reaction flask; `location` (`Ort`, `Location`), optional, at most 100 characters; `opened_on` (`Angebrochen am`, `Opened on`), for a vessel of a bought batch, the day it was first opened, or none while it is sealed (`versiegelt`, `sealed`), never after today, and none for a vessel of a made batch; and `note`. The batch, unit and `flask` are fixed once the vessel exists. A vessel's substance is its batch's, and a vessel belongs to every item of its substance's article, when the substance has one. Its amount shows in its unit to three decimal places, rounded half up. A vessel at zero is used up, and one above zero is open. A vessel of a bought batch opens sealed, unless a transfer makes it: a vessel a transfer makes is opened on the transfer's date. The first filling, withdrawal or transfer out of a sealed vessel sets its `opened_on` to that movement's date in the transaction that books it; a correction, and the reversal of the movement, leave it as it is. A vessel shows as its batch followed by `#<id>`.

A flask is made only by recording a batch from a task step with its yield and without a location (Inventory forms), and a batch has at most one; every other vessel is stored. A vessel's kind (`Art`, `Kind`) is `Kolben` (`Flask`) for a flask; for a stored vessel it is `Endprodukt` (`End product`) when its substance has an article, else `Zwischenprodukt` (`Intermediate`) when its batch is made and `Handelschemikalie` (`Commercial chemical`) when it is bought.

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
- **THEN** their kinds are `Kolben`, `Endprodukt`, `Zwischenprodukt` and `Handelschemikalie`

#### Scenario: A bought bottle is opened by its first withdrawal
- **WHEN** a signed-in user records a batch of `acetophenone` bought from `Sigma` with `100` g in `Chemikalienschrank 1`, then on 2026-11-20 withdraws `5` g of its vessel into a step of a running task, and on 2026-11-22 another `5` g
- **THEN** the vessel was sealed after the receipt and has the `opened_on` 2026-11-20 after both withdrawals

#### Scenario: A made vessel is never sealed
- **WHEN** a signed-in user posts the edit form of a stored vessel of a made batch with the `opened_on` 2026-11-20
- **THEN** the vessel keeps no `opened_on`

### Requirement: Vessel list
`/lab/inventory/vessels/` SHALL list the open vessels, of every substance, with the columns `Gefäß`, `Name`, `Artikelnr.`, `Art`, `Charge`, `Herkunft`, `Menge`, `Ort`, `Datum`, `Angebrochen` and `Bemerkung` (`Vessel`, `Name`, `Article no.`, `Kind`, `Batch`, `Source`, `Amount`, `Location`, `Date`, `Opened`, `Note`): `#<id>`, linking to the vessel's page; its substance's name, linking to the substance's page; the article number of the substance's article, empty when there is none; its kind; its batch, linking to the batch's page; the batch's source as the batch list shows it; its amount; its location; its batch's date; for a vessel of a bought batch its `opened_on` or `versiegelt` (`sealed`), and nothing for one of a made batch; and its note. The vessels are ordered by name regardless of case, then by their batch's date, oldest first and vessels without one last, then by id. `empty=1` adds the used-up vessels. `kind=<kind>`, one of `flask`, `end-product`, `intermediate` and `commercial`, lists the vessels of that kind; another value lists every kind. The page offers each kind and shows the one in force. A signed-in user sees a link `Neue Charge` (`New batch`).

#### Scenario: Used-up vessels
- **WHEN** the database holds an open vessel and a used-up vessel, and a test client requests the vessel list with and without `empty=1`
- **THEN** it lists both with it and only the open vessel without

#### Scenario: Vessels by kind
- **WHEN** the database holds an open flask of a made batch of `cinnamic-acid`, an open vessel of a made batch of `acetophenone`, which has no article, and one of a batch of `acetophenone` bought from `Sigma`, and a test client requests the vessel list, and then with `kind=commercial`
- **THEN** the first lists the three with the kinds `Kolben`, `Zwischenprodukt` and `Handelschemikalie`, the first with `CH-0012` and the others with an empty article number, the last with `gekauft · Sigma`; the second lists the bought vessel alone

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
- `/lab/inventory/batches/new/`: a new batch with its substance by key; its source, `hergestellt` when none is chosen; for a made batch its number and its journal entry, given as `<code>/<number>` as a task step names one (task-tracker "Task page"); for a bought batch its supplier, the supplier's article number and the supplier's batch; its date, today by default; its note; and an amount, its unit and a location, with a `datalist` of the locations in use, that open the batch's first vessel, a stored one, when the amount is given. `?substance=<key>` fills in the substance, and `?source=bought` chooses `gekauft`. `?step=<id>` records a batch made by that task step: the source is `hergestellt`, the substance is filled in with the first product of the step's entry, or the task's substance for a step without one, and a substance the step does not make is refused; the journal entry is the step's, shown and not editable, when the step names one; and the amount is required and is the batch's yield, opening a flask when no location is given and a stored vessel at the location given. A step whose task is neither planned nor running, a number another made batch has regardless of case, a number on a bought batch, an amount without its unit, and a journal entry whose code is no notebook's are refused;
- `/lab/inventory/batches/<id>/edit/`: the number, journal entry and yield of a made batch, the supplier, supplier's article number and supplier's batch of a bought one, and the date and note;
- `/lab/inventory/batches/<id>/vessels/new/`: a new stored vessel of the batch with its opening amount, its unit, its location, with the `datalist` of the locations in use, and its note;
- `/lab/inventory/vessels/<id>/withdraw/`: a withdrawal from an open vessel into a step of a task that is planned or running, chosen among those tasks' steps or given as `?step=<id>`, with the amount in the vessel's unit and the date; an amount above the vessel's is refused;
- `/lab/inventory/vessels/<id>/transfer/`: a transfer from an open vessel, with the amount in the source vessel's unit, the date and a note, into a stored vessel of the same batch, chosen among them, or into a new vessel at the location given; an amount above the vessel's, and a target whose unit converts from the source's only through a molar mass the substance lacks, are refused, the latter with an error at the target;
- `/lab/inventory/vessels/movements/<id>/reverse/`, a POST: reverses a withdrawal not yet reversed;
- `/lab/inventory/vessels/<id>/edit/`, for the location and note and, for a vessel of a bought batch, its `opened_on`, which may be emptied to mark it sealed, and `/lab/inventory/vessels/<id>/correct/`.

The withdrawal, transfer, correction and edit forms of a vessel open in a dialog over the page where a list offers them so (Lists by substance); the vessel's page links them as pages, as before.

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

#### Scenario: Goods receipt
- **WHEN** a signed-in user requests `/lab/inventory/batches/new/?substance=benzaldehyde&source=bought`
- **THEN** the form has the substance `benzaldehyde` and the source `gekauft` filled in

### Requirement: Batches
The `inventory` package SHALL keep batches (`Chargen`), each a quantity of one substance with one origin, with a change history:

- `substance`, a substance of the registry;
- `source` (`Herkunft`, `Source`), `made` (`hergestellt`, `made`) or `bought` (`gekauft`, `bought`);
- for a made batch: `number` (`Charge`, `Batch`), required, at most 30 characters, unique among made batches regardless of case and of their substance; `journal_entry` (`Laborjournal`, `Lab notebook`), the journal entry it is written down in (lab-journal "Notebooks and entries"), or none; `task_step`, the task step that made it, or none: a step whose entry has the batch's substance among its products, or, for a step without an entry, whose task makes the batch's substance; and `yield` (`Ausbeute`, `Yield`), an amount above zero in one of the units `mg`, `g`, `umol` and `mmol`, or none;
- for a bought batch: `supplier` (`Lieferant`, `Supplier`), at most 100 characters, and `supplier_article_number` (`Artikelnr. des Lieferanten`, `Supplier's article no.`) and `supplier_batch` (`Charge des Lieferanten`, `Supplier's batch`), at most 50 characters each, each optional; a bought batch has no number, journal entry, step or yield;
- `date` (`Datum`, `Date`), the day it was made or received, or none, never after today;
- `note`.

The substance, source and `task_step` are fixed once the batch exists. A batch may be of any substance, intermediates and commercial chemicals among them, and one substance may have made and bought batches side by side; a journal entry may be named by no batch, one or several. A batch shows as its number, a bought batch as its supplier's batch number, and either, when it has none, as `#<id>`. A batch is recorded from a task step only while the step's task is planned or running, and then names the step's journal entry when the step names one. Its yield shows in its unit to three decimal places, rounded half up. A batch that has vessels, or that a task step made, cannot be deleted, except by `demo_data --replace` (lab-demo "Demo data command").

#### Scenario: Made and bought batches
- **WHEN** a signed-in user records a batch of `cinnamic-acid` made in the lab with the number `KL0412FA`, and another bought from `Sigma` with the supplier's article number `C80857` and the supplier's batch `MKCK1234`
- **THEN** both batches exist with their sources, the first showing as `KL0412FA` and the second as `MKCK1234` with its supplier and article number

#### Scenario: Numbers unique regardless of case
- **WHEN** a made batch `KL0412FA` of `cinnamic-acid` exists and a signed-in user records a made batch of `acetophenone` with the number `kl0412fa`
- **THEN** the form shows an error at the number and no batch is created

#### Scenario: Fractions of one entry
- **WHEN** the first step of a running task following `SEQ-0002` names the journal entry `CE-3/2`, and a signed-in user records from that step two batches of `4-acetylbiphenyl`, `CE3002FA` and `CE3002FB`, and then one of `cinnamic-acid`
- **THEN** the first two exist, each made by that step and naming `CE-3/2`, and the third is refused with an error at the substance

#### Scenario: Not from an ended task
- **WHEN** a signed-in user posts the new-batch form for a step of an ended task
- **THEN** the form shows an error and no batch is created
