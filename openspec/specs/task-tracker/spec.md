# task-tracker Specification

## Purpose
Track the syntheses of end products in the lab application: tasks with product, priority, assignee, dates, steps and progress, product batches, and the report and QC-list flags, their numbers, derived state and follow-up, the list with its filters, the task page with its actions, the forms and the admin.
## Requirements
### Requirement: Task record
A task SHALL hold:

- `number`, assigned when the task is created;
- `substance`, the substance it makes, a required substance of the registry (lab-registry "Substances"), shown as its name linking to its page (web-app "Substance links");
- `priority`: `high` (`hoch`, `high`), `medium` (`mittel`, `medium`) or `low` (`niedrig`, `low`); `medium` when created;
- `assignee`, an optional account;
- `started` and `ended`, optional dates, neither after today; `ended` needs `started` and is not before it;
- `sequence`, an optional synthesis sequence of the collection (collection-import "Imported rows");
- `start_step`, the step of its sequence the task starts at, from 1, and 1 for a task without a sequence: the steps before it are skipped, their product taken from stock (production-planning "Starting from stock"). A save that sets or changes `sequence` or changes `start_step` plans the steps anew, and then the sequence is not withdrawn, its target is the task's substance and `start_step` is at most its number of steps; a save that changes the substance of a task with a sequence gives it the sequence's target. Other saves keep a plan whose sequence the collection has since changed, whatever its target or number of steps now;
- its steps, in order, each with its `position`, from 1; `entry`, the scope entry it carries out, or none for a step not written down as one; `planned_import`, the accepted import that was the latest when the step was planned, or none; `done_on`, the date it was done, or none; and `journal_entry`, the journal entry it is written down in (lab-journal "Notebooks and entries"), or none. A step that names a journal entry is never removed, and the task's `sequence` is not set, changed or cleared, nor its `start_step` changed, while one of its steps names one. A save may set, change or clear `sequence`, or change `start_step`, only while none of the task's steps is done, has made a batch (end-product-inventory "Batches") or has taken a withdrawal (end-product-inventory "Vessels"). When it sets or changes either, the task's steps become one per step of the sequence from `start_step` on, in its order, each with that step's entry and the latest accepted import; when it clears it, they become plain steps, as many as the form's steps total (Task forms). A save that leaves `sequence` and `start_step` as they were leaves the steps' entries and imports as they were, so a task keeps its steps after the sequence changes in the collection or is withdrawn. Without a sequence the steps carry no entry and no import;
- `report` and `qc_list`, flags, off when created;
- `cancelled`, a flag, off when created;
- `failed`, a flag, off when created: the synthesis failed and makes no product; a failed task has no product batch;
- `note`, optional text of several lines;
- `created_by` and `created_at`, set when it is created.

Its progress is the number of its steps done divided by the number of its steps, as a whole percentage rounded down, and has no value without steps. A task's batches are the batches its steps made (production-planning "Batches of tasks"), and its product batches those of them whose substance is the task's. A task that is ended and has not failed SHALL have a product batch; a save or action that would end one without one is refused. Since a batch is recorded from a step, a task needs a step to end without failing. A task's substance does not change once one of its steps made a batch. A save or action that ends a task, marks it failed or cancels it, through the actions, the forms or the admin, writes off in the same transaction what each flask of its batches still holds, by a `remainder` movement dated the day it is booked, whatever the task's end date (end-product-inventory "Vessels"); a save that is refused writes off nothing. Its state is `cancelled` (`Verworfen`, `Cancelled`) when that flag is on, else `failed` (`Fehlgeschlagen`, `Failed`) when that flag is on, else `ended` (`Abgeschlossen`, `Ended`) with an end date, else `running` (`In Arbeit`, `Running`) with a start date, else `planned` (`Geplant`, `Planned`). An ended task that has not failed needs follow-up (`Nacharbeit`, `Follow-up`) while `report` or `qc_list` is off; a failed one needs none. Tasks and their steps keep a change history.

