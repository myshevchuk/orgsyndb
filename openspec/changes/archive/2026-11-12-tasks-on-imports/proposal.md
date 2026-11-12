## Why

Since `collection-import` the lab application holds the collection's
procedures, scope entries and sequences as rows, but its tasks still
name a sequence by ID text, copy the procedure IDs of its steps into a
JSON list, and count done steps in two numbers, all read through
`index.json`. A running synthesis is therefore not tied to the scope
entry it carries out or to the collection as it read when the step was
planned. The owner settled in draft 07 that a task's steps are rows
naming the entry and the import current when they were planned. This
change moves tasks onto the imported rows and retires `index.json`.

## What Changes

- **BREAKING** A task's `sequence` is an imported sequence. Its steps
  are rows: position, the scope entry they carry out (or none for a
  step not written down as one), the import current when planned, and
  the date they were done. `sequence_steps`, `steps_total` and
  `steps_done` go.
- Choosing a sequence creates one step per step of the sequence;
  without one, the form's step total creates plain steps. Steps done
  in the form, the `step` action and the `end` action set the steps'
  dates. Progress counts done steps.
- The task page lists its steps by procedure and entry, with the date
  each was done.
- **BREAKING** `index.json`, `ORGSYNDB_INDEX` and
  `orgsyndb_web.index` go. The interface language is the latest
  accepted import's; a substance links `In der Sammlung` when an
  accepted import is not older than it. The builder no longer runs
  `orgsyndb index` (Emacs still does).
- The demo data set records an accepted import of the demo collection
  from `webapp/demo/manifest.json`, so its tasks can follow
  `SEQ-0001` and `SEQ-0002`; the builder's next cycle replaces it with
  a real build. Its texts follow the language of the import found
  before replacing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `task-tracker`: the task record, page, actions and forms on
  imported sequences and step rows.
- `web-app`: no collection index or `ORGSYNDB_INDEX`; the language
  from the latest accepted import.
- `lab-registry`: when a substance links to the collection.
- `lab-overview`: the language scenario.
- `lab-demo`: the data set's own import, tasks on it, the language of
  its texts.
- `container-deployment`: no `index` run and no `index.json` in a
  release.
- `collection-import`: the demo command as the other writer of
  imported rows; tasks refer to them; a procedure keeps whether it is
  general.
- `database-diagram`: the new tables in the diagram.

## Impact

- Changed: `webapp/tasks/` (models, migration, forms, views,
  templates, history, admin), `webapp/orgsyndb_web/` (settings,
  middleware, `index.py` removed), `webapp/registry/views.py`,
  `webapp/demo/` (seed, data, the manifest), `webapp/overview/`
  and `webapp/planning/` where they read steps or the index,
  `webapp/collection/` (the `general` column),
  `deploy/docker/orgsyndb-deploy`, `deploy/webapp/Dockerfile`,
  `deploy/orgsyndb.env.example`, and the tests of each; `webapp/tests/fixtures/demo-manifest.json` moves to
  `webapp/demo/manifest.json`.
- Docs: `README.md` (tasks, the lab application's settings, the demo,
  builds) and `webapp/docs/database-schema.html`, regenerated.
