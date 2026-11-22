## MODIFIED Requirements

### Requirement: Demo inventory
The data set SHALL open the inventory on the opening day `O`, `D` less 400 days, and hold:

- items of seven articles: `CH-0001`, `CH-0002`, `CH-0010`, `CH-0012`, `CH-0013` and `CH-0016`, the articles of the substances that set `item_number` in `examples/demo`; and `NV-0007`, the article of the substance `new-compound-7`, `Neuverbindung 7` (`New compound 7`), which the demo registry adds. At least one article has three sizes, and the sizes use the units `mg`, `g` and `umol`;
- one item of the substance `1-phenylethanol`, whose article has no article number, opened after `O`, filled 89 days before `D` from the flask of the product batch of its task, which ends after that filling, and never delivered;
- sizes that planning leaves out: `CH-0012` in 1 g, `discontinued`, and `CH-0010` in 25 g, `not_needed`, each set aside after its opening count and never delivered; and `CH-0001` in 250 mg, whose consumption is entered for the four quarters from the eighth to the fifth before the quarter of `O` and is none since;
- `CH-0013` in 1 g, opened 60 days before `D`, with a delivery of one container every 15 days from then on;
- each item's opening count, dated `O`, or later for a size added afterwards, and a compartment and a box, numbers such as `3` and `12`, the sizes of an article in one compartment;
- for the items that have them, entered consumption for each of the seven quarters from the eighth before the quarter of `O` to the second before it, and for `CH-0001` in 250 mg for the four from the eighth to the fifth, entered in the 30 days from `O`;
- historical delivery notes dated from the first day of the quarter before that of `O` to the day before `O`, entered in the 30 days from `O`, one of them later reversed with a note;
- current delivery notes from `O` on, each with a recipient, some with several lines;
- every delivery note numbered `LS-<year>-<nnn>`, where `<year>` is the year of its date and `<nnn>` counts the notes of that year in the order of their dates from `001`;
- one delivery reversed with a note, and one correction with a note;
- batches and vessels: made batches recorded from task steps, each naming its step's journal entry where the step names one, two of them naming one entry; made batches recorded without a step, each with its number, the date it was made and a stored vessel with a location; a batch of `NV-0007` with a vessel in `umol`; a batch bought from a supplier, with the supplier's article number and batch; and an open vessel of a made batch of a substance that has no article;
- fillings, each from a vessel and naming its movement; one vessel used up, one corrected with a note, and one transfer from a flask into a stored vessel.

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

- tasks in each state: planned, running, ended with `report` and `qc_list` on, ended needing follow-up, failed, and cancelled; on `D` the task list's default filter counts at least two planned, three running and two follow-up tasks;
- at least three ended tasks matching `CH-0012`, so that its synthesis time is `längste der letzten 3 Synthesen`;
- tasks of the sequences `SEQ-0001`, of the substance of `CH-0010`, and `SEQ-0002`, of the substance of `CH-0002`, of the data set's import, each with one step per step of its sequence from the one it starts at (task-tracker "Task record"); the first step of an ended task of `SEQ-0001` made a batch of salicylic acid, stored in a vessel, from which the planned task of `SEQ-0001` starts at its second step; one of them running with the first of its two steps done, which made a batch of its intermediate whose flask was withdrawn in part into its second step;
- one task without an assignee;
- an ended task of `1-phenylethanol`, whose article has no article number, with its product batch;
- every other ended task that has not failed with a product batch recorded from its last step, so that each such task lists its batches and each batch its task;
- no flask of a task that is ended, failed or cancelled holding an amount.

The planning parameters are stored, created with `target_days` 180 more than a year before `D` and changed to 365 since, every other value the default.

#### Scenario: Task list
- **WHEN** the data set is written as of `D` and a test client requests `/lab/tasks/` and `/lab/tasks/?state=all`
- **THEN** the first counts at least 2 planned, 3 running and 2 follow-up tasks, and the second shows each of the states `Geplant`, `In Arbeit`, `Abgeschlossen` and `Verworfen`

#### Scenario: Parameters with a history
- **WHEN** the data set is written and a test reads the stored planning parameters
- **THEN** their `target_days` is 365, every other value is its default, and their history lists a change of `target_days` from 180 to 365

