## Context

`item_list.html` renders one table whose twelve cells per row are
written out by hand, and the pane `#item-detail` as the template
partial `detail`. The view controls are controls outside any form
that `lab.css` reads with `:has()` and that `lab.js` keeps in local
storage under `data-remember`; the checkbox `#detail-switch` is one of
them. Checked, a rule inside `@media screen` hides seven columns by
name and lays the table and the pane out as a grid. The table is
`width: 100%` in both views.

Facts about columns are spread over `views.py`: `column_labels` (key,
label, unit, order), `SORT_VALUES`, `NUMERIC`, `FIXED_COLUMNS` and
`HIDDEN_COLUMNS`; the `Spalten` menu's hiding rules are hard-coded per
key in `lab.css`.

Selection exists in the details view only. `lab.js` fires
`item-select` on a row; htmx loads `/lab/inventory/items/<id>/detail/`
into `#item-detail` (`hx-sync="this:replace"` on the body); after the
swap `lab.js` marks the row with `aria-current="true"` and writes
`detail=<id>` with `history.replaceState`. The dialogs' refresh after
a save fetches `location.href` and replaces every `[data-refresh][id]`
element, so the server must read the selection from the address.

## Goals / Non-Goals

**Goals:** base columns that look and behave the same in both views;
one column model from which headers, cells, the `Spalten` menu and
every hiding rule come, so that a later change can let users choose
the base columns by changing where a column's group comes from;
selection in both views, kept across reloads, filtering, reordering
and dialog saves; the view as a per-browser preference the server
knows on the first request; an animated switch.

**Non-Goals:** a user interface for choosing base columns or the
order of columns; sorting and filtering through htmx (with Idiomorph,
`openspec/STATE.md`); any change to the pane's content or to the item
page; printing.

## Decisions

**One column model.** `views.py` gets one tuple of column
definitions, each with its key, label, unit, whether it is numeric,
its sort value, its group (`base` or `table`) and whether it shows by
default. It replaces `column_labels`, `SORT_VALUES`, `NUMERIC`,
`FIXED_COLUMNS` and `HIDDEN_COLUMNS`; labels stay lazy so that the
active language applies, and the year in the unit of `this_year` is
filled in when the list is rendered. `columns()` returns the bound
columns in the model's order, base columns first.

The template iterates the bound columns for the header and, per row,
renders each cell through one partial `cell` that picks its markup by
the column's key. Each cell carries `col-<key>`, and each cell of a
table-view column also `table-only`. A per-column template file was
rejected: twelve includes per row cost a loader lookup each on lists
of hundreds of rows, where a partial renders from the parsed
template.

**Hiding rules come from the model.** The list fills the page shell's
`head` block with a `<style>` element holding one rule per table-view
column: `main:has(#column-<key>:not(:checked)) .item-table
.col-<key>` hides the column. One static rule in `lab.css` hides
`.table-only` while the details view shows. Adding a column, or
moving one between the groups, then needs no edit of `lab.css`. The
`Spalten` menu lists the table-view columns alone.

**Geometry.** `.item-table` overrides the `width: 100%` that
`.inventory-table` gives every list and takes its natural width. Every
base cell is `nowrap`, header and units included, so its minimum and
maximum content widths are equal; the automatic table layout then
gives each base column its widest content's width whatever the other
columns do, and a table wider than its box overflows into the box's
scroll range rather than narrowing a base column. In the table view
the note column, when shown, takes the width left over. In the
details view the grid gives the table box its natural width, at most
what is left beside a pane of at least 20rem, and the pane the rest.
Below 55rem the pane stays under the table, as now.

A base column keeps its width and its left edge relative to the
table. Where the box is scrolled sideways and the details view leaves
less to scroll, the browser clamps the scroll offset, so the table may
move as a whole; that is accepted, and the base columns still line up
with themselves.

