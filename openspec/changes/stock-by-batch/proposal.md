## Why

Since `batches`, every filling names the vessel and so the batch it
came from, but an item still counts its containers as one number.
Once filled, the containers lose their batch. A delivery cannot say
which batch it sent, though the batch is printed on every container
and written on every delivery note. A batch's page cannot say where
its containers went beyond the filling.

The owner decided on 2026-11-21 and 2026-11-22 the following:

- Consumer containers are kept per batch.
- Old stock, whose batch the Excel sheet never recorded, is held as
  containers of unknown batch until it is delivered.
- A delivery line always names its batch. A line that delivers
  containers of unknown batch names a batch already recorded, and an
  old batch is first recorded with its number alone.
- Lines of historical notes name their batch too.
- A new item's opening count may name one batch.
- The yearly stock-taking (Inventur) is left for later
  (`openspec/STATE.md`).

## What Changes

- **BREAKING** An item keeps its containers by batch, as shares: one
  share for each batch of its substance that has held containers of
  it, and one share of unknown batch (`unbekannt`). Its quantity is
  the sum of its shares.
- **BREAKING** Each movement names the batch whose share it changes:
  - an opening count, its batch or none;
  - a filling, its vessel's batch;
  - a delivery, its line's batch;
  - a correction, the share it sets;
  - a reversal, the batch of the movement it undoes.
- A new movement kind, `assignment` (`Zuordnung`), moves containers of
  unknown batch into a batch. A current delivery line books one before
  its delivery when its batch's share holds too few containers. It is
  refused when that share and the share of unknown batch together hold
  too few.
- **BREAKING** Every delivery note line, current or historical, names
  a batch of its item's substance. One note may hold the same item
  once per batch.
- The new-item form takes an optional batch for the opening count. The
  correction form corrects one share, chosen among the item's batches
  and `unbekannt`.
- The item page shows the containers by batch, and the ledger shows
  each movement's batch. Delivery notes show each line's batch. The
  batch page lists the items holding its containers and its
  deliveries. The admin shows an item's shares read-only.
- The demo data set holds shares, assignments and batches recorded by
  number alone. The diagram shows the new table.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: the new requirement "Stock by batch";
  changes to "Items", "Item movements", "Delivery notes", "Delivery
  list", "Item page", "Inventory forms", "Inventory in the admin" and
  "Batch page".
- `lab-demo`: "Demo inventory".
- `database-diagram`: "Tables and columns".

## Impact

- `webapp/inventory/`:
  - models: `BatchStock`, plus `Movement.batch` and
    `DeliveryLine.batch`;
  - a schema-only migration;
  - `bookings.py`, forms, views, templates, admin and the German
    catalogue.
- `webapp/demo/`: data and seeding.
- `webapp/orgsyndb_web/schema_diagram.py` (grid) and the regenerated
  `webapp/docs/database-schema.html`.
- Tests across `webapp/tests/` that book deliveries, corrections and
  opening counts.
- Docs: `README.md` (inventory), `docs/SCHEMA*.md`,
  `docs/GLOSSARY.de.md`.
- The migration carries no data. The test server is reseeded with
  `demo_data --replace`. No new dependency.
