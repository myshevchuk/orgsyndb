## Why

The item list's `Bestand` column tells only how urgent a stock is: four
levels and no colour at all for the rest. The lab's Excel colours every
position, and three situations matter beyond urgency: a stock that is
fine, a position never delivered, and one that no longer matters to
planning because nobody has asked for it in two years or because it is
being discontinued or is not needed. The owner also wants the column
reduced to coloured numbers, so that they align, with the legend saying
what each colour means. New positions, those that entered stock this
calendar year, carry a hand-typed `new` in the Excel note; the
application can derive the mark, and it needs a forecast for such
positions, which have no complete year of consumption yet.

## What Changes

- Every item gets one level: `ruhend` (dormant), `noch nie
  abgegeben` (never delivered), the four levels, or `ausreichend`
  (sufficient), the new name for a stock of at least twice the mean per
  quarter.
- An item is dormant when it is set aside by hand, as `nicht benötigt`
  (not needed) or `auslaufend` (discontinued), a state of its own on
  each item, or when it has consumption but none in the current or the
  previous calendar year. Planning leaves dormant and never-delivered
  items out.
- The item list's stock cells show the number alone, coloured by
  level, with the level's name as a tooltip and as text for
  screen readers. The legend names all seven levels with how many
  items are at each, and each entry lists those items.
- Items record the day they entered stock, `Im Bestand seit` (in stock
  since), set by the first movement that leaves containers and editable.
  An item that entered stock in the current calendar year is marked
  with a blue superscript `neu` (`new`) beside its name.
- An item whose consumption all lies in the current year gets means
  projected from it, marked as provisional, so that it has a level and
  a coverage from its first delivery on.
- The demo data shows every level and the mark.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: the item's state and stock entry date, the
  levels, the projected means, the list's stock cells, legend
  and level filter, the mark, the item page and forms.
- `production-planning`: dormant and never-delivered items have no
  demand.
- `lab-demo`: items at every level, and marked ones.

## Impact

- Changed: `inventory` models with a migration, bookings, figures,
  forms, views, templates, admin and `lab.css`; `planning.plan`; the
  demo data set; the German translations; their tests.
- Docs: `README.md`, on stock levels and the item list.
- `openspec/STATE.md`: the mean in an item's second year, which counts
  its partial first year as a whole one; handling discontinued items.
- Not included: restrictions on discontinued items, such as refusing
  new tasks for them.
