## MODIFIED Requirements

### Requirement: Demo data command
`manage.py demo_data` SHALL write the demo data set as of today in `Europe/Berlin`, `D`, into the database, all in one transaction, so that a failure leaves the database as it was, its records, histories and task counter included. Lab records are accounts, substances, vocabulary terms, articles, tasks, items, delivery notes, bulk lots, entered consumption values, stored planning parameters, change-history records and the demo mark. The command writes only with `ORGSYNDB_DEMO` true:

- without options, it exits 1 with a message and changes nothing when `ORGSYNDB_DEMO` is not true, the message naming `ORGSYNDB_DEMO`, or when the database holds lab records, the message naming `--replace`;
- `--replace` deletes every lab record, with the movements, lines and change histories that belong to them, sets the task counter to zero and writes the data set, when the database is a demo database or holds no lab records. On any other database it exits 1 with a message saying it replaces only a demo database, and changes nothing; when `ORGSYNDB_DEMO` is not true, it exits 1 as above;
- `--if-empty` writes the data set when `ORGSYNDB_DEMO` is true and the database holds no lab records, and otherwise exits 0, saying why, without changing anything.

`--replace` and `--if-empty` together are refused as a usage error, changing nothing. After the accounts, as the data set's first changes, on `O` and made by `klehmann` (Recorded past), the command loads the demo registry, `webapp/demo/registry.json`, as `registry_load` does (lab-registry "Loading a registry"). On success it prints how many accounts, substances, items, delivery notes and tasks it wrote.

#### Scenario: Flag off
- **WHEN** `ORGSYNDB_DEMO` is unset and `demo_data` runs once without options and once with `--replace` on an empty database
- **THEN** both exit 1 with a message naming `ORGSYNDB_DEMO`, and the database stays empty

#### Scenario: Records present
- **WHEN** `ORGSYNDB_DEMO` is true, the database holds one account, and `demo_data` runs without options
- **THEN** it exits 1 with a message naming `--replace`, and that account is the only record

#### Scenario: Real records are not replaced
- **WHEN** `ORGSYNDB_DEMO` is true, the database holds an account `kl` and a task by it and no demo mark, and `demo_data --replace` runs
- **THEN** it exits 1, and `kl` and its task are the only records

#### Scenario: Replace a demo database
- **WHEN** `ORGSYNDB_DEMO` is true, the data set was written, a test then adds an account `kl` and a task by it, and `demo_data --replace` runs
- **THEN** `kl` and its task no longer exist, the five demo accounts do, and the task first created by the data set is `T-001`

#### Scenario: At start
- **WHEN** `demo_data --if-empty` runs with `ORGSYNDB_DEMO` unset on an empty database, with it true on a database holding one account, and with it true on an empty database
- **THEN** each exits 0, the first two change nothing, and the third writes the data set

#### Scenario: Failure changes nothing
- **WHEN** `ORGSYNDB_DEMO` is true and writing the data set fails partway, once on an empty database and once under `--replace` on a demo database
- **THEN** the command exits 1 each time, the first database is empty, and the second holds the records, histories and task counter it held before

#### Scenario: Options together
- **WHEN** `demo_data --replace --if-empty` runs
- **THEN** it is refused as a usage error and the database is unchanged

#### Scenario: No index
- **WHEN** `ORGSYNDB_DEMO` is true, `ORGSYNDB_INDEX` names a file that does not exist, and `demo_data` runs on an empty database
- **THEN** it exits 0 without a warning, and the data set is written, the substances of the demo registry included

### Requirement: Demo inventory
The data set SHALL open the inventory on the opening day `O`, `D` less 400 days, and hold:

- items of seven articles: `CH-0001`, `CH-0002`, `CH-0010`, `CH-0012`, `CH-0013` and `CH-0016`, the articles of the substances that set `item_number` in `examples/demo`; and `NV-0007`, the article of the substance `new-compound-7`, `Neuverbindung 7` (`New compound 7`), which the demo registry adds. At least one article has three sizes, and the sizes use the units `mg`, `g` and `umol`;
- one item of the substance `1-phenylethanol`, whose article has no article number, opened after `O`, filled without a lot 89 days before `D`, and never delivered;
- sizes that planning leaves out: `CH-0012` in 1 g, `discontinued`, and `CH-0010` in 25 g, `not_needed`, each set aside after its opening count and never delivered; and `CH-0001` in 250 mg, whose consumption is entered for the four quarters from the eighth to the fifth before the quarter of `O` and is none since;
- `CH-0013` in 1 g, opened 60 days before `D`, with a delivery of one container every 15 days from then on;
- each item's opening count, dated `O`, or later for a size added afterwards, and a compartment and a box, numbers such as `3` and `12`, the sizes of an article in one compartment;
- for the items that have them, entered consumption for each of the seven quarters from the eighth before the quarter of `O` to the second before it, and for `CH-0001` in 250 mg for the four from the eighth to the fifth, entered in the 30 days from `O`;
- historical delivery notes dated from the first day of the quarter before that of `O` to the day before `O`, entered in the 30 days from `O`, one of them later reversed with a note;
- current delivery notes from `O` on, each with a recipient, some with several lines;
- every delivery note numbered `LS-<year>-<nnn>`, where `<year>` is the year of its date and `<nnn>` counts the notes of that year in the order of their dates from `001`;
- one delivery reversed with a note, and one correction with a note;
- bulk lots, each with a batch, a location and the date it was made, and fillings from them, each naming its lot's movement; one lot used up, one lot corrected with a note, one lot of `NV-0007` in `umol`, one lot bought from a supplier, and one open lot, made in the lab, of a substance that has no article.