#### Scenario: State and progress
- **WHEN** a task has `started` 2026-11-02, no end, and five steps, two of them done
- **THEN** its state is running and its progress 40

#### Scenario: Follow-up
- **WHEN** a task has an end date, `report` on and `qc_list` off
- **THEN** its state is ended and it needs follow-up, and setting `qc_list` ends the follow-up

#### Scenario: Cancelled outranks ended
- **WHEN** a task has an end date, both flags off and `cancelled` on
- **THEN** its state is cancelled and it needs no follow-up

#### Scenario: Steps from a sequence
- **WHEN** the demo collection is imported and a signed-in user saves a task with the sequence `SEQ-0002` and the steps total 7
- **THEN** the task has two steps, the first carrying the entry of `OSDB-0004` and the second entry 1 of `OSDB-0009`, both with the latest accepted import and neither done

#### Scenario: Sequence gone from the collection
- **WHEN** a task was saved with `SEQ-0001`, an import then withdraws that sequence, and a signed-in user sets the task's report flag
- **THEN** the save succeeds and the task keeps its two steps, their entries and their import

#### Scenario: Ending needs a product batch
- **WHEN** a running task of `cinnamic-acid` has no batch, and a signed-in user posts `end`; then a batch of `cinnamic-acid` is recorded from its last step and `end` is posted again
- **THEN** the first is refused with an error message and the task stays running, and the second ends it

#### Scenario: A failed synthesis
- **WHEN** a signed-in user posts `fail` to a running task without a product batch
- **THEN** the task is ended and failed, its state is `failed`, and it needs no follow-up

#### Scenario: Ending through the admin
- **WHEN** the first step of a running task recorded a batch of its intermediate whose flask holds `300` mg, and a staff user marks the task failed with the end date of yesterday in the admin
- **THEN** the task is failed and the flask's newest movement is a `remainder` of `300` mg dated today

#### Scenario: A refused save keeps the flask
- **WHEN** a running task without a product batch has a step whose batch of an intermediate has a flask holding `300` mg, and a signed-in user posts the task's form with an end date
- **THEN** the form shows an error at the end date, the task stays running and the flask holds `300` mg

#### Scenario: Ending writes off the flask
- **WHEN** the last step of a running task of `cinnamic-acid` recorded a batch whose flask holds `2` g, `1,5` g of it were transferred into a stored vessel, and a signed-in user posts `end`
- **THEN** the task is ended, the flask holds nothing, its newest movement is a `remainder` of `0,5` g, and the stored vessel keeps `1,5` g

#### Scenario: A task that starts at the second step
- **WHEN** a signed-in user creates a task of `acetylsalicylic-acid` with the sequence `SEQ-0001` and `start_step` 2
- **THEN** the task has one step, carrying out the entry of `OSDB-0002`, and its `start_step` is 2

#### Scenario: A plan outlives a shorter sequence
- **WHEN** a task follows a three-step sequence from its third step, an accepted import shortens the sequence to two steps, and a signed-in user edits only the task's note
- **THEN** the save succeeds and the task keeps its `start_step` 3 and its one step

### Requirement: Task numbers
A task's number SHALL be `T-` followed by a counter of at least three digits, zero-padded: `T-001`, `T-099`, `T-1000`. A counter row, incremented by one atomic update in the transaction that creates the task and read back in it, gives the next value, so tasks created at the same time get different numbers and a number is never given twice, even after its task was deleted. A task's page is `/lab/tasks/<number>/`; an unknown number answers 404.

#### Scenario: Numbers after a deletion
- **WHEN** a test creates three tasks, deletes `T-003` and creates another
- **THEN** the new task is `T-004`

