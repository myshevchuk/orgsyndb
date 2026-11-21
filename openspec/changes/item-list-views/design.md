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

**Hiding rules come from the model.** The page renders, inside
`main`, a `<style>` element with one rule per table-view column:
`main:has(#column-<key>:not(:checked)) .item-table .col-<key>` hides
the column. One static rule in `lab.css` hides `.table-only` while
the details view shows. Adding a column, or moving one between the
groups, then needs no edit of `lab.css`. The `Spalten` menu lists the
table-view columns alone.

**Geometry.** The item table drops `width: 100%` and takes its
natural width; every cell but the note's is `nowrap`, so a base
column is as wide as its widest content in both views. In the table
view the note column, when shown, takes the remaining width. In the
details view the grid gives the table its natural width, at most
what is left beside a pane of at least 20rem, and the pane the rest.
Below 55rem the pane stays under the table, as now.

**Two-part switch, view in a cookie.** The switch is a fieldset of two
radio buttons, `#view-table` (`Tabelle`) and `#view-details`
(`Details`), named `view`, outside any form, with a visually hidden
legend `Ansicht` (`View`). `lab.css` reads `#view-details:checked`
where it read `#detail-switch:checked`, so the views switch without a
script too. A change sets the cookie `item-list-view` to `table` or
`details`, path `/lab/inventory/end-products/`, a year's `max-age`,
`SameSite=Lax`. The view reads it and checks the matching radio; any
other value is the table view. The checkbox `#detail-switch`, its
`data-remember` key and the rule that `detail` in the address turns it
on go. The `Spalten` button is disabled while the details view shows.

**`selected` in the address.** `chosen_row` reads `selected`; the
details' URL redirects a request without htmx to `?selected=<id>`.
The selected row carries `aria-current="true"` in both views, and
`lab.css` marks it in both. The server writes the request's
`selected` into the list's links to itself (the column headers, the
stock levels, `Zurücksetzen`) and as a hidden field into the filter
form. After each selection `lab.js` writes the new id into the
address, into that hidden field and into those links' `selected`, so
a later filter or reorder keeps it; a `selected` that the new list
does not hold falls back to the first row, as now.
`OrgSynLab.detailSearch` becomes `OrgSynLab.paramSearch(search, name,
value)`, which sets or removes one parameter, so the address and the
links share it.

**Selection in both views.** Rows take focus (`tabindex="-1"`) in
both views. A click without a modifier key in a row selects it unless
it lands on a link or an `input`; links follow their targets. ↑ and ↓
in the table move from the focused row, else the marked one. Selecting
fires `item-select`, so htmx loads the pane in both views, hidden or
not, and switching to the details view needs no request. Mark and
address still move only after the swap, as `item-detail-pane` settled,
so they never name an item other than the pane's.

**Animated switch.** The radio's click is cancelled, and inside
`document.startViewTransition(update)` `update` checks the radio and
dispatches `change`, so that the browser takes its snapshot of the old
view before the change. The pane and the table box get their own
`view-transition-name`, so the pane slides in beside base columns
that stay where they are, and the table view's columns fade. Without
`startViewTransition`, or under `prefers-reduced-motion: reduce`, the
switch changes at once. The keyboard selects radios through click
events too, so the arrow keys animate as well.

## Risks / Trade-offs

- [The mark follows the load in the table view too] → holding ↓
  aborts each request for the next, so the mark waits until the key
  is released and the last request has answered; the focused row
  shows the keyboard's place meanwhile. Checked by hand (tasks 4.2).
- [A `<style>` element in the page] → the application sends no
  Content Security Policy; one that forbids inline styles later must
  allow this element or move the rules to a generated stylesheet.
- [Natural width] → a table wider than the window scrolls in its
  box, as now; a very long name widens the name column in both views
  alike, which is the point.
