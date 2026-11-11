# task-tracker Specification

## Purpose
Track the syntheses of end products in the lab application: tasks with product, priority, assignee, dates, steps and progress, batch, and the report and QC-list flags, their numbers, derived state and follow-up, the list with its filters, the task page with its actions, the forms and the admin.
## Requirements
### Requirement: Task record
A task SHALL hold:

- `number`, assigned when the task is created;
- `substance`, the substance it makes, a required substance of the registry (lab-registry "Substances"), shown as its name linking to its page (web-app "Substance links");
- `priority`: `high` (`hoch`, `high`), `medium` (`mittel`, `medium`) or `low` (`niedrig`, `low`); `medium` when created;
- `assignee`, an optional account;
- `started` and `ended`, optional dates, neither after today; `ended` needs `started` and is not before it;
- `sequence`, an optional synthesis sequence ID, and `sequence_steps`, the procedure IDs of its steps in order; when a save sets or changes `sequence`, `sequence_for` must find it, and the save stores its steps in `sequence_steps` and their number in `steps_total`; a save that leaves `sequence` as it was reads nothing from the index, so a task keeps its steps after the sequence changes or leaves the collection; a save that clears `sequence` clears `sequence_steps`;
- `steps_total`, an optional whole number of at least 1, and `steps_done`, a whole number from 0 to `steps_total`, 0 when created and 0 whenever `steps_total` is empty; with a sequence, `steps_total` is the number of `sequence_steps`;
- `batch`, an optional batch number of at most 30 characters;
- `report` and `qc_list`, flags, off when created;
- `cancelled`, a flag, off when created;
- `note`, optional text of several lines;
- `created_by` and `created_at`, set when it is created.

Its progress is `steps_done` divided by `steps_total`, as a whole percentage rounded down, and has no value without `steps_total`. Its state is `cancelled` (`Verworfen`, `Cancelled`) when the flag is on, else `ended` (`Abgeschlossen`, `Ended`) with an end date, else `running` (`In Arbeit`, `Running`) with a start date, else `planned` (`Geplant`, `Planned`). An ended task needs follow-up (`Nacharbeit`, `Follow-up`) while `report` or `qc_list` is off. Tasks keep a change history.

#### Scenario: State and progress
- **WHEN** a task has `started` 2026-11-02, no end, `steps_total` 5 and `steps_done` 2
- **THEN** its state is running and its progress 40

#### Scenario: Follow-up
- **WHEN** a task has an end date, `report` on and `qc_list` off
- **THEN** its state is ended and it needs follow-up, and setting `qc_list` ends the follow-up

#### Scenario: Cancelled outranks ended
- **WHEN** a task has an end date, both flags off and `cancelled` on
- **THEN** its state is cancelled and it needs no follow-up

#### Scenario: Steps from a sequence
- **WHEN** the index is the demo collection's and a signed-in user saves a task with the sequence `SEQ-0001` and `steps_total` 7
- **THEN** the task's `steps_total` is 2 and its `sequence_steps` are `OSDB-0001` and `OSDB-0002`

#### Scenario: Sequence gone from the collection
- **WHEN** a task was saved with `SEQ-0001`, the index then loses that sequence, and a signed-in user sets the task's report flag
- **THEN** the save succeeds and the task keeps its two steps

### Requirement: Task numbers
A task's number SHALL be `T-` followed by a counter of at least three digits, zero-padded: `T-001`, `T-099`, `T-1000`. A counter row, incremented by one atomic update in the transaction that creates the task and read back in it, gives the next value on PostgreSQL and SQLite alike, so tasks created at the same time get different numbers and a number is never given twice, even after its task was deleted. A task's page is `/lab/tasks/<number>/`; an unknown number answers 404.

#### Scenario: Numbers after a deletion
- **WHEN** a test creates three tasks, deletes `T-003` and creates another
- **THEN** the new task is `T-004`

