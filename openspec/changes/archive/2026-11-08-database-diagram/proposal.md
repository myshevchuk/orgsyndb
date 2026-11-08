## Why

The lab application's tables are described only by its models and
migrations. A developer or operator who wants the shape of the
database has to read five `models.py` files and Django's naming rules.
A diagram drawn by hand goes stale with the next migration. One
generated from the models, whose freshness the suite checks, stays
correct.

## What Changes

- A new management command, `manage.py schema_diagram`, writes
  `webapp/docs/database-schema.html` from the models: a standalone
  page with an entity-relationship diagram of the application's
  tables, their columns with PostgreSQL types and keys, the foreign
  keys drawn between them, and lists of the constraints, the delete
  rules, the history tables, each table's docstring and Django's own
  tables.
- `schema_diagram --check` writes nothing and fails when the file
  differs from what the models give. The suite runs the check, so a
  model change without a regenerated diagram fails.
- The diagram's arrangement is kept by hand in the generator, a grid
  slot per table. The command refuses an arrangement that misses a
  table, names one that does not exist, or would draw a line through a
  table.
- The generated file is committed.

## Capabilities

### New Capabilities

- `database-diagram`: the generated table diagram, its content, its
  arrangement and the freshness check.

### Modified Capabilities

None.

## Impact

- New: `orgsyndb_web/schema_diagram.py`, the command
  `orgsyndb_web/management/commands/schema_diagram.py`, its template,
  `webapp/docs/database-schema.html` and the tests.
- Docs: `README.md`, the command under the lab application's
  development section.
- No model, migration or page of the application changes.
