## Context

The item list renders on the server under a GET form of filters
(`category`, `compartment`, `box`, `level`, `q`, `sort` and a hidden
`stock`) and carries no script: the web-app Page shell allows none.
Rows are built for the whole inventory, filtered in Python, and sorted
by `Item.sort_key` or, with `sort=urgency`, by `Row.urgency`. The
legend already counts over the whole inventory, not the filtered rows.
The ticked rows' check boxes reach the separate form `pick` through
HTML's `form` attribute. The table sits in the site's `div.table-scroll`,
which scrolls sideways only.

## Goals / Non-Goals

**Goals:**

- Sort and filter by each column, with every view a bookmarkable URL.
- See at a glance which articles are consumed most.
- Keep the headers and the article number in view on a long, wide list.

**Non-Goals:**

- Heat relative to an item's category or container size.
- Range filters on number columns.
- Sorting by several columns at once.

## Decisions

### Sorting by links in the headers

Each header is a link to the list with the filters in force and
`sort=<column>`; when the list is already sorted by that column
ascending, the link adds `dir=desc`. The sorted header carries
`aria-sort`. Links need no script, and a URL names every view.

The rows are first put in the default order, then sorted stably by the
column's key, reversed for `dir=desc`; Python's sort keeps ties in
their order under `reverse=True`, so ties stay in the default order in
both directions. Items with no value in the column, such as no
category or no coverage, are split off before sorting and appended in
the default order, so blanks never crowd the top of a descending list.

`stock` sorts as `sort=urgency` did: by level, then coverage. Its name
follows the column, like every other key. `container` compares sizes in
the base unit (mg or µmol), mass before amount of substance, so 1 g
follows 250 mg. `compartment` and `box` use the natural order the
location choices already use.

### The filter row

A second row in `thead` holds a control per filtered column, each with
`form="filters"` and an `aria-label` naming its column, the trick the
check boxes use. The form `filters` above the table holds the search
`q`, hidden `sort` and `dir`, the button and a reset link, so pressing
Enter in any text field submits it. Number columns get no control.

`level`, a level and the more urgent ones, goes: sorting by `Bestand`
puts the urgent items first, and the exact `stock` choice replaces the
filter the legend links already used. The `Order` choice goes for the
same reason. The search `q` stays for finding text in the article
number, name, category or note, or in the compound's name, at once.

`container` values are `<size> <unit>` with the plain size and the
unit's code, as `2.5 mg` or `10 umol`, independent of the language;
the options are labelled as the column shows them.

### Heat by fifths of the consuming items

For each of `Ø Jahr` and `lfd. Jahr` on its own, the cell of a value
above zero gets `heat-<n>`, `n = 1 + ⌊5B/N⌋`, N the items of the
inventory with a value above zero in that column and B those with a
smaller value. Ranks, not value thresholds, so one heavily used
article does not leave every other cell pale; ties share a step. The
count runs over the whole inventory, like the legend, so a filter does
not recolour the cells. Zero and no value stay uncoloured. The steps
run from pale pink to a blackish red; their text keeps the contrast
the level colours keep, tested the same way.

### Grouped sizes

Sorted by `number`, a row whose article number equals the row
before's, both being set, carries `same-article`: its name is visually hidden, kept for
screen readers, and its article number is muted; the rule between the
rows of one article is lighter. Every size keeps its own link and
check box. In other orders the sizes of an article need not be
adjacent, so nothing is grouped. Items without an article number are
unrelated positions that happen to sort together, so they are never
grouped.

### Sticky header and first column

The item list's scroll box gains `table-sticky`: it scrolls in both
directions and is at most the window's height less a margin, `thead`
is `position: sticky` at its top and the first column's cells at its
left, both on an opaque background. A sticky header inside a box that
scrolls sideways only would stick to that box, which does not scroll
vertically, so the box must scroll both ways. `lab.css` loads after
`print.css` and unscoped, so these rules sit inside `@media screen`:
the printed list keeps `print.css`'s visible overflow, no height limit
and static positions. A test checks the scoping; a browser on the demo
data checks the sticking, the overlap of header and first column,
and printing a long list.

## Risks / Trade-offs

- A page and a box that both scroll. → The box is at most the window's
  height, so scrolling the page brings it whole into view.
- Bookmarks with `level=` or `sort=urgency` lose their filter or order.
  → An alpha with no users; unknown values fall back to the defaults.
- Fifths by rank compare a 5 g size with a 100 mg one. → Recorded in
  `STATE.md` as heat by category and size.
