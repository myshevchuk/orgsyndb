## MODIFIED Requirements

### Requirement: Demo data command
`manage.py demo_data` SHALL write the demo data set as of today in `Europe/Berlin`, `D`, into the database, all in one transaction, so that a failure leaves the database as it was, its records, histories and task counter included. Lab records are accounts, substances, vocabulary terms, articles, tasks, items, delivery notes, bulk lots, entered consumption values, stored planning parameters, the collection's imports with their procedures, scope entries and sequences (collection-import "Imported rows"), change-history records and the demo mark. The command writes only with `ORGSYNDB_DEMO` true:

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

#### Scenario: Replacing after an import
- **WHEN** the demo data set is written, an import of the demo collection is accepted, and `demo_data --replace` runs with `ORGSYNDB_DEMO` true
- **THEN** it exits 0, no import, procedure or sequence remains, and the snapshot's `import` is `null`