#### Scenario: Item list
- **WHEN** the data set is written as of `D` and a test client requests `/lab/inventory/end-products/`
- **THEN** the list shows the seven article numbers, the name of each item with an article number linking to its substance's page, `Neuverbindung 7` among them, and the item `1-Phenylethanol` without an article number after the other items of its category, its name linking to its page

#### Scenario: Levels on any seeding day
- **WHEN** the data set is written, each time into an empty database, as of 2026-01-01, 2026-02-14, 2026-03-31, 2026-11-07 and 2028-02-29, and a test client requests `/lab/inventory/end-products/` on that day
- **THEN** on each day the list has stock cells with each of the classes `level-out`, `level-critical`, `level-low`, `level-watch`, `level-ok`, `level-undelivered` and `level-dormant`

#### Scenario: Notes
- **WHEN** the data set is written as of `D` and a test client requests the delivery list
- **THEN** it lists notes numbered `LS-<year>-<nnn>`, historical notes among them, one historical note shown as reversed, and one current note shown as reversed or partly reversed

#### Scenario: New positions
- **WHEN** the data set is written as of 2026-11-07 and a test client requests `/lab/inventory/end-products/`
- **THEN** the items `1-Phenylethanol` and `CH-0013` of 1 g are marked `neu` and no other item is, and the means of `CH-0013` of 1 g are projected

### Requirement: Demo tasks and parameters
The data set SHALL hold tasks for the articles of the demo inventory and for its item without an article number, each checked by the task's own validation before every save, as a form's would be, and numbered in the order they were created:

- tasks in each state: planned, running, ended with `report` and `qc_list` on, ended needing follow-up, and cancelled; on `D` the task list's default filter counts at least two planned, three running and two follow-up tasks;
- at least three ended tasks matching `CH-0012`, so that its synthesis time is `längste der letzten 3 Synthesen`;
- tasks of the sequences `SEQ-0001`, of the substance of `CH-0010`, with the steps `OSDB-0001` and `OSDB-0002`, and `SEQ-0002`, of the substance of `CH-0002`, with the steps `OSDB-0004` and `OSDB-0009`, the steps written from the data set and not read from the index; one of them running with one of two steps done;
- one task without an assignee;
- an ended task of `1-phenylethanol`, whose article has no article number, with a batch and no lot;
- other ended tasks with batches, and bulk lots of the same batches, so that each such task lists its lots and each lot its task.

The planning parameters are stored, created with `target_days` 180 more than a year before `D` and changed to 365 since, every other value the default.

#### Scenario: Task list
- **WHEN** the data set is written as of `D` and a test client requests `/lab/tasks/` and `/lab/tasks/?state=all`
- **THEN** the first counts at least 2 planned, 3 running and 2 follow-up tasks, and the second shows each of the states `Geplant`, `In Arbeit`, `Abgeschlossen` and `Verworfen`

#### Scenario: Parameters with a history
- **WHEN** the data set is written and a test reads the stored planning parameters
- **THEN** their `target_days` is 365, every other value is its default, and their history lists a change of `target_days` from 180 to 365

### Requirement: Language of the demo texts
The data set's free texts, categories, notes, recipients and locations, SHALL be written in the language of the collection index, German when it has none. Its substances have names in both languages, shown as the language chooses (lab-registry "Substances").

#### Scenario: English index
- **WHEN** the data set is written with an index whose language is `en`
- **THEN** the item `NV-0007` is named `New compound 7` and the item `CH-0012` `(E)-Cinnamic acid`

#### Scenario: Same records whatever the index
- **WHEN** the data set is written as of one day, once with the demo collection's index and once with no index
- **THEN** both databases hold the same items by article number, size, unit and quantity, the same movements by kind, count and date, the same lots by batch and amount, and the same tasks by number, substance and dates

### Requirement: Demo planning
On `D`, under the data set's parameters, the planning list SHALL show without `all=1` exactly the articles `CH-0012`, `CH-0013`, `CH-0010`, `CH-0016` and `NV-0007`:

- `CH-0012` with priority high and a running task marked `verspätet`, its figures from the order model;
- `CH-0013` with priority high, no task, and `Synthese planen`;
- `CH-0010` with priority medium, a planned task of `SEQ-0001`, and no `Synthese planen`;
- `CH-0016` with priority low and `Abfüllen` for one of its sizes;
- `NV-0007` with `Bulk prüfen` and no `Synthese planen`.

With `all=1` it also shows `CH-0001`, with priority low and its figures marked `grob`, and `CH-0002`, with priority low and a running task not marked late, and no other article. The item without an article number has no forecast; its item page shows `Kein Verbrauch, keine Prognose.`

#### Scenario: Any seeding day
- **WHEN** the data set is written, each time into an empty database, as of 2026-01-01, 2026-02-14, 2026-03-31, 2026-11-07 and 2028-02-29, and a test client requests `/lab/planning/` and `/lab/planning/?all=1` on that day
- **THEN** on each day both lists show the articles, priorities, tasks and actions this requirement names