#### Scenario: Ended tasks have their batches
- **WHEN** the data set is written as of `D`
- **THEN** every ended task that has not failed has a product batch, one task is failed and has none, one batch was made by a task step and its flask has a withdrawal into another step of the same task, and no flask of a task that is ended, failed or cancelled holds an amount

#### Scenario: A demo task from stock
- **WHEN** the demo data set is written and a test client requests the page of the planned task of `SEQ-0001`
- **THEN** it shows `SEQ-0001 ab Stufe 2` and one step, of `OSDB-0002`, and an open vessel of `salicylic-acid` belongs to a batch whose page names the first step of an ended task of `SEQ-0001` as the step that made it

### Requirement: Language of the demo texts
The data set's free texts, categories, notes, recipients and locations, SHALL be written in the language of the latest accepted import the database holds before the command deletes anything, German when it holds none. Its substances have names in both languages, shown as the language chooses (lab-registry "Substances").

#### Scenario: English collection
- **WHEN** an import of language `en` was accepted and the data set is written with `--replace`
- **THEN** the item `NV-0007` is named `New compound 7` and the item `CH-0012` `(E)-Cinnamic acid`

#### Scenario: Same records whatever the language
- **WHEN** the data set is written as of one day, once over an accepted import of language `en` and once on an empty database
- **THEN** both databases hold the same items by article number, size, unit and quantity, the same movements by kind, count and date, the same batches by number, the same vessels by batch and amount, and the same tasks by number, substance and dates

### Requirement: Demo data command
`manage.py demo_data` SHALL write the demo data set as of today in `Europe/Berlin`, `D`, into the database, all in one transaction, so that a failure leaves the database as it was, its records, histories and task counter included. Lab records are accounts with their access tokens, notebooks with their entries, substances, vocabulary terms, articles, tasks, items, delivery notes, batches with their vessels, entered consumption values, stored planning parameters, the collection's imports with their procedures, scope entries and sequences, issued IDs (collection-import "Imported rows"), change-history records and the demo mark. The command writes only with `ORGSYNDB_DEMO` true:

- without options, it exits 1 with a message and changes nothing when `ORGSYNDB_DEMO` is not true, the message naming `ORGSYNDB_DEMO`, or when the database holds lab records, the message naming `--replace`;
- `--replace` deletes every lab record, with the movements, lines and change histories that belong to them, sets the task counter to zero and writes the data set, when the database is a demo database or holds no lab records. On any other database it exits 1 with a message saying it replaces only a demo database, and changes nothing; when `ORGSYNDB_DEMO` is not true, it exits 1 as above;
- `--if-empty` writes the data set when `ORGSYNDB_DEMO` is true and the database holds no lab records, and otherwise exits 0, saying why, without changing anything.

`--replace` and `--if-empty` together are refused as a usage error, changing nothing. After the accounts, as the data set's first changes, on `O` and made by `klehmann` (Recorded past), the command loads the demo registry, `webapp/demo/registry.json`, as `registry_load` does (lab-registry "Loading a registry"), and registers the demo notebooks (Demo notebooks). Then, on `O`, it records an accepted import of the demo collection from `webapp/demo/manifest.json`, the output of `tools/orgsyndb manifest` for the demo collection, as the manifest view applies one (collection-import "Applying an import"), adopting its IDs (collection-import "Issued IDs"), with the commit of forty zeros, the release `demo`, the trigger `catch-up`, no base, the current snapshot's digest and the language of the demo texts (Language of the demo texts); the builder's next cycle replaces it with an import of a real build. On success it prints how many accounts, substances, items, delivery notes and tasks it wrote.

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

#### Scenario: The data set's import
- **WHEN** `ORGSYNDB_DEMO` is true and `demo_data` runs on an empty database
- **THEN** it exits 0, one accepted import exists, with the release `demo` and the trigger `catch-up`, and the procedures `OSDB-0001` to `OSDB-0009` and the sequences `SEQ-0001` and `SEQ-0002` exist, none withdrawn

#### Scenario: Replacing after an import
- **WHEN** the demo data set is written, an import of the demo collection is accepted, and `demo_data --replace` runs with `ORGSYNDB_DEMO` true
- **THEN** it exits 0, the only import is the data set's own, the snapshot's `import` names it, and no procedure or sequence remains that the demo manifest lacks
