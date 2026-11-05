## Context

`task-tracker` brings in the web application under `/lab/`: accounts,
open reading and signed-in changes, change history, the reader of the
collection index with `compound_for` and molar masses, compound links
and the compound `datalist`.

The owner described the end-product inventory on 2026-11-04. It has one
row per item and records no batches; an article number is shared by
the rows of its container sizes. A row holds the article number,
name, category, container size, size unit (`mg`, `µmol`, `g` or
`mmol`), quantity left, a note, and the consumption of past quarters.
From that history the file computes a mean per quarter and per year.
The quantity cell is pale green below half a year's consumption,
yellow below a quarter's, orange below half a quarter's, and red when
nothing is left. The inventory counts aliquoted containers, ready to
deliver; bulk, not yet aliquoted, appears as free text in the note,
which the owner wants standardized. Task priorities are estimated today
from this forecast.

## Goals / Non-Goals

**Goals:** the inventory as an editable view with the file's columns
and colours; a history of every count; consumption that accrues from
bookings; bulk as records that can be counted and filled from.

**Non-Goals:** importing or exporting Excel; QC results; the catalogue;
other inventories; batches of aliquots; labels or barcodes; a stock box
on compound pages; suggested priorities and a replenishment list
(`production-planning`).

## Decisions

### One row per item, as in the file

An item is an article in one container size: its identity is the
article number with the size and unit, since the file may list one
article in several sizes. Its count of containers changes only through
movements. Rejected: the batch-and-container model of the first draft,
which the file does not have and the lab does not track for aliquots.

Each item belongs to an inventory, `end-products` for now, so the
intermediates and the commercial reagents can reuse the table with
their own view.

Article number, size and unit are fixed once the item exists, since
its count, its deliveries and its consumption are all measured in that
size; a wrong item is corrected to zero and replaced, and staff may
delete one that has only its opening count.

### Compounds through the article number

The article number is looked up with `compound_for`, which matches the
values of unique compound fields such as the demo's `item_number`. The
link gives the compound's page and its molar mass. Nothing is stored
about the compound, so a renamed or removed compound only stops
linking. Every size of an article therefore has one compound and one
molar mass, which the bulk lots of that article rely on. Rejected: a
compound named per item, which let two sizes drawing on one lot
convert it with different molar masses.

### Movements as a ledger

Every change of a count is a movement, stored in one transaction with
the new count: a delivery takes containers out and may name the
recipient; a filling adds aliquots; a correction sets the count after
counting and needs a note; the opening count is the first movement of a
new item. Each keeps the count after it, so the item's page reads as a
ledger in booking order; its date is when it happened, and decides its
quarter. A delivery larger than the count is refused.

The count changes by one conditional update,
`quantity = quantity - n WHERE quantity >= n`, read back in the same
transaction, so two people booking at once cannot overdraw it on
either database; `select_for_update()` would do nothing on SQLite.

Movements are never edited or deleted, because both the count and the
consumption rest on them. A mistaken delivery or filling is reversed
by a movement of its own, which restores the count, returns a
filling's amount to its lot, and takes a delivery out of the
consumption. The record history of django-simple-history still covers
the other fields.

### Consumption as the file computes it

A quarter's consumption is the number of containers delivered in it:
the value entered for that quarter, for the time before the
application, plus the lines of the delivery notes dated in it. Entered
values and bookings add up, so the quarter in which the application
starts holds both halves.

The means follow the file, so the view can be checked against it: the
mean per year is taken over all complete calendar years before the
current one, from the item's first year with data, and the mean per
quarter is a quarter of it. The current year stays out of the mean and
has a column of its own, so this year's consumption can be compared
with past years'. Means and coverage show rounded half up, while
levels compare the unrounded values. A more responsive forecast, for
priorities, belongs to `production-planning`; this view mirrors the
file until the transition ends. Rejected: an eight-quarter window,
which the first draft had and the file does not.

### Delivery notes

Deliveries leave the lab on internal delivery notes (`Lieferscheine`),
whose dates are the best record of demand and are never used today.
So a delivery is booked as a note with its lines, one per item, all in
one transaction, and the note's number, date and recipient are kept.
Old notes can be entered as historical notes, which count as
consumption but change no count; a quarter takes either an entered
total or historical notes, never both, so nothing is counted twice,
and removing an entered total makes room for the notes behind it. A
note's date, kind and lines are as fixed as the movements they book,
and no note is deleted, since consumption rests on them; a mistake is
reversed, line by line for a current note, whole for a historical
one, and reversed records count for nothing, not even as the start of
an item's history.
The dated deliveries are what `production-planning` forecasts from.

### Levels from the mean

The levels follow the file's colours, compared with the mean per
quarter `Q`. `out` (red) applies when no container is left. `critical`
(orange) applies below `Q/2`, `low` (yellow) below `Q`, and `watch`
(pale green) below `2Q`. An item without consumption has no level
unless it is out. The cell carries the level's label as text, and the
colours are tokens with a dark-scheme variant, so the meaning survives
without colour and in both schemes. The coverage is the count divided
by `Q`, in quarters.

### Bulk lots

A bulk lot belongs to an article number, which ties it to every size of
that article, and records an amount in `mg`, `g`, `µmol` or `mmol`, a
batch, a location, a date and a note. Its amount changes only through
its own movements: filling, which takes the amount aliquoted,
correction, and the reversal of a filling. The amount is kept in a base
unit, mg or µmol, with six decimal places, and shown in the lot's own
unit: one 10 µmol container of cinnamic acid takes 1.4816 mg, which
three places of a lot kept in grams would round to 0.001 g. Article
number and unit are fixed once the lot exists. Filling an item may name a lot. Its form then proposes the
amount to take from the lot, converted into the lot's unit, and both
movements are stored in one transaction. Mass and amount of substance
convert through the molar mass of the item's compound; without one,
only units of the same kind convert, and the amount is entered by hand.
Each item shows how many of its containers the open lots would still
fill, counted lot by lot, since a filling draws on one lot: two 6 mg
lots fill no 10 mg container.

### A chart without JavaScript

The item's page draws the consumption of each quarter of the two
complete years before the current one and of the current year as an
inline SVG bar chart rendered on the server, each bar titled with its
quarter and value, with a line at the mean per quarter, beside a table
of the same numbers.

## Risks / Trade-offs

- The columns follow the owner's description, not the file itself.
  The owner chose so on 2026-11-05: the application is a prototype and
  will differ from the file anyway.
- Without the import, every item and its past quarters are typed in.
- A product's first year counts fully in the mean, as in the file,
  even when the product started during it.

## Open Questions

None. "Quantity left" is taken as a count of containers, since each
row names its container size.
