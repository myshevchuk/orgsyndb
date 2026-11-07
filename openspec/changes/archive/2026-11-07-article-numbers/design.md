## Context

`Item.article_number` is required and, with size and unit, the item's
identity. Everything that relates an item to something else goes
through it: `compound_for(article_number)` for the compound and molar
mass, `Lot.article_number` for bulk, planning's articles (items grouped
by article number) and the matching of tasks. The demo collection
declares `item_number` (`Artikelnr.`) as required, unique and patterned
`CH-\d{4}`, and every one of its twenty compounds sets it; the lab demo
uses those numbers as article numbers, so items find their compounds.

## Goals / Non-Goals

**Goals:**

- Record a position that is in stock but was never delivered, without
  an article number, and keep the invariant that an item without one
  has no consumption.
- Make the demo show the distinction: numbers only where a delivery
  note would carry one.

**Non-Goals:**

- A second identifier for items, lots or tasks, such as a number of the
  database's own or a compound key on the item. Until one exists, a
  position without an article number links to nothing.
- Hiding a compound-directory column that a tab leaves empty.
- Changing how a number the collection does not know shows: an item
  `NV-0007` keeps the mark `nicht in der Sammlung`.

## Decisions

### Null, not empty

A missing article number is stored as NULL. The unique constraint on
inventory, article number, size and unit then leaves items without one
uncompared on PostgreSQL and SQLite alike, so two never-delivered
positions of the same size can exist. Forms turn an empty input into
None.

### Entered once, by a conditional update

The edit form shows the article number only while the item has none.
Saving it goes through a booking that updates the row only where the
article number is still NULL and refuses a number another item of the
same size and unit has, so two users cannot both assign one. The admin
shows the field read-only once it is set; while it is not, the admin's
save leaves the article number out of the fields it writes and hands a
number entered to the same booking, so a change page loaded before
another user assigned one cannot overwrite it.

### Refused at delivery and at entered consumption

The delivery note form offers only items with an article number, and
`book_note` refuses a line of an item without one as well, so the
demo's writer and any other caller meet the same rule. Entering
consumption for such an item is refused, zero included: a
never-delivered position has no history to record, and an entered zero
would start one, so that its first delivery would count against years
in which it did not exist.

### Planning skips the items

`Plan.items` groups by article number and leaves out items without
one; `matches` never matches an empty article number. Such an item has
no consumption, so it would have no demand anyway; skipping it keeps
NULL out of the article keys.

### The article number's `datalist`

The new-item and new-lot forms suggest the values of the compounds'
unique text fields, labelled with the compound's name, and not the
compound keys: a key is the collection's identifier, not a number a
delivery note carries. The task form's product field keeps every
identifier.

### The demo

The demo collection keeps `item_number` on the six final products the
lab demo delivers (`CH-0001`, `CH-0002`, `CH-0010`, `CH-0012`,
`CH-0013`, `CH-0016`) and drops it from the other fourteen, among them
1-phenylethanol (`CH-0003`), which the lab demo never delivers. The
field stays unique and patterned but is no longer required. The lab
demo's item of 1-phenylethanol loses its article number; its synthesis
fills every container without a lot, keeps its batch, and names the
compound key `1-phenylethanol` as its product.

The test collection under `tests/fixtures/collection/` mirrors the
demo byte for byte (sample-procedures "Test collection"), so it changes
with it. The two compound-fields scenarios that cite numbers of
compounds losing theirs are restated with what those links now read,
and one cites a final product's number. The Emacs scenario that creates
a compound in a copy of the demo no longer answers an `item_number`
prompt, since the command prompts only for required fields.

The demo's writer books a filling without a lot when its change names
none, and the data set's check of the compounds it names covers the
item without an article number through its compound key.

## Risks / Trade-offs

- A synthesized position's bulk cannot be recorded until the position
  is delivered once. → Accepted by the owner for now; a numbering of
  the database's own will lift it.
- The demo site's `Purchased` tab shows an empty `Artikelnr.` column.
  → Realistic for a collection that only numbers end products.
