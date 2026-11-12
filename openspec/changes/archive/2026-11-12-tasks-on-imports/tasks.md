## 1. Tests

- [x] 1.1 Task record: sequence rows, steps from a sequence, kept on a
  withdrawn sequence, no change of sequence with a step done,
  progress from steps
- [x] 1.2 Task forms: sequence choice, steps by hand, steps done and
  their dates, a withdrawn sequence refused when new
- [x] 1.3 Task page and actions: steps listed with entries and dates,
  withdrawn sequences, procedures and entries, `Eintrag <n>` only for
  general procedures, the combined history, `step` and `end`
- [x] 1.4 Language from the latest accepted import; the registry
  page's link by import and creation; no `ORGSYNDB_INDEX`
- [x] 1.5 Demo: the data set's import, tasks on it, the language of
  its texts, replacing after an import; a real import after the
  demo's keeps the tasks' entries; the procedure's `general`; the
  "First import" scenario without the demo data set
- [x] 1.6 Builder: no `index` run and no `index.json`; the manifest
  fixture's new home and its drift guard
- [x] 1.7 Remove the tests of `orgsyndb_web.index` and the index
  helpers of the lab tests; the diagram's table set

## 2. Implementation

- [x] 2.1 `tasks`: `TaskStep`, the `sequence` foreign key, migration
  emptying the reshaped tables, admin, history; `collection`: the
  procedure's `general`
- [x] 2.2 Task forms, views, actions and templates; strings
- [x] 2.3 Middleware and demo language from the latest accepted
  import; the registry page's link; `orgsyndb_web/index.py` and
  `ORGSYNDB_INDEX` removed
- [x] 2.4 Demo: `webapp/demo/manifest.json`, the data set's import,
  tasks and steps; clearing deletes task steps before imported rows
- [x] 2.5 `orgsyndb-deploy`, `deploy/webapp/Dockerfile` and
  `deploy/orgsyndb.env.example`: no index
- [x] 2.6 `webapp/docs/database-schema.html` regenerated

## 3. Docs and archive

- [x] 3.1 `README.md`: tasks and their steps, settings, the demo,
  builds
- [x] 3.2 Review, then archive