### Requirement: Task list
`/lab/tasks/` SHALL list tasks in a table with the columns `Nr.`, `Produkt`, `Priorität`, `Bearbeitung`, `Beginn`, `Ende`, `Fortschritt`, `Charge`, `Bericht`, `QC-Liste` and `Status` (`No.`, `Product`, `Priority`, `Assignee`, `Started`, `Ended`, `Progress`, `Batch`, `Report`, `QC list`, `State`): the number linking to the task's page; the substance; the task's priority, computed or entered, with its mark, as `production-planning` states under Computed priority on tasks; the assignee's initials with the display name as title; the dates; the progress as `<done>/<steps>`, the numbers of its steps done and of its steps, and a `progress` element, empty without steps; the numbers of its product batches, joined by `, `; the two flags as `ja` or `nein` (`yes`, `no`); and the state as a badge with its label, followed by `Nacharbeit` (`Follow-up`) when the task needs it. Rows are ordered by that priority, high first, then by the task's slack, smallest first and tasks without one last, then by state, running before planned before ended before cancelled, then by start date, earliest first and tasks without one last, then by number. Above the table a line counts the tasks: `<p> geplant · <r> in Arbeit · <f> Nacharbeit` (`<p> planned · <r> running · <f> follow-up`). There is no paging. A signed-in user sees a link `Neue Aufgabe` (`New task`).

The list filters with GET parameters in a form above it, and each filter keeps its value in the form:

- `state`: `active` (planned, running, and ended needing follow-up; the default), `planned`, `running`, `followup`, `ended`, `cancelled` or `all`;
- `person`: an account's initials, or `none` for tasks without an assignee;
- `priority`: `high`, `medium` or `low`, compared with the task's priority, computed or entered;
- `q`: text found, regardless of case, in the number, the substance's key, name or German name, the number of one of its batches, or the note.

An unknown value of a filter is ignored, with the default in its place.

#### Scenario: Default view
- **WHEN** the database holds a planned task of priority low, a running task of priority high, an ended task with both flags on, an ended task of priority low without the report, and a cancelled task, and a test client requests `/lab/tasks/`
- **THEN** the table lists the running task, the planned task and the ended task without the report, in that order, the last marked `Nacharbeit`, and the count reads `1 geplant · 1 in Arbeit · 1 Nacharbeit`

#### Scenario: Filters
- **WHEN** the demo data set is written and a test client requests `/lab/tasks/?state=all&person=KL&q=zimt`
- **THEN** the table lists exactly the tasks of `KL`, in any state, whose number, substance key or names, a batch's number or note contains `zimt` in any case, among them a task of `cinnamic-acid`, and the form shows `all`, `KL` and `zimt`

#### Scenario: Computed over entered
- **WHEN** a planned task with the entered priority low matches an article whose slack is 11 days, a running task with the entered priority high matches no article, a planned task has the entered priority medium, and a test client requests `/lab/tasks/` and `/lab/tasks/?priority=high`
- **THEN** both list the first task with `hoch` and `berechnet`; the first lists it before the task of medium priority, and the second lists the first two tasks and not the third