### Requirement: Task list
`/lab/tasks/` SHALL list tasks in a table with the columns `Nr.`, `Produkt`, `Priorität`, `Bearbeitung`, `Beginn`, `Ende`, `Fortschritt`, `Charge`, `Bericht`, `QC-Liste` and `Status` (`No.`, `Product`, `Priority`, `Assignee`, `Started`, `Ended`, `Progress`, `Batch`, `Report`, `QC list`, `State`): the number linking to the task's page; the substance; the task's priority, computed or entered, with its mark, as `production-planning` states under Computed priority on tasks; the assignee's initials with the display name as title; the dates; the progress as `<steps_done>/<steps_total>` and a `progress` element, empty without a total; the batch; the two flags as `ja` or `nein` (`yes`, `no`); and the state as a badge with its label, followed by `Nacharbeit` (`Follow-up`) when the task needs it. Rows are ordered by that priority, high first, then by the task's slack, smallest first and tasks without one last, then by state, running before planned before ended before cancelled, then by start date, earliest first and tasks without one last, then by number. Above the table a line counts the tasks: `<p> geplant · <r> in Arbeit · <f> Nacharbeit` (`<p> planned · <r> running · <f> follow-up`). There is no paging. A signed-in user sees a link `Neue Aufgabe` (`New task`).

The list filters with GET parameters in a form above it, and each filter keeps its value in the form:

- `state`: `active` (planned, running, and ended needing follow-up; the default), `planned`, `running`, `followup`, `ended`, `cancelled` or `all`;
- `person`: an account's initials, or `none` for tasks without an assignee;
- `priority`: `high`, `medium` or `low`, compared with the task's priority, computed or entered;
- `q`: text found, regardless of case, in the number, the substance's key, name or German name, the batch or the note.

An unknown value of a filter is ignored, with the default in its place.

#### Scenario: Default view
- **WHEN** the database holds a planned task of priority low, a running task of priority high, an ended task with both flags on, an ended task of priority low without the report, and a cancelled task, and a test client requests `/lab/tasks/`
- **THEN** the table lists the running task, the planned task and the ended task without the report, in that order, the last marked `Nacharbeit`, and the count reads `1 geplant · 1 in Arbeit · 1 Nacharbeit`

#### Scenario: Filters
- **WHEN** the demo data set is written and a test client requests `/lab/tasks/?state=all&person=KL&q=zimt`
- **THEN** the table lists exactly the tasks of `KL`, in any state, whose number, substance key or names, batch or note contains `zimt` in any case, among them a task of `cinnamic-acid`, and the form shows `all`, `KL` and `zimt`

#### Scenario: Computed over entered
- **WHEN** a planned task with the entered priority low matches an article whose slack is 11 days, a running task with the entered priority high matches no article, a planned task has the entered priority medium, and a test client requests `/lab/tasks/` and `/lab/tasks/?priority=high`
- **THEN** both list the first task with `hoch` and `berechnet`; the first lists it before the task of medium priority, and the second lists the first two tasks and not the third

### Requirement: Task page
`/lab/tasks/<number>/` SHALL show the number and the substance's name as heading, then the state, follow-up, priority with its mark, assignee, dates, progress, batch, the two flags, note, the creating user and time, and the change history. A task with a sequence shows the sequence's ID linking to `/sequences/<ID in lower case>/` and its `sequence_steps` as an ordered list, each procedure linking to `/procedures/<ID in lower case>/`, the first `steps_done` steps marked `erledigt` (`done`); a sequence or procedure the current index lacks shows with the mark `nicht in der Sammlung` and no link. For the article the task matches (production-planning "Matching tasks and articles"), when there is one, it shows the article number linking to `/lab/planning/` and, for an article without a forecast, `Kein Verbrauch, keine Prognose.` (`No consumption, no forecast.`), else the article's runway, synthesis time, slack and latest start, and, for a planned or running task, the task's own slack, marked `verspätet` (`late`) when below zero. It links each bulk lot that belongs to the task through its batch. A signed-in user sees a link `Bearbeiten` (`Edit`) and the actions that apply, and on an ended task with a batch a link `Als Bulk erfassen` (`Record as bulk`) to `/lab/inventory/bulk/new/` with `substance`, `batch` and `made_on` filled in: the task's substance's key, its batch and its end date.

