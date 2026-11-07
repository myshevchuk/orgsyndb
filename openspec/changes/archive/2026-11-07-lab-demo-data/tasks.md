## 1. Tests

- [x] 1.1 Settings: `ORGSYNDB_DEMO` unset, true and malformed
- [x] 1.2 Demo database: the banner with its day on the lab's pages
  and not the admin's; the sign-in note; neither without the mark,
  whatever the flag
- [x] 1.3 The change list as plain data: moments from `O` to `D` and
  rising, every replayed quantity and amount at least zero
- [x] 1.4 Command: flag off, records present, real records not
  replaced, a demo database replaced, `--if-empty`, both options
  together, a failure partway on an empty and a demo database, no
  index
- [x] 1.5 Accounts and signing in
- [x] 1.6 Inventory: articles, units, notes, reversals, correction,
  lots, and the levels on each of the five seeding days
- [x] 1.7 Tasks, sequences, batches and the stored parameters
- [x] 1.8 Planning on each of the five seeding days
- [x] 1.9 Recorded past: recording times from `O` to `D`, histories
  at their moments, the order of records and of task numbers
- [x] 1.10 Language of the texts; the same records whatever the index
- [x] 1.11 Dockerfile command and the example settings

## 2. Implementation

- [x] 2.1 `ORGSYNDB_DEMO` in the settings; the `demo` application
  with the demo mark; the banner and the sign-in note with their
  German texts
- [x] 2.2 The data set: the change list as a pure function of `D`
- [x] 2.3 The writer: each change through the bookings or the models'
  saves, with the clock at its moment and tasks fully validated
- [x] 2.4 `manage.py demo_data` with its guards
- [x] 2.5 Dockerfile command and `deploy/orgsyndb.env.example`

## 3. Docs and archive

- [x] 3.1 `README.md`: running the lab with the demo data locally and
  in containers, and replacing a demo database before real use
- [ ] 3.2 Seed the Compose stack on the test server in demo mode and
  look through the lab's pages (owner, manual)
- [x] 3.3 Review, then archive
