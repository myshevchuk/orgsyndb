## MODIFIED Requirements

### Requirement: Task list
`/lab/tasks/` SHALL list tasks in a table with the columns `Nr.`, `Produkt`, `Priorität`, `Bearbeitung`, `Beginn`, `Ende`, `Fortschritt`, `Charge`, `Bericht`, `QC-Liste` and `Status` (`No.`, `Product`, `Priority`, `Assignee`, `Started`, `Ended`, `Progress`, `Batch`, `Report`, `QC list`, `State`): the number linking to the task's page; the product; the task's priority, computed or entered, with its mark, as `production-planning` states under Computed priority on tasks; the assignee's initials with the display name as title; the dates; the progress as `<steps_done>/<steps_total>` and a `progress` element, empty without a total; the batch; the two flags as `ja` or `nein` (`yes`, `no`); and the state as a badge with its label, followed by `Nacharbeit` (`Follow-up`) when the task needs it. Rows are ordered by that priority, high first, then by the task's slack, smallest first and tasks without one last, then by state, running before planned before ended before cancelled, then by start date, earliest first and tasks without one last, then by number. Above the table a line counts the tasks: `<p> geplant · <r> in Arbeit · <f> Nacharbeit` (`<p> planned · <r> running · <f> follow-up`). There is no paging. A signed-in user sees a link `Neue Aufgabe` (`New task`).

The list filters with GET parameters in a form above it, and each filter keeps its value in the form:

- `state`: `active` (planned, running, and ended needing follow-up; the default), `planned`, `running`, `followup`, `ended`, `cancelled` or `all`;
- `person`: an account's initials, or `none` for tasks without an assignee;
- `priority`: `high`, `medium` or `low`, compared with the task's priority, computed or entered;
- `q`: text found, regardless of case, in the number, the product, the name of the product's compound, the batch or the note.

An unknown value of a filter is ignored, with the default in its place.

#### Scenario: Default view
- **WHEN** the database holds a planned task of priority low, a running task of priority high, an ended task with both flags on, an ended task of priority low without the report, and a cancelled task, and a test client requests `/lab/tasks/`
- **THEN** the table lists the running task, the planned task and the ended task without the report, in that order, the last marked `Nacharbeit`, and the count reads `1 geplant · 1 in Arbeit · 1 Nacharbeit`

#### Scenario: Filters
- **WHEN** the index is the demo collection's and a test client requests `/lab/tasks/?state=all&person=KL&q=zimt`
- **THEN** the table lists exactly the tasks of `KL`, in any state, whose number, product, compound name, batch or note contains `zimt` in any case, among them a task with the product `CH-0012`, and the form shows `all`, `KL` and `zimt`

#### Scenario: Computed over entered
- **WHEN** a planned task with the entered priority low matches an article whose slack is 11 days, a running task with the entered priority high matches no article, a planned task has the entered priority medium, and a test client requests `/lab/tasks/` and `/lab/tasks/?priority=high`
- **THEN** both list the first task with `hoch` and `berechnet`; the first lists it before the task of medium priority, and the second lists the first two tasks and not the third

### Requirement: Task page
`/lab/tasks/<number>/` SHALL show the number and the product as heading, then the state, follow-up, priority with its mark, assignee, dates, progress, batch, the two flags, note, the creating user and time, and the change history. A task with a sequence shows the sequence's ID linking to `/sequences/<ID in lower case>/` and its `sequence_steps` as an ordered list, each procedure linking to `/procedures/<ID in lower case>/`, the first `steps_done` steps marked `erledigt` (`done`); a sequence or procedure the current index lacks shows with the mark `nicht in der Sammlung` and no link. For each article of the inventory `end-products` the task matches, it shows the article number linking to `/lab/planning/` and, for an article without a forecast, `Kein Verbrauch, keine Prognose.` (`No consumption, no forecast.`), else the article's runway, synthesis time, slack and latest start, and, for a planned or running task, the task's own slack, marked `verspätet` (`late`) when below zero. It links each bulk lot that belongs to the task through its batch. A signed-in user sees a link `Bearbeiten` (`Edit`) and the actions that apply, and on an ended task with a batch and a matching article a link `Als Bulk erfassen` (`Record as bulk`) to `/lab/inventory/bulk/new/` with `article`, `batch` and `made_on` filled in: the first matching article number in alphabetical order, the task's batch and its end date.

#### Scenario: Task with a sequence
- **WHEN** the index is the demo collection's and a test client requests the page of a task with the sequence `SEQ-0001` and `steps_done` 1
- **THEN** it lists `OSDB-0001`, marked done, and `OSDB-0002`, each linking to its procedure, and shows no edit link when not signed in

#### Scenario: Forecast of the product
- **WHEN** on 2026-11-04 with the default parameters a test client requests the page of a planned task that matches an article of one 1 mg item with 10 containers, `m` 9, `v` 9 and no bulk
- **THEN** it shows the article number linking to `/lab/planning/`, the runway 60 days, the synthesis time 21 days, the slack 11 days, the latest start 2026-11-15 and the task's slack 11 days

### Requirement: Task forms
`/lab/tasks/new/` SHALL create a task and `/lab/tasks/<number>/edit/` change one, for a signed-in user. The form holds the product with the compound `datalist`, priority, assignee (every account, shown as initials and display name, or none), start and end dates, sequence, steps total, steps done, batch, report, QC list, cancelled (on the edit form only) and note. Invalid input, among it an end without a start or before it, steps done above the total, and a sequence the index lacks, shows the form again with the errors beside their fields and saves nothing. A saved form leads to the task's page with the message `Aufgabe <number> gespeichert.` (`Task <number> saved.`). The creating user becomes `created_by`. The priority field carries the help text `Gilt, solange keine Prognose die Priorität berechnet.` (`Applies while no forecast computes the priority.`). The new-task form fills in a `product` given as a GET parameter.

#### Scenario: Creating a task
- **WHEN** user `KL` posts the product `CH-0012`, priority `high` and assignee `AE` to `/lab/tasks/new/`
- **THEN** a planned task `T-<n>` exists with `created_by` `KL`, and the response redirects to its page, which shows the message and `(E)-Zimtsäure`

#### Scenario: End before start
- **WHEN** a signed-in user posts a task started 2026-11-05 and ended 2026-11-04
- **THEN** the form shows again with an error at the end date, and nothing is saved

#### Scenario: Product from the query
- **WHEN** a signed-in user requests `/lab/tasks/new/?product=CH-0012`
- **THEN** the form's product field holds `CH-0012`
