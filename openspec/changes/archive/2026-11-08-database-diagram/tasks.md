## 1. Tests

- [x] 1.1 Collection: the application's tables and no others, columns
  in table order with PostgreSQL types, keys, nullability, notes from
  choices, validators, defaults and help texts, the columns a history
  leaves out
- [x] 1.2 Foreign keys: targets, one-to-one, delete rules; the history
  tables and Django's tables listed apart
- [x] 1.3 Constraints: unique and check constraints with their
  conditions, the `>= 0` checks, the note on nullable columns in a
  unique constraint; an unsupported condition refused
- [x] 1.4 Arrangement: each routing rule's points; spreading lines
  that share a gap; a missing table, an unknown table, an unroutable
  reference and a line through a box refused; the box width
- [x] 1.5 Page: a standalone document, the title, the one external
  stylesheet, every table and column in the `svg`, the sections
- [x] 1.6 Command: writes the file; `--check` exits 0 on a current
  file and 1 on a stale or missing one, naming the file
- [x] 1.7 The committed diagram is current

## 2. Implementation

- [x] 2.1 `orgsyndb_web/schema_diagram.py`: collection, constraints,
  arrangement, rendering
- [x] 2.2 Template and the command
- [x] 2.3 Generate and commit `webapp/docs/database-schema.html`

## 3. Docs and archive

- [x] 3.1 `README.md`: the command, under the lab application's
  development section
- [x] 3.2 Review, then archive