### Requirement: Task page
`/lab/tasks/<number>/` SHALL show the number and the substance's name as heading, then the state, follow-up, priority with its mark, assignee, dates, progress, product batches, each linking to its page, the two flags, note, the creating user and time, and the change history. A task with a sequence shows the sequence's ID linking to `/sequences/<ID in lower case>/`, followed by `ab Stufe <k>` (`from step <k>`) when its `start_step` is above 1. A task with steps lists them in order: a step with an entry as its procedure's ID linking to `/procedures/<ID in lower case>/`, followed for a general procedure by `Eintrag <n>` (`Entry <n>`), the entry's position; a step without one as `Stufe <n>` (`Step <n>`), its position; and a done step marked `erledigt am <date>` (`done on <date>`). A withdrawn sequence or procedure shows with the mark `nicht in der Sammlung` and no link, and so does a step whose entry is withdrawn, shown by its procedure's ID and the entry's signature in place of `Eintrag <n>`, since its position may since belong to another entry. `Eintrag <n>` appears only for an entry of a procedure the import marked general. The change history lists the task's changes and its steps', newest first; a step's change is headed `Stufe <n>` (`Step <n>`) and a removed step's `Stufe <n> entfernt` (`Step <n> removed`). For the article the task matches (production-planning "Matching tasks and articles"), when there is one, it shows the article number linking to `/lab/planning/` and, for an article without a forecast, `Kein Verbrauch, keine Prognose.` (`No consumption, no forecast.`), else the article's runway, synthesis time, slack and latest start, and, for a planned or running task, the task's own slack, marked `verspätet` (`late`) when below zero. Under each step it shows, when the step names a journal entry, `Laborjournal <entry>` (`Lab notebook <entry>`) linking to the notebook's page, and for a signed-in user, whatever the task's state, a form posting `journal_entry` to `/lab/tasks/steps/<id>/journal/`, with a field `Laborjournal` (`Lab notebook`) holding the step's entry and a button `Speichern` (`Save`): a value `<code>/<number>` whose code is a notebook's makes the step name that entry, an empty value makes it name none, and either leads back to the task's page with the message `Laborjournal von Stufe <n> gespeichert.` (`Lab notebook of step <n> saved.`), the change recorded in the step's history; any other value leads back with the error as a message and changes nothing. Under each step it also lists the batches the step made, each linking to its page, with its journal entry, its flask's amount while the flask holds one, and its stored vessels' amount, and the withdrawals booked into it, each linking to its vessel, and for a signed-in user, while the task is planned or running, the links `Charge erfassen` (`Record batch`) to `/lab/inventory/batches/new/?step=<id>` and `Entnahme buchen` (`Book a withdrawal`), the latter listing the open vessels of the step's substrates, or of every substance for a step without an entry. A signed-in user sees a link `Bearbeiten` (`Edit`) and the actions that apply.

#### Scenario: Task with a sequence
- **WHEN** the demo collection is imported and a test client requests the page of a task with the sequence `SEQ-0002` whose first step was done on 2026-11-03
- **THEN** it lists `OSDB-0004`, marked `erledigt am 03.11.2026`, and `OSDB-0009` with `Eintrag 1`, each linking to its procedure, and shows no edit link when not signed in

#### Scenario: Forecast of the product
- **WHEN** on 2026-11-04 with the default parameters a test client requests the page of a planned task that matches an article of one 1 mg item with 10 containers, `m` 9, `v` 9 and no bulk
- **THEN** it shows the article number linking to `/lab/planning/`, the runway 60 days, the synthesis time 21 days, the slack 11 days, the latest start 2026-11-15 and the task's slack 11 days

#### Scenario: A step's journal entry
- **WHEN** the demo data set is written and user `klehmann` posts `journal_entry` `CE-3/5` for the second step of the running task of `SEQ-0002`
- **THEN** the task's page shows `Laborjournal CE-3/5` under that step, linking to `/lab/journal/CE-3/`, the entry `CE-3/5` exists, and the step's history records the change

#### Scenario: A step names an unknown notebook
- **WHEN** the same user posts `journal_entry` `ZZ-1/1` for that step, and then `CE-3`
- **THEN** each leads back to the task's page with an error message, and the step names no entry

### Requirement: Task actions
For a signed-in user, the task's page SHALL offer these buttons, each a POST to `/lab/tasks/<number>/<action>/` that changes the task, records the change in its history and returns to the page with a message:

- `start`, `Beginnen` (`Start`), on a planned task: sets `started` to today;
- `step`, `Stufe erledigt` (`Step done`), on a running task with a step not done: marks its first such step done today;
- `end`, `Abschließen` (`End`), on a running task with a product batch (Task record): sets `ended` to today, marks every step not done as done today, and writes off what its flasks hold, the message naming each amount written off;
- `fail`, `Fehlgeschlagen` (`Failed`), on a running task without a product batch: sets `failed` and sets `ended` to today, leaving its steps as they are, and writes off what its flasks hold;
- `report` and `qc-list`, `Bericht erledigt` (`Report done`) and `Auf QC-Liste` (`On QC list`), on an ended task with that flag off: set the flag.

