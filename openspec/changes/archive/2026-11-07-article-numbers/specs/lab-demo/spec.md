## MODIFIED Requirements

### Requirement: Demo inventory
The data set SHALL open the inventory on the opening day `O`, `D` less 400 days, and hold in the inventory `end-products`:

- items of seven articles: `CH-0001`, `CH-0002`, `CH-0010`, `CH-0012`, `CH-0013` and `CH-0016`, the final products of `examples/demo` that set `item_number`, each item named as its compound is there, with `name_de` when the language is German; and `NV-0007`, named `Neuverbindung 7` (`New compound 7`), which names no compound of `examples/demo`. At least one article has three sizes, and the sizes use the units `mg`, `g` and `umol`;
- one item without an article number, named `1-Phenylethanol` as the compound `1-phenylethanol` of `examples/demo`, opened after `O`, filled without a lot and never delivered;
- each item's opening count, dated `O`, or later for a size added afterwards;
- for the items that have them, entered consumption for each of the seven quarters from the eighth before the quarter of `O` to the second before it, entered in the 30 days from `O`;
- historical delivery notes dated from the first day of the quarter before that of `O` to the day before `O`, entered in the 30 days from `O`, one of them later reversed with a note;
- current delivery notes from `O` on, each with a recipient, some with several lines;
- every delivery note numbered `LS-<year>-<nnn>`, where `<year>` is the year of its date and `<nnn>` counts the notes of that year in the order of their dates from `001`;
- one delivery reversed with a note, and one correction with a note;
- bulk lots, each with a batch, a location and the date it was made, and fillings from them, each naming its lot's movement; one lot used up, one lot corrected with a note, and one lot of `NV-0007` in `umol`.

#### Scenario: Item list
- **WHEN** the data set is written as of `D` with the demo collection's index and a test client requests `/lab/inventory/end-products/`
- **THEN** the list shows the seven article numbers, the name of each item of the six final products linking to its compound's page, the name `Neuverbindung 7` without a link to a compound, and last the item `1-Phenylethanol` without an article number, its name linking to its page

#### Scenario: Levels on any seeding day
- **WHEN** the data set is written, each time into an empty database, as of 2026-01-01, 2026-02-14, 2026-03-31, 2026-11-07 and 2028-02-29, with the demo collection's index, and a test client requests `/lab/inventory/end-products/` on that day
- **THEN** on each day the list has stock cells with each of the classes `level-out`, `level-critical`, `level-low` and `level-watch`, and at least one stock cell with none of them

#### Scenario: Notes
- **WHEN** the data set is written as of `D` and a test client requests the delivery list
- **THEN** it lists notes numbered `LS-<year>-<nnn>`, historical notes among them, one historical note shown as reversed, and one current note shown as reversed or partly reversed

### Requirement: Demo tasks and parameters
The data set SHALL hold tasks for the articles of the demo inventory and for its item without an article number, each checked by the task's own validation before every save, as a form's would be, and numbered in the order they were created:

- tasks in each state: planned, running, ended with `report` and `qc_list` on, ended needing follow-up, and cancelled; on `D` the task list's default filter counts at least two planned, three running and two follow-up tasks;
- at least three ended tasks matching `CH-0012`, so that its synthesis time is `längste der letzten 3 Synthesen`;
- tasks of the sequences `SEQ-0001`, product `CH-0010`, with the steps `OSDB-0001` and `OSDB-0002`, and `SEQ-0002`, product `CH-0002`, with the steps `OSDB-0004` and `OSDB-0009`, the steps written from the data set and not read from the index; one of them running with one of two steps done;
- one task whose product is the compound key `cinnamic-acid` and not an item number, and one without an assignee;
- an ended task of the item without an article number, its product the compound key `1-phenylethanol`, with a batch and no lot;
- other ended tasks with batches, and bulk lots of the same batches, so that each such task lists its lots and each lot its task.

The planning parameters are stored, created with `target_days` 180 more than a year before `D` and changed to 365 since, every other value the default.

#### Scenario: Task list
- **WHEN** the data set is written as of `D` with the demo collection's index and a test client requests `/lab/tasks/` and `/lab/tasks/?state=all`
- **THEN** the first counts at least 2 planned, 3 running and 2 follow-up tasks, and the second shows each of the states `Geplant`, `In Arbeit`, `Abgeschlossen` and `Verworfen`

#### Scenario: Parameters with a history
- **WHEN** the data set is written and a test reads the stored planning parameters
- **THEN** their `target_days` is 365, every other value is its default, and their history lists a change of `target_days` from 180 to 365

### Requirement: Demo planning
On `D`, under the data set's parameters and with the demo collection's index, the planning list SHALL show without `all=1` exactly the articles `CH-0012`, `CH-0013`, `CH-0010`, `CH-0016` and `NV-0007`:

- `CH-0012` with priority high and a running task marked `verspätet`, its figures from the order model;
- `CH-0013` with priority high, no task, and `Synthese planen`;
- `CH-0010` with priority medium, a planned task of `SEQ-0001`, and no `Synthese planen`;
- `CH-0016` with priority low and `Abfüllen` for one of its sizes;
- `NV-0007` with `Bulk prüfen` and no `Synthese planen`.

With `all=1` it also shows `CH-0001`, with priority low and its figures marked `grob`, and `CH-0002`, with priority low and a running task not marked late, and no other article. The item without an article number has no forecast; its item page shows `Kein Verbrauch, keine Prognose.`

#### Scenario: Any seeding day
- **WHEN** the data set is written, each time into an empty database, as of 2026-01-01, 2026-02-14, 2026-03-31, 2026-11-07 and 2028-02-29, and a test client requests `/lab/planning/` and `/lab/planning/?all=1` on that day
- **THEN** on each day both lists show the articles, priorities, tasks and actions this requirement names
