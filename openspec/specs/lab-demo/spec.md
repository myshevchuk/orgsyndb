# lab-demo Specification

## Purpose
Fill a test deployment's lab database with the records of an invented lab, dated back from the day it is seeded: the demo accounts, inventory, tasks and planning parameters, written through the application's own write paths by `manage.py demo_data`, only with `ORGSYNDB_DEMO` set, and marked so that every page of a demo database says its records are invented.
## Requirements
### Requirement: Demo database
A database SHALL be a demo database when it holds the demo mark, which the demo data set writes with the day `D` it was seeded as of. On a demo database, every page of the application but the admin's shows, as the first element of `main`, before the messages, a `p` with the class `lab-demo` and the text `Demo: Alle Einträge sind erfunden (Stand: <D>).` (`Demo: All records are invented (as of <D>).`), `<D>` in the date format of the interface language. Its sign-in page shows, below the form, an element with the class `lab-demo-accounts` listing the user names of the demo accounts that can sign in (Demo accounts), each with its display name, and the text `Passwort für alle: demo` (`Password for all: demo`). A database without the mark shows neither, whatever `ORGSYNDB_DEMO` says.

#### Scenario: Banner
- **WHEN** the data set is written as of 2026-11-07 and a test client requests `/lab/tasks/`, `/lab/planning/`, `/lab/inventory/end-products/` and `/lab/admin/login/`
- **THEN** the first three show `Demo: Alle Einträge sind erfunden (Stand: 07.11.2026).` as the first element of `main`, and the admin's page does not

#### Scenario: Sign-in note
- **WHEN** the data set is written and a test client requests `/lab/accounts/login/`
- **THEN** below the form it lists `klehmann`, `tbauer`, `aschmidt` and `jkoch` with their display names and the text `Passwort für alle: demo`, and does not list `mwolf`

#### Scenario: Not a demo database
- **WHEN** `ORGSYNDB_DEMO` is true, the database holds an account and a task but no demo mark, and a test client requests `/lab/tasks/` and `/lab/accounts/login/`
- **THEN** neither page has an element with the class `lab-demo` or `lab-demo-accounts`

### Requirement: Demo data command
`manage.py demo_data` SHALL write the demo data set as of today in `Europe/Berlin`, `D`, into the database, all in one transaction, so that a failure leaves the database as it was, its records, histories and task counter included. Lab records are accounts, tasks, items, delivery notes, bulk lots, entered consumption values, stored planning parameters, change-history records and the demo mark. The command writes only with `ORGSYNDB_DEMO` true:

- without options, it exits 1 with a message and changes nothing when `ORGSYNDB_DEMO` is not true, the message naming `ORGSYNDB_DEMO`, or when the database holds lab records, the message naming `--replace`;
- `--replace` deletes every lab record, with the movements, lines and change histories that belong to them, sets the task counter to zero and writes the data set, when the database is a demo database or holds no lab records. On any other database it exits 1 with a message saying it replaces only a demo database, and changes nothing; when `ORGSYNDB_DEMO` is not true, it exits 1 as above;
- `--if-empty` writes the data set when `ORGSYNDB_DEMO` is true and the database holds no lab records, and otherwise exits 0, saying why, without changing anything.

`--replace` and `--if-empty` together are refused as a usage error, changing nothing. When the collection index lacks a compound of `examples/demo` that the data set names, the command writes a warning to stderr naming how many it lacks, and writes the data set all the same. On success it prints how many accounts, items, delivery notes and tasks it wrote.

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
- **THEN** it warns on stderr that the index lacks the demo's compounds, exits 0, and the data set is written

### Requirement: Demo accounts
The data set SHALL hold five accounts:

| User name  | Name           | Initials | Account                    |
|------------|----------------|----------|----------------------------|
| `klehmann` | Katrin Lehmann | `KL`     | superuser and staff        |
| `tbauer`   | Tobias Bauer   | `TB`     |                            |
| `aschmidt` | Anna Schmidt   | `AS`     |                            |
| `jkoch`    | Jonas Koch     | `JK`     |                            |
| `mwolf`    | Miriam Wolf    | `MW`     | without a usable password  |

Every account but `mwolf` has the password `demo`. `mwolf` is named on records made more than a year before `D` and on none made later.

#### Scenario: Signing in
- **WHEN** the data set is written and a test client signs in as `tbauer`, as `klehmann` and as `mwolf`, each with the password `demo`
- **THEN** the first two succeed and `klehmann` reaches `/lab/admin/`, and the third fails

### Requirement: Demo inventory
The data set SHALL open the inventory on the opening day `O`, `D` less 400 days, and hold in the inventory `end-products`:

- items of eight articles: `CH-0001`, `CH-0002`, `CH-0003`, `CH-0010`, `CH-0012`, `CH-0013` and `CH-0016`, the in-house final products of `examples/demo`, each item named as its compound is there, with `name_de` when the language is German; and `NV-0007`, named `Neuverbindung 7` (`New compound 7`), which names no compound of `examples/demo`. At least one article has three sizes, and the sizes use the units `mg`, `g` and `umol`;
- each item's opening count, dated `O`, or later for a size added afterwards;
- for the items that have them, entered consumption for each of the seven quarters from the eighth before the quarter of `O` to the second before it, entered in the 30 days from `O`;
- historical delivery notes dated from the first day of the quarter before that of `O` to the day before `O`, entered in the 30 days from `O`, one of them later reversed with a note;
- current delivery notes from `O` on, each with a recipient, some with several lines;
- every delivery note numbered `LS-<year>-<nnn>`, where `<year>` is the year of its date and `<nnn>` counts the notes of that year in the order of their dates from `001`;
- one delivery reversed with a note, and one correction with a note;
- bulk lots, each with a batch, a location and the date it was made, and fillings from them, each naming its lot's movement; one lot used up, one lot corrected with a note, and one lot of `NV-0007` in `umol`.