An action that does not apply to the task's current state changes nothing and returns to the page with an error message.

#### Scenario: Steps through actions
- **WHEN** a signed-in user starts a planned task with two steps on 2026-11-04, posts `step` on 2026-11-05, records a batch of the task's substance from its second step, then posts `end` on 2026-11-06
- **THEN** the task has `started` 2026-11-04 and `ended` 2026-11-06, its first step was done on 2026-11-05 and its second on 2026-11-06, and its history lists the start, the end and the two steps' changes

#### Scenario: Action out of state
- **WHEN** a signed-in user posts `step` to a planned task
- **THEN** the task is unchanged and the page shows an error message

### Requirement: Task forms
`/lab/tasks/new/` SHALL create a task and `/lab/tasks/<number>/edit/` change one, for a signed-in user. The form holds the substance by key, offered through the substances' `datalist` as the inventory forms offer it, priority, assignee (every account, shown as initials and display name, or none), start and end dates, sequence, a choice of the collection's sequences that are not withdrawn, by ID and title, or none, keeping a withdrawn sequence the task already has, start step (`Beginn ab Stufe`, `Start at step`), a whole number, 1 when left empty and ignored without a sequence, steps total, steps done, report, QC list, cancelled and failed (on the edit form only) and note. Steps total sets the number of steps of a task without a sequence: steps are added, not done, or the last ones removed, and an empty total removes them all; with a sequence the field is ignored and the form shows the number of the task's steps. Steps done marks the first that many steps done, those done before keeping their dates and the others taking today, and the rest not done. Invalid input, among it an end date on a task that has not failed without a product batch, an unknown substance, an end without a start or before it, steps done above the number of steps, a steps total below the number of steps done, on a save that plans the steps anew a sequence whose target is not the task's substance or a start step above the sequence's number of steps, a substance changed on a task with a sequence to another than the sequence's target, a substance changed on a task one of whose steps made a batch, a sequence set, changed or cleared or a start step changed on a task with a step done or naming a journal entry, a steps total that would remove a step naming a journal entry, having made a batch or having taken a withdrawal, and a withdrawn sequence the task did not have, shows the form again with the errors beside their fields and saves nothing. A saved form leads to the task's page with the message `Aufgabe <number> gespeichert.` (`Task <number> saved.`). The creating user becomes `created_by`. The priority field carries the help text `Gilt, solange keine Prognose die Priorität berechnet.` (`Applies while no forecast computes the priority.`). The new-task form fills in a substance key given as the GET parameter `substance`.

#### Scenario: Creating a task
- **WHEN** user `KL` posts the substance `cinnamic-acid`, priority `high` and assignee `AE` to `/lab/tasks/new/`
- **THEN** a planned task `T-<n>` exists with `created_by` `KL`, and the response redirects to its page, which shows the message and `(E)-Zimtsäure`

#### Scenario: End before start
- **WHEN** a signed-in user posts a task started 2026-11-05 and ended 2026-11-04
- **THEN** the form shows again with an error at the end date, and nothing is saved

#### Scenario: Substance from the query
- **WHEN** a signed-in user requests `/lab/tasks/new/?substance=cinnamic-acid`
- **THEN** the form's substance field holds `cinnamic-acid`

#### Scenario: Steps by hand
- **WHEN** a signed-in user saves on 2026-11-05 a task without a sequence with the steps total 3 and steps done 1, and on 2026-11-06 the same task with steps done 2
- **THEN** the task has three steps without entries, the first done on 2026-11-05 and the second on 2026-11-06

#### Scenario: A sequence with work done
- **WHEN** a task follows `SEQ-0002` with its first step done, and a signed-in user posts it with the sequence `SEQ-0001`
- **THEN** the form shows again with an error at the sequence, and the task keeps its steps

