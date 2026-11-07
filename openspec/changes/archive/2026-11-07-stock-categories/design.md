## Context

`inventory.figures.level` gives an item one of four levels, or none:
`out` at zero, else, with a mean per quarter `Q` above zero, `critical`,
`low` or `watch` below `Q/2`, `Q` and `2Q`. An item has a mean only
from the complete calendar years before the current one. The item
list's stock cell carries `level-<level>` and the level's label as text;
the legend names the four levels. Planning (`planning.plan.Plan._item`)
gives an item a demand model from its consumption whatever its state.
Every change of an item's quantity is a movement made by
`inventory.bookings._movement`. After `article-numbers`, an item
without an article number has no consumption.

## Goals / Non-Goals

**Goals:**

- One level per item, so that every stock cell is coloured and the
  legend explains every colour.
- Positions that planning should ignore, by rule or by hand, kept out of
  every planning figure.
- A `neu` mark that follows the yearly inventory audit: the year a
  position entered the counted end-product stock, not the year it was
  synthesised or first delivered.
- Levels and coverage for a position in its first year of consumption.

**Non-Goals:**

- What a discontinued item may no longer do, such as get new tasks or
  fillings: the owner will decide that later.
- Fixing the mean in an item's second year (recorded in `STATE.md`).
- Planning's demand models for items in their first quarter.

## Decisions

### One level, by precedence

An item's level is the first that applies:

1. `dormant` (`ruhend`): set aside by hand, or with consumption above
   zero, but none in the current calendar year or the one before;
2. `undelivered` (`noch nie abgegeben`): no consumption above zero;
3. `out`, `critical`, `low`, `watch`, as before;
4. `ok` (`ausreichend`): every other item.

A set-aside item is dormant whatever its stock, an empty one included:
it is the least urgent of all. Entered consumption is refused for a
quarter after the current one, so no consumption lies in a year to
come, and an item with consumption above zero has either a complete
year with some or a projection. Every item with consumption that is not
dormant has a mean above zero, through the projection below, so no
item is left without a level. The new levels keep the class names
`level-<level>` and the `Level` choices grow by three, so that the
item page, the planning list and `sort=urgency` handle them without a
second vocabulary. Their urgency order is out, critical, low, watch,
ok, undelivered, dormant.

Dormant and never-delivered items have no coverage: a coverage is a
promise of how long stock lasts against demand that, for them, nobody
plans. Their means still show, as history.

### The state set by hand

`Item.status`, one of `active` (default), `not_needed` and
`discontinued`, labelled `aktiv`, `nicht benötigt` and `auslaufend`.
It belongs to the item, one size, because a size is discontinued while
its article lives on. It is edited in the item's edit form and the
admin and recorded in the history.

### Planning ignores dormant and never-delivered items

`Plan._item` gives such an item no demand model, and the article's
bulk unit, where its compound has no molar mass, comes from its first
item that planning keeps, so that a dormant size cannot make the
article's lots unconvertible. Every figure that
looks only at items with demand, the joint certainty, `s_max`, the
runway, the yield and the fill action, then leaves it out; the item
still belongs to its article, still matches tasks through it, and still
shows in the planning list's `Gebinde` with its level. An article
whose items are all dormant has no forecast.

### The day an item entered stock

`Item.stocked_on`, a date or none. `_movement`, through which every
booking passes, sets it to the movement's date by a conditional update
when the movement leaves the item above zero containers and the item
has none, so the opening count, the first filling or a correction finds
it, and records the change in the item's history as the movement's
user's; an opening count above zero sets it on the item as it is
created. No migration fills it for existing items: the product has no
users, and a demo database is seeded again. The edit form and the
admin may change it, never after today, so that an item entered from
the paper records carries the day it really entered stock rather than
the day it was typed in.

The mark `neu` shows when `stocked_on` lies in the current calendar
year in `Europe/Berlin`. It is a `sup` with the class `mark-new` after
the item's name in the item list and on the item page, coloured with
the site's link colour.

Rejected: deriving the day from the movements alone. The year the
inventory moves from Excel into the application, every opening count
would be dated that year, and every position would be marked new.

### Projected means

When all of an item's consumption above zero lies in the current year,
its mean per quarter is the current year's consumption times 91.3125
divided by the days from the first day of the quarter of its first
consumption above zero to today, today included, counted as at least
91.3125; the mean per year is four times that. The means, and the
coverage computed from them, are marked as projected: in the list and on
the page they carry the class `projected` and the title `hochgerechnet
aus dem laufenden Jahr` (`projected from the current year`).

The quarter's first day rather than the first delivery's date keeps
entered values, which carry no day, and deliveries on one footing; the
floor of one quarter keeps a single early delivery from projecting a
huge rate.

### The list's cells and legend

The stock cell holds the number alone, its level's label in a
`span.visually-hidden` and in the cell's `title`. The legend is one
entry per level, in urgency order, each with its colour swatch, its
label, what it means, and how many items of the inventory are in it,
linking to the list with `stock=<level>`, which lists exactly the
items at that level. The existing `level` filter, a level or a more
urgent one, stays.

### Colours

`ok` takes a green darker and more saturated than `watch`'s pale
green, `undelivered` a light slate blue, and `dormant` a dark grey with
light text, each as tokens with a dark-scheme variant and a contrast of
at least 4.5:1 for the cell's text, as the four levels have.

## Risks / Trade-offs

- An item delivered once two years ago and never since turns grey even
  if it is still wanted. → The rule is the owner's; delivering it again
  or a single entered value restores its level.
- The projection over-weights an early burst of orders in a new item's
  first quarter. → Marked as projected, and replaced by the mean of
  complete years from the next year on.
