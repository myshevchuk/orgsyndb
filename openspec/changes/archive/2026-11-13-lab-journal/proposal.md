## Why

A procedure names the paper notebook entry it was written from, and
its project, as fields that each collection declares for itself; the
application cannot tell which notebook an entry belongs to, and a
synthesis step has nowhere to say where it is written down. The owner
settled in draft 07, and again on 2026-11-12, that `notebook` and
`project` become built-in procedure keys and that notebooks are
registered in the lab application and listed in the snapshot.

## What Changes

- New package `journal`: notebooks (code as on the cover, owner,
  note) and their numbered entries, which stay on paper. Pages at
  `/lab/journal/` list the notebooks and each notebook's entries with
  the procedures and task steps that name them; signed-in users
  register and edit notebooks; staff see both in the admin.
- The snapshot lists the notebooks, inside its digest; the index too.
- **BREAKING** `notebook` and `project` are built-in procedure fields,
  the journal fields: a collection no longer declares them, and
  declaring either is a configuration error. The validator refuses a
  `notebook` whose notebook the registry lacks.
- The manifest gives each procedure's `notebook` and `project`; the
  import checks them, creates the entries named, and keeps both on the
  imported procedure.
- A task step names the journal entry it is written down in, set on
  the task's page.
- The demo registers four notebooks; its collection drops the two
  declarations.

## Capabilities

### New Capabilities

- `lab-journal`: notebooks and entries, their pages, forms and admin.

### Modified Capabilities

- `procedure-fields`: the journal fields; reserved keys; the fixture's
  declarations renamed to `sample_code` and `funding`.
- `procedure-validation`, `compound-fields`, `collection-index`: the
  journal fields among the procedure fields; `notebooks` in the index.
- `lab-registry`: `notebooks` in the snapshot, ignored by
  `registry_load`; the registry page links the notebooks.
- `build-script`: `notebook` and `project` in the manifest; the
  index's configuration-error scenario.
- `collection-import`: checks, rows, applying, and the lock.
- `task-tracker`: a step's journal entry.
- `lab-demo`, `sample-procedures`: the demo's notebooks and
  declarations.
- `localization`: its declared-field scenario uses `funding`.
- `database-diagram`: the boxes and links of the journal tables, and
  of the access-token and issued-ID tables, which the last change left
  out of the listing.

## Impact

- New: `webapp/journal/` (models, migrations, views, templates,
  admin, `.po`); `tasks_taskstep.journal_entry`;
  `collection_procedure.journal_entry` and `project`.
- Changed: `tools/validate.py` (journal fields, notebooks in the
  snapshot), `tools/pipeline.py` (field data, index, manifest),
  `webapp/registry/snapshot.py`, `webapp/collection/`,
  `webapp/tasks/`, `webapp/demo/` (`registry.json`, `manifest.json`,
  seed), `examples/demo/orgsyndb.toml`, `tests/fixtures/`
  (procedure-fields declarations, `notebooks` in every snapshot),
  `webapp/orgsyndb_web/schema_diagram.py` and the regenerated
  `webapp/docs/database-schema.html`.
- Docs: README (journal pages, built-in fields, snapshot), SCHEMA,
  AUTHORING and the Org guides in both languages where they describe
  `notebook`, `project` and declared fields.