#### Scenario: A withdrawn entry
- **WHEN** a task follows `SEQ-0002` and an import gives entry 1 of `OSDB-0009` other substances, and a test client requests the task's page
- **THEN** the second step shows `OSDB-0009` with the old entry's signature and the mark `nicht in der Sammlung`, and no `Eintrag 1`

#### Scenario: A journal entry holds the steps
- **WHEN** the second step of a task without a sequence names the journal entry `AE-1/9` and a signed-in user saves the task with the steps total 1
- **THEN** the form shows an error at the steps total and the task keeps its two steps

#### Scenario: Filled in from the planning list
- **WHEN** a signed-in user requests `/lab/tasks/new/?substance=acetylsalicylic-acid&sequence=SEQ-0001&start_step=2`
- **THEN** the form holds the substance `acetylsalicylic-acid`, the sequence `SEQ-0001` and the start step 2

#### Scenario: A sequence of another target
- **WHEN** a signed-in user posts the new-task form with the substance `cinnamic-acid` and the sequence `SEQ-0001`
- **THEN** the form shows an error at the sequence and no task is created

#### Scenario: A start step beyond the sequence
- **WHEN** a signed-in user posts the new-task form with the substance `acetylsalicylic-acid`, the sequence `SEQ-0001` and the start step 3
- **THEN** the form shows an error at the start step and no task is created

### Requirement: Tasks in the admin
The admin SHALL list tasks and accounts for staff, with search by number, the substance's key and names, and the numbers of its batches, and the change history of each task. Deleting a task in the admin does not free its number. A task's `sequence`, `start_step` and steps are read-only there, since only the task forms plan steps, and its history shows past versions without restoring one (a post answers 403), and a substance changed there on a task with a sequence to another than the sequence's target, or on a task one of whose steps made a batch, is refused, as the forms refuse it.

#### Scenario: Admin list
- **WHEN** a staff user requests `/lab/admin/tasks/task/`
- **THEN** the page lists the tasks by number

#### Scenario: The plan read-only in the admin
- **WHEN** a staff user opens the admin's change page of a task with a sequence, and posts it with the substance `cinnamic-acid`
- **THEN** the sequence and the start step show read-only, the page shows an error, and the task keeps its substance

### Requirement: Live task list
`/lab/tasks/` SHALL implement live list updates (web-app "Live lists") as a main list (web-app "Main lists"):

- Its filter form (`#filters`) updates `#item-rows` in place with `morph:outerHTML`, each row carrying the stable `id="task-row-<pk>"`. It updates `#task-counts`, `#item-head`, `#item-detail` and `#filter-selected` out of band with `#task-counts:morph,#item-head:morph,#item-detail:morph,#filter-selected:morph`. It uses `hx-get="/lab/tasks/"`, `hx-push-url="true"`, `hx-sync="#main:replace"`, and scoped triggers (`submit`, `search from:#filter-q`, `input delay:200ms from:#filter-q`, `change target:select`). It keeps its `method="get"`, `action="/lab/tasks/"`, and submit button for no-script use.
- Its column header links update `#item-rows` in place with `hx-sync="#main:replace"`, and out of band `#task-counts:morph,#item-head:morph,#item-detail:morph,#filters:morph`, keeping their `href` fallbacks.
- Its view returns the complete page for plain GET requests and HTMX history restores (`HX-Request: true` with `HX-History-Restore-Request: true`), and varies on `HX-Request` and `HX-History-Restore-Request`. On non-restore HTMX GET responses it sets `HX-Push-Url` to `/lab/tasks/` with cleaned active query parameters:
  - `state`, omitted when `active` (the default) and included otherwise;
  - normalized `person`, `none` or valid uppercase account initials;
  - valid `priority`;
  - trimmed non-empty `q`;
  - `sort` and `dir=desc` as web-app "Main lists" states;
  - the resolved `selected` task number, omitted when the list is empty.
