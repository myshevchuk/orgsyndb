## MODIFIED Requirements

### Requirement: Bulk lots
The `inventory` package SHALL keep bulk lots, each with a change history: `substance`, a substance of the registry; `source` (`Herkunft`, `Source`), `made` (`hergestellt`, `made`) or `bought` (`gekauft`, `bought`); `supplier` (`Lieferant`, `Supplier`), optional, at most 100 characters; `unit`, one of `mg`, `g`, `umol` and `mmol`, in which the lot is entered and shown; `amount`, at least zero, kept in the lot's base unit, `mg` for `mg` and `g` and `µmol` for `µmol` and `mmol`, with six decimal places; `batch`, `location`, at most 100 characters, and `made_on`, each optional; `task_step`, for a made lot only, the task step that made it (task-tracker "Task record"), whose entry has the lot's substance among its products, or, for a step without an entry, whose task makes the lot's substance; and `note`. The substance, source, unit and `task_step` are fixed once the lot is created. A lot may be of any substance, intermediates and house-made reagents among them, and one substance may have made and bought lots side by side; a lot belongs to every item of its substance's article, when the substance has one. Its amount shows in its unit to three decimal places, rounded half up.

Its amount changes only by its movements, each holding `kind`, `amount`, `amount_after`, `date`, `booked_at`, `user`, `note`, and `task_step` and `reverses` where they apply, by one atomic conditional update in the transaction that stores the movement, as for items: `opening`, the amount entered on creation; `filling`, the amount taken, more than zero and at most the lot's amount; `withdrawal` (`Entnahme`, `Withdrawal`), the amount taken into a task step, named by `task_step`, more than zero and at most the lot's amount; `correction`, the amount weighed, with a required note; `reversal`, the amount a reversed filling or withdrawal returns, the withdrawal named by `reverses`, each withdrawal reversed at most once. A lot at zero is used up. Lot movements are never edited or deleted, except that deleting a lot in the admin deletes its opening movement with it.

#### Scenario: Correction of a lot
- **WHEN** a signed-in user corrects a lot of `50` mg to `47,5` mg with the note `nachgewogen`
- **THEN** the lot holds `47,5` mg and its newest movement is that correction

#### Scenario: Made and bought lots
- **WHEN** a signed-in user creates a lot of `cinnamic-acid` made in the lab and another bought from the supplier `Sigma`
- **THEN** both lots exist with their sources, the second with its supplier, and the items of the article `CH-0012` count both among their bulk

#### Scenario: Lot of a substance without an article
- **WHEN** a signed-in user creates a lot of the substance `acetophenone`, which has no article
- **THEN** the lot exists and belongs to no item

#### Scenario: A lot made by a step
- **WHEN** a signed-in user records, from the first step of a task following `SEQ-0002`, a lot of `4-acetylbiphenyl` of `2` g
- **THEN** the lot exists, made in the lab, with that step as its `task_step`, and recording one of `cinnamic-acid` from that step is refused with an error at the substance

#### Scenario: Withdrawal and its reversal
- **WHEN** a signed-in user withdraws `500` mg of that lot into the second step, and then reverses the withdrawal
- **THEN** the lot holds `1,5` g after the withdrawal and `2` g after the reversal, the withdrawal names the step, the reversal names the withdrawal, and reversing it again is refused

### Requirement: Bulk lot page
`/lab/inventory/bulk/<id>/` SHALL show the lot's substance, linking to its page, and the article number of the substance's article when there is one; its source and supplier; its batch, amount, location, date and note, the mark `aufgebraucht` (`used up`) at zero, its movements in booking order, newest first, with date, booking time, kind, amount, amount after, the user's initials, note and, for a filling, the item filled, for a withdrawal, the task and step it went into, linking to the task, and for a reversal the movement it reverses, the step that made the lot, linking to its task, when it was made by one, each task that belongs to the lot through its batch, linking to it, and its change history. A signed-in user sees the links `Korrigieren` (`Correct`), `Bearbeiten` (`Edit`) and, on an open lot, `Entnahme` (`Withdraw`), and beside each withdrawal not yet reversed a button `Stornieren` (`Reverse`). An unknown id answers 404.

