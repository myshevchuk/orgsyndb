## Why

A filling may name no bulk lot, so containers of an end product can
enter stock from nowhere. Behind that gap the inventory has no record
of a batch: a batch is free text on a task and on a lot, joined by
equal values, and a lot is a batch and one vessel at once. One batch
cannot be split into several vessels, a product filled straight from
the reaction flask has no record to come from, and a journal entry
cannot list what it produced.

The owner decided on 2026-11-21 that a batch is a record of its own,
made in the lab from a journal entry or bought from a supplier; that
one journal entry makes no, one or several batches, since fractions of
different purity and separate reactions are separate batches; that a
made batch keeps its yield, which waits in the reaction flask until it
is filled or stored and is written off when the task ends; that made
batch numbers are free text, unique in the lab regardless of case; that
a supplier's article and batch numbers are kept in fields of their own,
ready for a later table of suppliers; and that every filling names the
batch it came from. Keeping consumer containers per batch, with the
batch on each delivery line, is a second change that builds on this
one.

## What Changes

- **BREAKING** A new record, the batch (`Charge`): its substance, its
  source, made or bought, and for a made batch its number, journal
  entry, the task step that made it and its yield; for a bought batch
  the supplier, the supplier's article number and the supplier's batch
  number; its date and note. Made batch numbers are unique regardless
  of case.
- **BREAKING** The bulk lot becomes the vessel (`Gefäß`): a weighed
  amount of one batch in one place, with its unit, amount, location and
  note. Its substance, source, supplier, batch text, date and making
  step move to its batch. "Vessel" names what is weighed; "container"
  stays the name of the consumer containers an item counts.
- A made batch recorded from a task step puts its yield into a new
  vessel: the batch's flask (`Kolben`), or a stored vessel when the
  form names a location. Ending, failing or cancelling the task writes
  off what its flasks still hold.
- Vessels of one batch can pass amounts between them (`Umfüllen`,
  transfer), so one batch can be stored in several vessels and a flask
  emptied into a jar.
- **BREAKING** A filling always names an open vessel of the item's
  substance; the filling form has no choice without one.
- **BREAKING** `Task.batch` goes. A task's batches are those its steps
  made; an ended task that has not failed needs a product batch, a
  batch of its own substance, in place of a batch number and a product
  lot. The task page's `Los erfassen` becomes `Charge erfassen`, and
  `Als Bulk erfassen` goes.
- **BREAKING** Pages and addresses: a batch list and batch pages under
  `/lab/inventory/batches/`, a vessel list and vessel pages under
  `/lab/inventory/vessels/` in place of the bulk list and the bulk lot
  pages; the inventory's section tabs read `Artikel`, `Chargen`,
  `Gefäße` and `Lieferungen`. The vessel list shows each vessel's kind:
  `Kolben` for a flask, otherwise `Endprodukt`, `Zwischenprodukt` or
  `Reagenz`, derived from its batch and whether its substance has an
  article.
- A journal notebook's page lists the batches each entry made; a
  substance's page lists its batches in place of its bulk lots.
- Planning reads open vessels where it read open lots; the overview's
  figure `Offene Bulk-Lose` becomes `Offene Gefäße`.
- The demo data set records its batches from task steps and fills
  every item from a vessel.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: "Batches" and "Vessels" replace "Bulk
  lots"; "Filling from bulk" requires a vessel; "Item movements",
  "Items", "Item list", "Item page", "Inventory forms" and "Inventory
  in the admin" follow; "Batch list", "Batch page", "Vessel list" and
  "Vessel page" replace "Bulk list" and "Bulk lot page".
- `task-tracker`: "Task record", "Task list", "Task page", "Task
  actions", "Task forms" and "Tasks in the admin" lose the batch field
  and take product batches.
- `production-planning`: "Runway", "Planning list" and "Starting from
  stock" read vessels; "Batches of tasks" replaces "Batches between
  tasks and bulk".
- `lab-journal`: "Notebooks and entries" lets a batch name an entry;
  "Journal pages" list each entry's batches.
- `lab-registry`: "Registry pages" list a substance's batches.
- `lab-overview`: "Overview page" and "Summary for the home page"
  count open vessels.
- `web-app`: "Substance links" names batches and vessels.
- `database-diagram`: "Tables and columns" and "Links between tables"
  show the new tables and lose the declared link of batch values.
- `lab-demo`: "Demo inventory", "Demo tasks and parameters" and
  "Language of the demo texts" hold batches and vessels.

## Impact

- `webapp/inventory/`: models (`Batch`, `Vessel`, `VesselMovement` in
  place of `Lot` and `LotMovement`; `Movement.vessel_movement` in place
  of `bulk_movement`), a migration, `bookings.py`, forms, views, URLs,
  templates, admin, the German catalogue.
- `webapp/tasks/`: the model loses `batch`; the end rule, actions,
  forms, list, page, admin and catalogue follow.
- `webapp/planning/`, `webapp/overview/`, `webapp/journal/`,
  `webapp/registry/` templates and views that read lots;
  `webapp/demo/` data and seeding;
  `webapp/orgsyndb_web/schema_diagram.py` (grid, declared links) and
  the regenerated `webapp/docs/database-schema.html`.
- Tests across `webapp/tests/` that touch lots, task batches, the
  demo, planning, the overview and the diagram.
- `README.md` sections on the inventory and tasks.
- The test server's lab database is rewritten with
  `demo_data --replace` after deploy; the migration does not carry
  links that only batch text held.
- No new dependency.
