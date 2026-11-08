## Context

The application's own models live in the packages under `webapp/`:
`accounts`, `inventory`, `tasks`, `planning` and `demo`.
django-simple-history adds a historical model beside each tracked one.
The deployment runs PostgreSQL, the tests run SQLite or PostgreSQL,
and CI runs the suite on both.

## Goals / Non-Goals

**Goals:**

- A diagram that shows what the database holds, taken from the
  models, so that it cannot silently disagree with them.
- A page that opens from disk in a browser and needs no network
  except for its fonts, and no script to show the diagram.

**Non-Goals:**

- Automatic arrangement of the tables.
- Serving the diagram from the application.
- A German version (AGENTS.md "Documents for people").

## Decisions

### Types from the PostgreSQL backend, without a connection

The generator builds a PostgreSQL `DatabaseWrapper` from Django's
backend without connecting, and asks each field for its `db_type` and
`db_check`. The output therefore does not depend on the database the
settings name, and the SQLite and PostgreSQL CI jobs check the same
file. Two long type names are shortened to their PostgreSQL aliases,
`timestamptz` and `float8`, and spaces are dropped from type
arguments.

Django adds range validators to integer fields from the default
connection, so a field's `validators` differ between SQLite and
PostgreSQL. The notes read only the validators a field declares, and
they render under English, since the settings default to German.

### Static SVG drawn in Python

The diagram is an inline `svg` written by the generator. The page's
script only adds the highlighting of a table and its neighbours. The
page shows everything without the script, and a test can read the
geometry.

### Arrangement by hand, lines by rule

A hand-kept grid gives each table a band and a column, and several
tables may share a slot one under another. The box width is the widest
any table needs, estimated from its text, so a long new column widens
every box instead of overflowing one. Lines follow fixed rules:

- a table in the next column, in any band, is reached by an elbow
  through the gap between the two columns, from the row of the foreign
  key to the row of the key it references;
- a table in the same column, in the next band or slot, is reached by
  a straight vertical line;
- a table two or more columns away in the same band is reached by a
  line under the tables between them;
- a reference to the table itself loops below its box.

Lines that share a gap or a column over overlapping heights are spread
apart. A reference the rules cannot route, or a line that would cross
another table's box, stops the command with a message naming the
reference. Moving a table in the grid is the fix.

### What is not drawn

Foreign keys to `accounts_user` are many and would cross the whole
drawing. Their key mark takes the accounts colour, and highlighting the
user table lights them. The history tables share one layout, drawn
once as a generic box. Two links the models do not hold are declared
next to the grid: a lot belongs to the item with the same inventory and
article number, and task numbers come from `tasks_counter`. The
generator checks that the columns they name exist.

### Prose from the docstrings

The page's description of each table is the model's docstring, so the
rules it states, such as "the quantity changes only by movements",
change with the code. The page's own text is limited to the legend and
the section headings.

### Freshness as a test

`schema_diagram --check` compares the file with the generated text.
One test runs it. The output carries no date or commit, so it changes
only when the models or the generator change.
