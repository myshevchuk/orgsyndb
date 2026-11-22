## Context

`batches` (archived 2026-11-22) made batches and vessels records of
their own and made every filling name a vessel. An item's stock is
still one number, `Item.quantity`, which movements change by
conditional updates on the item's row (`_take`, `_add` in
`inventory/bookings.py`). A delivery note line is an item and a count,
unique per note and item. Planning, the item list, the overview and
consumption all read `Item.quantity` or delivery movements.

## Goals / Non-Goals

**Goals:**

- Keep every container's batch from its filling to its delivery.
- Let old stock stay of unknown batch until it is delivered.
- Keep the guarantee that concurrent bookings never take more than
  is there, on PostgreSQL and SQLite.

**Non-Goals:**

- Stock-taking (Inventur): deferred by the owner to `STATE.md`.
- A table of suppliers.
- Narrowing a row's batch choice to the chosen item in the browser.

## Decisions

### Shares as rows, the unknown share among them

`BatchStock(item, batch, quantity)`:

- `item` is a foreign key with `CASCADE`, and `batch` a nullable
  foreign key with `PROTECT`. A row whose `batch` is null is the share
  of unknown batch.
- `quantity` is a `PositiveIntegerField` with a check of `>= 0`.
- Two conditional unique constraints keep one row per (item, batch)
  where the batch is set, and one row per item where it is null.
  `nulls_distinct` would need only one constraint, but SQLite does not
  support it.
- The unknown row is created with the item. A batch row is created by
  the first booking into it, and kept at zero once emptied.

Every share change is a conditional `UPDATE … SET quantity = quantity
± n WHERE quantity >= n` on the share row, and the item's quantity
changes by the same amount in the same transaction. An assignment is
therefore two conditional updates, unknown down and batch up, which
are atomic on both databases.

Bookings that create a batch row lock the item row first (`_lock`), so
on PostgreSQL concurrent first bookings into one batch create the row
once. On SQLite writes are serialized. A unique violation that still
occurs is refused like a lost race, never shown as a server error.

`Item.quantity` stays stored, because the list sorts and filters by it
and planning reads it. It always equals the sum of the shares. A
model-level test asserts this after every kind of booking.

Rejected:

- **An implicit unknown share** (the quantity less the batch rows). An
  assignment would then need a conditional update on a sum across
  rows, which neither database does atomically without locks. SQLite
  has none.
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

### Choosing a batch in a form

On a delivery row and on the new-item form, the batch is a `<select>`
of every batch of the substances offered, grouped by substance in
`<optgroup>`. Booking refuses a batch of another substance than the
item's. The correction form offers only the batches of the item's
substance, with the counts the item holds.

Rejected:

- **One select of item and batch pairs.** It breaks `?item=`
  pre-filling, and the list grows as items times batches.
- **A typed batch number.** The owner chose recorded batches only.

### Correction stays one share at a time

Until the Inventur exists, `Bestand korrigieren` sets one share. A
correction of the unknown share is how old stock found to be
miscounted is fixed. Assigning old containers to their batch without
a delivery waits for the Inventur.

## Risks / Trade-offs

- [The delivery form renders ten selects of every batch] → The lab
  has few hundred batches at most. Narrowing in the browser is a
  later change if needed.
- [A forgotten share update would drift `Item.quantity` from the sum]
  → Every share change goes through one helper that updates both, and
  the invariant test covers each booking path.

## Migration Plan

The migration is schema-only. It adds `BatchStock`,
`Movement.batch` and `DeliveryLine.batch` (non-null, with no
default), and swaps the line constraint. Before 1.0 there is no data
to carry. The test server is reseeded with `demo_data --replace`
after deploy.