#### Scenario: Task with a sequence
- **WHEN** the index is the demo collection's and a test client requests the page of a task with the sequence `SEQ-0001` and `steps_done` 1
- **THEN** it lists `OSDB-0001`, marked done, and `OSDB-0002`, each linking to its procedure, and shows no edit link when not signed in

#### Scenario: Forecast of the product
- **WHEN** on 2026-11-04 with the default parameters a test client requests the page of a planned task that matches an article of one 1 mg item with 10 containers, `m` 9, `v` 9 and no bulk
- **THEN** it shows the article number linking to `/lab/planning/`, the runway 60 days, the synthesis time 21 days, the slack 11 days, the latest start 2026-11-15 and the task's slack 11 days

### Requirement: Task actions
For a signed-in user, the task's page SHALL offer these buttons, each a POST to `/lab/tasks/<number>/<action>/` that changes the task, records the change in its history and returns to the page with a message:

- `start`, `Beginnen` (`Start`), on a planned task: sets `started` to today;
- `step`, `Stufe erledigt` (`Step done`), on a running task whose `steps_done` is below `steps_total`: adds one to `steps_done`;
- `end`, `Abschließen` (`End`), on a running task: sets `ended` to today, and `steps_done` to `steps_total` when there is a total;
- `report` and `qc-list`, `Bericht erledigt` (`Report done`) and `Auf QC-Liste` (`On QC list`), on an ended task with that flag off: set the flag.

An action that does not apply to the task's current state changes nothing and returns to the page with an error message.

#### Scenario: Steps through actions
- **WHEN** a signed-in user starts a planned task with `steps_total` 2 on 2026-11-04, posts `step`, then `end` on 2026-11-06
- **THEN** the task has `started` 2026-11-04, `ended` 2026-11-06 and `steps_done` 2, and its history lists three changes

#### Scenario: Action out of state
- **WHEN** a signed-in user posts `step` to a planned task
- **THEN** the task is unchanged and the page shows an error message

### Requirement: Task forms
`/lab/tasks/new/` SHALL create a task and `/lab/tasks/<number>/edit/` change one, for a signed-in user. The form holds the substance by key, offered through the substances' `datalist` as the inventory forms offer it, priority, assignee (every account, shown as initials and display name, or none), start and end dates, sequence, steps total, steps done, batch, report, QC list, cancelled (on the edit form only) and note. Invalid input, among it an unknown substance, an end without a start or before it, steps done above the total, and a sequence the index lacks, shows the form again with the errors beside their fields and saves nothing. A saved form leads to the task's page with the message `Aufgabe <number> gespeichert.` (`Task <number> saved.`). The creating user becomes `created_by`. The priority field carries the help text `Gilt, solange keine Prognose die Priorität berechnet.` (`Applies while no forecast computes the priority.`). The new-task form fills in a substance key given as the GET parameter `substance`.

#### Scenario: Creating a task
- **WHEN** user `KL` posts the substance `cinnamic-acid`, priority `high` and assignee `AE` to `/lab/tasks/new/`
- **THEN** a planned task `T-<n>` exists with `created_by` `KL`, and the response redirects to its page, which shows the message and `(E)-Zimtsäure`

#### Scenario: End before start
- **WHEN** a signed-in user posts a task started 2026-11-05 and ended 2026-11-04
- **THEN** the form shows again with an error at the end date, and nothing is saved

#### Scenario: Substance from the query
- **WHEN** a signed-in user requests `/lab/tasks/new/?substance=cinnamic-acid`
- **THEN** the form's substance field holds `cinnamic-acid`

### Requirement: Tasks in the admin
The admin SHALL list tasks and accounts for staff, with search by number, the substance's key and names, and batch, and the change history of each task. Deleting a task in the admin does not free its number.

#### Scenario: Admin list
- **WHEN** a staff user requests `/lab/admin/tasks/task/`
- **THEN** the page lists the tasks by number