- `/lab/tasks/<number>/detail/` sets `HX-Replace-Url` on HTMX responses to the list URL with the active filters and `selected` naming the task.

#### Scenario: Live filtering and canonical URL on the task list
- **WHEN** a test client requests `/lab/tasks/?state=active&person=kl&priority=bogus&q=+Alpha+`, `/lab/tasks/?state=all&person=none`, `/lab/tasks/?state=running&sort=number`, `/lab/tasks/?state=bogus`, and `/lab/tasks/?q=no-match` with `HX-Request: true`
- **AND** it requests `/lab/tasks/?state=running` once with both `HX-Request: true` and `HX-History-Restore-Request: true`, and once without HTMX headers
- **THEN** all responses return complete page markup (`html`, `#main`, table, filter form) and vary on `HX-Request` and `HX-History-Restore-Request`
- **AND** `#filters` carries `hx-get="/lab/tasks/"`, `hx-push-url="true"`, `hx-sync="#main:replace"`, scoped triggers (`submit`, `search from:#filter-q`, `input delay:200ms from:#filter-q`, `change target:select`), `hx-target="#item-rows"`, `hx-select="#item-rows"`, `hx-swap="morph:outerHTML"`, and disjoint `hx-select-oob="#task-counts:morph,#item-head:morph,#item-detail:morph,#filter-selected:morph"`
- **AND** populated `#item-rows` rows carry `id="task-row-<pk>"` and `data-item` with the task's number, the state-filtered response keeps counts across all states in `#task-counts`, and the empty search renders an addressable empty `#item-rows`
- **AND** the five ordinary HTMX responses set `HX-Push-Url` to `/lab/tasks/?person=KL&q=Alpha&selected=<resolved>`, `/lab/tasks/?state=all&person=none&selected=<resolved>`, `/lab/tasks/?state=running&sort=number&selected=<resolved>`, `/lab/tasks/?selected=<resolved>`, and `/lab/tasks/?q=no-match`, while the history-restore and plain GET responses omit `HX-Push-Url`

### Requirement: Task details
The task list SHALL be a main list (web-app "Main lists") whose details of a task, `/lab/tasks/<number>/detail/`, show:

- the number and the substance's name as heading, linking to the task's page;
- its state as a badge, followed by `Nacharbeit` (`Follow-up`) when the task needs it;
- its priority with its mark, as the task list shows it;
- its assignee and dates;
- its progress as `<done>/<steps>`;
- its product batches, each linking to its page;
- the two flags as `ja` or `nein` (`yes`, `no`);
- its note;
- each field `–` when it has no value;
- its steps, when it has any, in a table with the columns `Stufe`, `Vorschrift` and `Erledigt` (`Step`, `Procedure`, `Done`): the step's position; its procedure's ID linking as the task page links it, followed for a general procedure by `Eintrag <n>`, or empty for a step without an entry; and the date the step was done, or empty;
- a link `Aufgabenseite öffnen` (`Open task page`) to the task's page.

For a signed-in user the details also link `Bearbeiten` (`Edit`) to the task's edit form. The details endpoint answers only GET, other methods with 405, and its path is never read as a task action.

#### Scenario: Details of a task
- **WHEN** the demo collection is imported and a test client requests the task list with `state=all` and `selected` naming a task with the sequence `SEQ-0002` whose first step was done on 2026-11-03
- **THEN** `#item-detail` is headed by the task's number and product, linking to its page, and lists its steps with `OSDB-0004` done on `03.11.2026` and `OSDB-0009` with `Eintrag 1`, each linking to its procedure, and links `Aufgabenseite öffnen`, and no `Bearbeiten` for a visitor

#### Scenario: Details are not an action
- **WHEN** a signed-in user requests `/lab/tasks/<number>/detail/` with `HX-Request: true`, and posts to it
- **THEN** the first answers 200 with the task's `#item-detail`, and the second answers 405 and leaves the task unchanged

