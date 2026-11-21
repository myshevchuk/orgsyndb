## Context

The inventory has two kinds of stock, measured differently: an item
counts consumer containers of one size of an article, and a bulk lot
weighs an amount of one substance. A lot carries a batch as text, and
so does a task; the two belong together when the texts are equal and
the substances match. A filling of an item may name a lot, or none.

The owner's account of a compound's life is: planning, task, journal
entry, batch, and then storage in bulk or filling into consumer
containers, straight from the flask or later from storage. A journal
entry makes no, one or several batches. Batch numbers follow a personal
pattern (initials, the entry's number, an optional suffix such as `FA`
for fraction A), which the application does not interpret.

## Goals / Non-Goals

**Goals:**

- A batch is a record: what it is, where it came from, and the journal
  entry and step that made it.
- Every weighed amount belongs to one batch; every filling comes from
  one.
- A product can go from the flask into containers without passing
  through a stored vessel, and one batch can be stored in several.
- Terms that keep the three notions apart: substance, batch, vessel;
  and items counting containers.

**Non-Goals:**

- Consumer containers per batch, the batch on delivery lines and
  stock-taking by batch: the next change.
- A table of suppliers; the supplier fields stay text.
- Reservations, labels, barcodes.

## Decisions

### Terms

`Charge` / batch, `Gefäß` / vessel, `Kolben` / flask, `Umfüllen` /
transfer. English "container" already means a consumer container
throughout the inventory's specs and pages (`Gebinde` in German), so
the weighed record cannot be called a container without making the two
read alike; "vessel" covers a reaction flask, a storage jar and a
supplier's bottle. "Bulk" remains the name of the aggregate an item and
an article draw on, the amount in the open vessels of their substance,
as the item list's and the planning list's `Bulk` columns show it.

Models: `Batch`, `Vessel`, `VesselMovement`; `Movement.vessel_movement`
replaces `bulk_movement`. All stay in `inventory`.

### The batch owns origin, the vessel owns place and amount

`Batch`: `substance` (fixed), `source` (`made`/`bought`, fixed),
`number` (made: required, at most 30 characters, unique among made
batches by `Lower(number)`; bought: empty), `journal_entry` (made,
optional), `task_step` (made, optional, fixed), `date`, `yield_amount`
and `yield_unit` (made, optional), `supplier`,
`supplier_article_number` and `supplier_batch` (bought, at most 100, 50
and 50 characters), `note`, with history.

`Vessel`: `batch` (fixed), `unit` (fixed), `amount`, `flask` (fixed),
`location`, `note`, with history leaving out the amount, as the lot's
did. The substance is the batch's.

The kind the vessel list shows is derived, never stored: `Kolben` for
a flask; otherwise `Endprodukt` when the substance has an article,
`Zwischenprodukt` when the batch is made, `Reagenz` when it is bought.
Storing a role would let a vessel contradict its batch or its
substance's article.

### The flask holds the yield until the task ends

Recording a batch from a step requires its yield, which becomes the
opening amount of the batch's first vessel: a flask when the form names
no location, a stored vessel there when it does. Fillings, withdrawals
into later steps and transfers draw from the flask like from any
vessel. When a save or action ends, fails or cancels the task, each
flask of a batch made by one of its steps that still holds an amount is
emptied by a `remainder` movement in the same transaction.

The alternative, splitting the whole yield in one form with no
remainder, was rejected by the owner: a flask often waits a few days
before its contents are filled or stored.

The yield stays on the batch as the recorded fact, editable with
history; corrections of what a vessel holds are the vessel's
corrections. A made batch recorded without a step (old stock found at
stock-taking) has no flask and may have no yield; its vessels open with
an amount.

### Transfers

A transfer is two movements: `transfer_out` on the source and
`transfer_in` on the target, the second naming the first. The target is
a vessel of the same batch, not a flask, or a new stored vessel created
by the transfer in the source's unit, whose first movement is then the
`transfer_in`. Each movement holds the amount in its own vessel's base
unit; across mass and amount of substance the transfer converts through
the molar mass, as a filling does, and is refused without one. Transfers are not
reversed; a wrong one is undone by a transfer back or a correction.

### Fillings

`bookings.fill` takes a required vessel. The rule is enforced by the
booking and its form, not by a check constraint: a constraint would
fail the migration on databases that hold fillings without a lot, and
the old filling form allowed them. A filling the migration carries over
without a vessel movement stays in the item's ledger, shows no vessel,
and its reversal takes the containers back as before, returning nothing
to any vessel.

### Tasks

`Task.batch` goes. A task's batches are the batches whose `task_step`
is one of its steps; its product batches are those of its substance.
Ending without failing needs a product batch. A batch can be recorded
only from a step of a planned or running task, so a task needs a step
to end without failing, and a task entered after the fact is created
running, its batch recorded, and then ended. The write-off runs in one
service that the actions, the form's save and the admin's `save_model`
call inside the transaction that closes the task, after validation, so
a refused save writes off nothing.

After a flask's task is closed, the flask takes nothing back: a
correction of it and the reversal of a filling or withdrawal from it are
refused, so closed stock cannot reappear for filling or planning. A
batch a step made is never deleted, so an ended task cannot lose its
product batch. The task list's `Charge`
column joins the product batches' numbers; its search and the admin's
search match the numbers of the task's batches.

### Journal entries

A batch may name an entry, given in the form as `<code>/<number>` as a
step names one, and the entry is created on first naming as it is for
steps. Recorded from a step that names an entry, the batch names that
entry. An entry a batch names is not deleted.

### Migration

An `inventory` migration renames `Lot` to `Vessel` and `LotMovement`
to `VesselMovement` in place, so movement ids and the `PROTECT` links
from item movements and reversals stay intact, and renames
`HistoricalLot` with them. It adds `Batch` and creates one batch per
live lot, with the lot's source, supplier, date and step; a made
batch's number is `L<lot id>`, always unique and short, and the lot's
batch text, which may be up to 100 characters and need not be unique,
goes into the batch's note. It points each vessel at its batch, drops
the moved fields from the vessel and its history, and sets `flask` off.
A `tasks` migration, depending on it, drops `Task.batch` from the task
and its history.

The unique constraint on made numbers compares `Lower(number)`; on
SQLite `lower()` folds ASCII only, so the forms also compare
`casefold()` before saving, and the constraint is the backstop on
PostgreSQL. A test migrates a database populated at the previous
migration (lots of both sources, with and without batch text, a
filling with and without a lot, a withdrawal and its reversal, a task
with a batch) and checks the batches, vessels, movement links and
histories that result. Links that only
the batch text held are not reconstructed, so a converted ended task
may lack its product batch; the application has no
users, and the test server's database is rewritten by
`demo_data --replace`.

## Risks / Trade-offs

- [The change touches most inventory and task pages and their tests]
  → tasks are grouped by area, and each area's tests run on their own.
- [A flask emptied automatically could discard product someone meant
  to store] → the remainder is a visible movement on the flask, the
  task page lists the step's batches with their flasks, and the end
  action's message names what was written off.
- [Two made batches of different substances cannot share a number] →
  the owner's numbering makes numbers unique in practice; the error
  names the batch that holds the number.
