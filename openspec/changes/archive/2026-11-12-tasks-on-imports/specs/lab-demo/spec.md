## MODIFIED Requirements

### Requirement: Demo data command
`manage.py demo_data` SHALL write the demo data set as of today in `Europe/Berlin`, `D`, into the database, all in one transaction, so that a failure leaves the database as it was, its records, histories and task counter included. Lab records are accounts, substances, vocabulary terms, articles, tasks, items, delivery notes, bulk lots, entered consumption values, stored planning parameters, the collection's imports with their procedures, scope entries and sequences (collection-import "Imported rows"), change-history records and the demo mark. The command writes only with `ORGSYNDB_DEMO` true:

- without options, it exits 1 with a message and changes nothing when `ORGSYNDB_DEMO` is not true, the message naming `ORGSYNDB_DEMO`, or when the database holds lab records, the message naming `--replace`;
- `--replace` deletes every lab record, with the movements, lines and change histories that belong to them, sets the task counter to zero and writes the data set, when the database is a demo database or holds no lab records. On any other database it exits 1 with a message saying it replaces only a demo database, and changes nothing; when `ORGSYNDB_DEMO` is not true, it exits 1 as above;
- `--if-empty` writes the data set when `ORGSYNDB_DEMO` is true and the database holds no lab records, and otherwise exits 0, saying why, without changing anything.

`--replace` and `--if-empty` together are refused as a usage error, changing nothing. After the accounts, as the data set's first changes, on `O` and made by `klehmann` (Recorded past), the command loads the demo registry, `webapp/demo/registry.json`, as `registry_load` does (lab-registry "Loading a registry"). Then, on `O`, it records an accepted import of the demo collection from `webapp/demo/manifest.json`, the output of `tools/orgsyndb manifest` for the demo collection, as the manifest view applies one (collection-import "Applying an import"), with the commit of forty zeros, the release `demo`, the trigger `catch-up`, no base, the current snapshot's digest and the language of the demo texts (Language of the demo texts); the builder's next cycle replaces it with an import of a real build. On success it prints how many accounts, substances, items, delivery notes and tasks it wrote.

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

### Requirement: Demo tasks and parameters
The data set SHALL hold tasks for the articles of the demo inventory and for its item without an article number, each checked by the task's own validation before every save, as a form's would be, and numbered in the order they were created:

- tasks in each state: planned, running, ended with `report` and `qc_list` on, ended needing follow-up, and cancelled; on `D` the task list's default filter counts at least two planned, three running and two follow-up tasks;
- at least three ended tasks matching `CH-0012`, so that its synthesis time is `längste der letzten 3 Synthesen`;
- tasks of the sequences `SEQ-0001`, of the substance of `CH-0010`, and `SEQ-0002`, of the substance of `CH-0002`, of the data set's import, each with one step per step of its sequence (task-tracker "Task record"); one of them running with the first of its two steps done;
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
The data set's free texts, categories, notes, recipients and locations, SHALL be written in the language of the latest accepted import the database holds before the command deletes anything, German when it holds none. Its substances have names in both languages, shown as the language chooses (lab-registry "Substances").

#### Scenario: English collection
- **WHEN** an import of language `en` was accepted and the data set is written with `--replace`
- **THEN** the item `NV-0007` is named `New compound 7` and the item `CH-0012` `(E)-Cinnamic acid`

#### Scenario: Same records whatever the language
- **WHEN** the data set is written as of one day, once over an accepted import of language `en` and once on an empty database
- **THEN** both databases hold the same items by article number, size, unit and quantity, the same movements by kind, count and date, the same lots by batch and amount, and the same tasks by number, substance and dates