**Two-part switch, view in a cookie.** The switch is a fieldset of two
radio buttons, `#view-table` (`Tabelle`) and `#view-details`
(`Details`), named `view`, outside any form, with a visually hidden
legend `Ansicht` (`View`). The view reads the cookie `item-list-view`
and checks the matching radio, any other value being the table view,
and renders the same view as `data-view` on `.item-layout`. On a
change `lab.js` sets the cookie to `table` or `details`, path
`/lab/inventory/end-products/`, a year's `max-age`, `SameSite=Lax`.
The checkbox `#detail-switch`, its `data-remember` key and the rule
that `detail` in the address turns it on go. The `Spalten` button is
disabled while the details view shows.

The layout follows `data-view`. `lab.js` marks `.item-layout` with
`data-scripted` when it starts; until then, and on a page without the
script, the layout follows `#view-details:checked` instead. Both agree
on the first paint, since the server renders both from the cookie.

**`selected` in the address.** `chosen_row` reads `selected`; the
details' URL redirects a request without htmx to `?selected=<id>`.
The selected row carries `aria-current="true"` in both views, and
`lab.css` marks it in both. The server writes the id of the row it
selected, whether `selected` named it or the first row stands in, into
the list's links to itself (the column headers, the stock levels,
`Zurücksetzen`) and as a hidden field into the filter form, and leaves
it out of them for an empty list; a stale `selected` therefore never
travels on. `OrgSynLab.detailSearch` becomes
`OrgSynLab.paramSearch(search, name, value)`, which sets or removes
one parameter, so the address and the links share it.

`lab.js` keeps all of these in step with the pane through one
function, `follow(id)`: it marks the row of `id`, and writes `id` into
the address, the hidden field and every link of the list to itself,
or removes `selected` from them when `id` is empty. It runs after a
row's details are swapped in and after a dialog's refresh, in either
view, with the id the pane carries as `data-item`. The refresh
replaces the rows, the pane, the stock levels and the reset link with
the fetched page's, which the server rendered from the address; the
column headers and the hidden field stay, and `follow` brings them up
to date, also when the save moved the selected item out of the
filters and the fetched page selected another.

**Selection in both views.** Rows take focus (`tabindex="-1"`) in
both views. A click without a modifier key in a row selects it unless
it lands on a link or an `input`; links follow their targets. ↑ and ↓
in the table move from the focused row, else the marked one. Selecting
fires `item-select`, so htmx loads the pane in both views, hidden or
not, and switching to the details view needs no request. Mark and
address still move only after the swap, as `item-detail-pane` settled,
so they never name an item other than the pane's.

**Animated switch.** The radios keep their native activation: click,
Space and the arrow keys check them and fire `input` and `change` as
the browser does. Because the layout follows `data-view` and not the
radios, the `change` handler can call
`document.startViewTransition(() => { layout.dataset.view = view; })`,
and the browser snapshots the old layout before the attribute
changes. A `change` that names the view already shown does nothing.

The intended effect: the base columns stand still, the table view's
columns fade out or in, and the pane slides in from the right or out
to it. The table box and the pane get their own
`view-transition-name`. The table box's old and new snapshots are
drawn unscaled, anchored at their left edge (`object-fit: none`,
`object-position: left top`, a full-size image in a group that clips),
so that its width animating does not stretch the columns; the pane's
entering and leaving snapshots get a slide keyed to the same
duration. Without `startViewTransition`, or under
`prefers-reduced-motion: reduce`, the attribute changes at once.

## Risks / Trade-offs

- [The mark follows the load in the table view too] → holding ↓
  aborts each request for the next, so the mark waits until the key
  is released and the last request has answered; the focused row
  shows the keyboard's place meanwhile. Checked by hand (tasks 4.2).
- [A `<style>` element in the page's head] → the application sends no
  Content Security Policy; one that forbids inline styles later must
  allow this element or move the rules to a generated stylesheet.
- [Natural width] → a table wider than the window scrolls in its
  box, as now; a very long name widens the name column in both views
  alike, which is the point.
- [Column geometry and the transition's look are a browser's] → no
  test client can measure them; tasks 4.2 measures the five base
  columns' widths and left edges in both views by script in a real
  browser.