#### Scenario: Lot page after a filling
- **WHEN** a test client requests the page of a lot from which 5 containers of an item were filled
- **THEN** its newest movement is that filling, linking to the item

### Requirement: Inventory forms
For a signed-in user, the application SHALL offer:

- `/lab/inventory/end-products/new/`: a new item with its opening count, its substance by key, the article number, optional, and the category with a `datalist` of the categories in use, the `stocked_on`, optional, left empty for the opening count to set, and the compartment and the box, each with a `datalist` of the values in use;
- `/lab/inventory/items/<id>/edit/`: the item's note, `status`, `stocked_on`, compartment and box, the last two each with a `datalist` of the values in use, and its article's category and, while the article has none, its article number, both saved on the article for every size of it, as the form says beside them;
- `/lab/inventory/deliveries/new/`: a delivery note with ten rows for lines, each offering the items with an article number, each shown as its article number, container and name and, where they are set, `Fach <compartment>` and `Box <box>` (`Compartment <compartment>`, `Box <box>`), joined by ` · ` and the locations by ` / `, rows left empty being ignored, and a check box `nachgetragen – Bestand bleibt unverändert` (`entered later – stock unchanged`) for a historical note; `?item=<id>`, given once or several times, puts those items in the first rows in the order given, up to ten, leaving out ids of items it does not offer and ids given twice;
- `/lab/inventory/deliveries/<id>/reverse/`: marking a historical note reversed, with its note;
- `/lab/inventory/items/<id>/fill/` and `/correct/`: a movement;
- `/lab/inventory/items/<id>/movements/<movement id>/reverse/`: the reversal of a delivery or filling, with its note;
- `/lab/inventory/items/<id>/consumption/`: the entered value of a year and quarter, replacing an earlier one of that quarter, or removing it when left empty;
- `/lab/inventory/deliveries/<id>/edit/`: a note's number, recipient and note;
- `/lab/inventory/bulk/new/`: a new lot with its opening amount, its substance by key, its source, `hergestellt` when none is chosen, and its supplier, and the location with a `datalist` of the locations in use; `?substance=<key>`, `?batch=<batch>` and `?made_on=<date>` fill in those fields, and `?step=<id>` makes the lot one made by that task step, filling in the first product of the step's entry, or the task's substance for a step without one, its task's batch when the substance is the task's, and today, and refusing a substance the step does not make;
- `/lab/inventory/bulk/<id>/withdraw/`: a withdrawal from an open lot into a step of a task that is planned or running, chosen among those tasks' steps or given as `?step=<id>`, with the amount in the lot's unit and the date; an amount above the lot's is refused;
- `/lab/inventory/bulk/movements/<id>/reverse/`, a POST: reverses a withdrawal not yet reversed;
- `/lab/inventory/bulk/<id>/edit/`, for the batch, location, date and note, refusing at the batch a change that would leave an ended task that has neither failed nor been cancelled without its product lot (task-tracker "Task record"), and `/correct/`.

A substance is named by its key, offered through a `datalist` of every substance's key labelled with its name; an unknown key is an error at the field. On the new-item form, the article number and the category make the substance's article when it has none, an empty number giving it none. When the substance has an article, a field left empty leaves the article's value as it is; a category entered replaces the article's; an article number entered gives the article that number when it has none, as the edit form does, and must otherwise be its number, or the form shows an error at it. On the edit form, the category field holds the article's category and saves what it holds, empty included, and the article number, offered only while the article has none, gives it one when entered and leaves it without one when empty. Invalid input shows the form again with the errors beside their fields and saves nothing. A saved form leads, with a message naming the record, to the page of the delivery note for the forms of notes, and to the page of the item or lot for every other.

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
