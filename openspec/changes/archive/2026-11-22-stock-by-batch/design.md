## Context

`batches` (archived 2026-11-22) made batches and vessels records of
their own and made every filling name a vessel. An item's stock is
still one number, `Item.quantity`, which movements change by
conditional updates on the item's row (`_take`, `_add` in
`inventory/bookings.py`). A delivery note line is an item and a count,
unique per note and item. Planning, the item list, the overview and
consumption all read `Item.quantity` or delivery movements.
`postgresql-only` made PostgreSQL the only database.

## Goals / Non-Goals

**Goals:**

- Keep every container's batch from its filling to its delivery.
- Let old stock stay of unknown batch until it is delivered.
- Keep the guarantee that concurrent bookings never take more than
  is there.

**Non-Goals:**

- Stock-taking (Inventur): deferred by the owner to `STATE.md`.
- A table of suppliers.

## Decisions

### Shares as rows, the unknown share among them

`BatchStock(item, batch, quantity)`:

- `item` is a foreign key with `CASCADE`, and `batch` a nullable
  foreign key with `PROTECT`. A row whose `batch` is null is the share
  of unknown batch.
- `quantity` is a `PositiveIntegerField` with a check of `>= 0`.
- Two conditional unique constraints keep one row per (item, batch)
  where the batch is set, and one row per item where it is null. One
  constraint with `nulls_distinct=False` would do the same, but the
  table diagram notes for every unique constraint over a nullable
  column that null rows never conflict, which that constraint would
  make false.
- The unknown row is created with the item. A batch row is created by
  the first booking into it, and kept at zero once emptied.

Every share change is a conditional `UPDATE … SET quantity = quantity
± n WHERE quantity >= n` on the share row, and the item's quantity
changes by the same amount in the same transaction. An assignment is
therefore two conditional updates, unknown down and batch up.

Every booking that changes a share (`create_item` aside, whose item
is new) takes its locks before it reads a share, computes a shortfall
or a correction's difference, or touches a vessel: the task of a flask
first, then every item it changes in the order of their IDs (`_lock`),
then vessels. `fill`, `book_note`, `correct` and `reverse` all follow
this order, so no two of them wait for each other, a correction never
applies a difference read before a concurrent filling, and concurrent
first bookings into one batch create its row once. The conditional
updates stay as the guard of last resort. A unique violation that
still occurs is refused like a lost race, never shown as a server
error. Overlap tests with two connections, as for task closure, cover
a delivery against a correction and a filling against a correction.

`Item.quantity` stays stored, because the list sorts and filters by it
and planning reads it. It always equals the sum of the shares. A
model-level test asserts this after every kind of booking.

Rejected:

- **An implicit unknown share** (the quantity less the batch rows). An
  assignment would then need a conditional update on a sum across
  rows, which only works under a lock held for the whole booking.
- **No share table**, deriving shares by summing movements. Openings
  and corrections hold absolute counts rather than changes, and every
  read would aggregate the ledger.

### Assignment as its own movement

A delivery from containers of unknown batch books an `assignment`
first. The delivery itself then always takes from a batch's share,
and its reversal returns the containers to that batch: once delivered,
their batch is known. The ledger shows the assignment as its own row,
naming the delivery note that caused it. An assignment is not
reversible on its own, and reversing the delivery leaves it in place.

The line takes from its batch's share first. Only the shortfall is
assigned, so containers already known to be of that batch are used
before unknown ones.

Rejected: a delivery movement naming the unknown share. Its reversal
would return the containers to the unknown share, losing the batch the
note recorded.

### `Movement.batch` names the share changed

The field is nullable, with null for the unknown share. An opening
names the batch entered, or none. A correction names its share, and
its `count` is that share's counted number. A filling names its
vessel's batch, and its reversal the same batch. The delivery
movement has no line key. Its line is the one with the same note,
item and batch, which is unique per note.

### Delivery lines carry the batch

`DeliveryLine.batch` is a required foreign key with `PROTECT`. The
unique constraint becomes (note, item, batch). Historical lines name a
batch too, as the owner decided, and still move no stock. Reading a
note as reversed or partly reversed looks only at the note's delivery
movements and leaves out its assignments.

### Readers of delivery lines

Lines of one item are no longer unique per note, so every reader that
joins lines and movements by note and item now also matches by batch
and by the movement's kind:

- `counted_lines()` (`inventory/figures.py`), which consumption, the
  overview and planning read, leaves out a line whose own delivery is
  reversed, and keeps its siblings of other batches;
- the note page matches each line to its delivery movement and
  ignores assignments;
- planning's rhythm (`planning/plan.py`, `forecast.py`) counts the
  distinct notes of the surviving lines, not the lines. Deduplicating
  by date would merge two real notes of one day.

The batch page lists delivery lines rather than delivery movements,
so historical lines show too.

### Choosing a batch in a form

On a delivery row, the batch is a `<select>` of every batch of the
substances offered; on the new-item form, of every batch of every
substance, since a new item may be the first of its substance. The batches are grouped in
one `<optgroup>` per substance, carrying `data-substance` with the
substance's key, and each item option carries the same attribute.
`lab.js` hides the groups of other substances than the one chosen in
the row, or typed on the new-item form, and clears a choice that it
hid. The function that picks the groups to show is pure and
exported on `OrgSynLab`, so `test_lab_script.py` tests it under Node.
The DOM wiring is a thin adapter. Booking still refuses a batch of
another substance than the item's, so the form stays correct without
the script.

The correction form offers only the batches of the item's substance,
with the counts the item holds. Its choice needs no narrowing.

Rejected:

- **One select of item and batch pairs.** It breaks `?item=`
  pre-filling, and the list grows as items times batches.
- **A typed batch number.** The owner chose recorded batches only.
- **Loading a row's batches with htmx.** A request per row change
  costs more than hiding groups already on the page.

### Correction stays one share at a time

Until the Inventur exists, `Bestand korrigieren` sets one share. A
correction of the unknown share is how old stock found to be
miscounted is fixed. Assigning old containers to their batch without
a delivery waits for the Inventur.

## Risks / Trade-offs

- [The delivery form renders ten selects of every batch] → The lab
  has at most a few hundred batches. Rendering rows on demand is a
  later change if needed.
- [A forgotten share update would drift `Item.quantity` from the sum]
  → Every share change goes through one helper that updates both, and
  the invariant test covers each booking path.

## Migration Plan

The migration is schema-only, shaped so that it runs on old demo rows.
It adds `BatchStock`, `Movement.batch`, and `DeliveryLine.batch` as a
nullable column. Forms, bookings and the admin require the line's
batch, so the database's null serves only lines written before the
migration. It also swaps the line constraint. Items migrated without
share rows stay so until reseeding. The test server is reseeded with
`demo_data --replace` right after deploy. The demo's reset deletes
shares before items and batches, and lines and movements before
batches, so a second replacement runs on a seeded database.