#### Scenario: Item list
- **WHEN** the data set is written as of `D` with the demo collection's index and a test client requests `/lab/inventory/end-products/`
- **THEN** the list shows the eight article numbers, the name of each item but those of `NV-0007` linking to its compound's page, and the name `Neuverbindung 7` without a link

#### Scenario: Levels on any seeding day
- **WHEN** the data set is written, each time into an empty database, as of 2026-01-01, 2026-02-14, 2026-03-31, 2026-11-07 and 2028-02-29, with the demo collection's index, and a test client requests `/lab/inventory/end-products/` on that day
- **THEN** on each day the list has stock cells with each of the classes `level-out`, `level-critical`, `level-low` and `level-watch`, and at least one stock cell with none of them

#### Scenario: Notes
- **WHEN** the data set is written as of `D` and a test client requests the delivery list
- **THEN** it lists notes numbered `LS-<year>-<nnn>`, historical notes among them, one historical note shown as reversed, and one current note shown as reversed or partly reversed

### Requirement: Demo tasks and parameters
The data set SHALL hold tasks for the articles of the demo inventory, each checked by the task's own validation before every save, as a form's would be, and numbered in the order they were created:

- tasks in each state: planned, running, ended with `report` and `qc_list` on, ended needing follow-up, and cancelled; on `D` the task list's default filter counts at least two planned, three running and two follow-up tasks;
- at least three ended tasks matching `CH-0012`, so that its synthesis time is `längste der letzten 3 Synthesen`;
- tasks of the sequences `SEQ-0001`, product `CH-0010`, with the steps `OSDB-0001` and `OSDB-0002`, and `SEQ-0002`, product `CH-0002`, with the steps `OSDB-0004` and `OSDB-0009`, the steps written from the data set and not read from the index; one of them running with one of two steps done;
- one task whose product is the compound key `cinnamic-acid` and not an item number, and one without an assignee;
- ended tasks with batches, and bulk lots of the same batches, so that each such task lists its lots and each lot its task.

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

With `all=1` it also shows `CH-0001`, with priority low and its figures marked `grob`, and `CH-0002`, with priority low and a running task not marked late. `CH-0003` has no forecast; its item page shows `Kein Verbrauch, keine Prognose.`

#### Scenario: Any seeding day
- **WHEN** the data set is written, each time into an empty database, as of 2026-01-01, 2026-02-14, 2026-03-31, 2026-11-07 and 2028-02-29, and a test client requests `/lab/planning/` and `/lab/planning/?all=1` on that day
- **THEN** on each day both lists show the articles, priorities, tasks and actions this requirement names

### Requirement: Recorded past
The data set SHALL be written as a sequence of changes, each made at its own moment: a day from `O` to `D` and a time between 08:00 and 18:00 in `Europe/Berlin`, the moments rising in the order the changes are made. Each change is made with the application's clock at its moment, so that every time a change stamps, a movement's `booked_at`, a delivery note's or task's `created_at`, an entered value's `entered_at` and a change-history record's time, is that moment, and each history record names the account that made the change. A movement is dated the day it is made, and a task's start or end never lies after the day of the change that sets it. The dates and quarters records name may lie before `O`: historical notes and entered consumption describe the time before the inventory, and are entered in its first 30 days. An item's movements, newest first, are therefore in descending order of date, and task numbers ascend with `created_at`. A task's history holds its creation and each later change of its dates, steps or flags at the moment it was made.

#### Scenario: Item history
- **WHEN** the data set is written as of `D` and a test client requests the page of an item opened on `O`
- **THEN** its oldest movement is the opening count, dated `O`, its movements are in descending order of date, and its history's creation entry is dated `O`

#### Scenario: Task history
- **WHEN** the data set is written as of `D` and a test reads the history of the running task of `CH-0012`
- **THEN** it holds the task's creation and a later change setting `started`, the first dated before the second, the second on the task's start date

#### Scenario: Times within the inventory's life
- **WHEN** the data set is written as of `D`
- **THEN** every `booked_at`, `created_at`, `entered_at` and change-history time lies from `O` to `D`, and every movement's date and task's start and end lies on or before `D`

### Requirement: Language of the demo texts
The data set's free texts, the names of items without a compound, categories, notes, recipients and locations, SHALL be written in the language of the collection index, German when it has none.

#### Scenario: English index
- **WHEN** the data set is written with an index whose language is `en`
- **THEN** the item `NV-0007` is named `New compound 7` and the item `CH-0012` `(E)-Cinnamic acid`

#### Scenario: Same records whatever the index
- **WHEN** the data set is written as of one day, once with the demo collection's index and once with no index
- **THEN** both databases hold the same items by article number, size, unit and quantity, the same movements by kind, count and date, the same lots by batch and amount, and the same tasks by number, product and dates

