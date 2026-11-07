## Why

The item list is the lab's working view of the end-product stock, and
it is wide: twelve columns of figures and text per size. Staff sort and
filter it the way they did in Excel, column by column, but the list
offers one order besides the default and a handful of filters in a form
above the table. Consumption shows as bare numbers, so a heavily used
article does not stand out, and Ø Quartal is always a quarter of
Ø Jahr. Scrolling a long list loses the column headers, and scrolling
sideways loses the article number. The owner asked for basic sorting
and filtering per column, a naive heat colouring of the consumption,
and accepted a sticky table and grouped sizes.

## What Changes

- Every column header sorts the list by that column, and choosing it
  again reverses the order. `sort=stock` takes the place of
  `sort=urgency`; the `Order` choice goes. Empty values come last in
  either direction.
- A filter row below the headers: "contains" text fields for
  `Artikelnr.`, `Name` and `Bemerkung`, choices of the values in use
  for `Kategorie`, `Gebinde`, `Fach` and `Box`, and the exact level
  for `Bestand`. The search over all text stays above the table. The
  filter of a level and the more urgent ones (`level`) goes.
  **BREAKING** for bookmarks with `level=` or `sort=urgency`.
- `Ø Jahr` and `lfd. Jahr` cells are coloured from pale pink to a
  blackish red by the fifth of the inventory's consuming items they
  fall in; the legend shows the scale.
- `Ø Quartal` leaves the list; the item page keeps it.
- Sorted by article number, the sizes of one article are grouped: the
  name shows once.
- The table's header rows and first column stay in view while it
  scrolls.
- `STATE.md` records heat colouring by category and size as wanted.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: the item list's columns, ordering, filters,
  grouping and scroll box; a new requirement for the consumption heat.

## Impact

- Changed: `inventory` views, the item list and legend templates,
  `lab.css`, the German translations, their tests.
- Docs: `README.md`, on finding stock in the item list.
- Not included: heat relative to an item's category or size, which
  `STATE.md` records; filters on number columns.
