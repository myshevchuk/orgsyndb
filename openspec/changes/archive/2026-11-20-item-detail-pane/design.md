## Context

The item list (`inventory.views.item_list`, `item_list.html`) computes
for every item its figures, its bulk and its statistics, and renders
two popups per row from them: `Ort` (location and open lots) and
`Abgegeben` (consumption by quarter). Its view controls, `Spalten`,
`Zeilenhöhe` and `Verbrauch einfärben`, are controls outside any form
whose state `lab.css` reads with `:has()` and `lab.js` keeps in local
storage under `data-remember`. Since `adopt-htmx`, every page of the
shell loads htmx 2.0.11, configured with `allowEval` false, and then
`lab.js`. Django 6.0 renders a template partial by
`"template.html#name"`.

## Goals / Non-Goals

**Goals:** a reading pane beside a narrowed table, switched on and off
by the user and remembered; one item's details in it, chosen by click
or arrow keys and loaded in place; the address naming the item so that
a reload or a link shows it; the popups gone; the item list's
requirement cut to what is rooted deeper than its look.

**Non-Goals:** movements and the forecast in the pane; forms in
dialogs (the next change); sorting and filtering through htmx; any
change to the item page.

## Decisions

**A switch, not open-on-click.** The reading pane of mail clients and
file managers fits a list that is used both for scanning and for
working through items: the user chooses the mode, and the layout does
not jump on every click. The switch is a check box `Details`
(`Details`) among the view controls, `id="detail-switch"`,
`data-remember="item-list:detail"`, off by default. `lab.css` reads
it as it reads the others: checked, the table drops every column but
`Artikelnr.`, `Name`, `Gebinde`, `Bestand` and `Reichweite`, the
rows show a pointer and the chosen row a mark, and the pane shows.
These rules sit inside `@media screen`, so paper prints the whole
table without the pane.

**The server always renders the pane.** The list view puts one
item's details into the page: the item `detail` names, when it is
listed, else the first row listed, else a note that no item is
chosen; that row carries `aria-current="true"`, and the pane carries
the item's id as `data-item`. A `detail` that the filters leave out
falls back like a missing one, so the pane always belongs to a
listed row, which the arrow keys and the switch start from. The switch
then needs no request to show the pane, and a page loaded with
`detail` shows the item before any script runs. The figures, bulk and
statistics are computed for every row already.

**`detail` turns the switch on.** The view renders the switch checked
when the query holds `detail`. `lab.js` restores remembered controls
first and then, when the address holds `detail`, checks the switch
again and saves it, so that a shared link opens on the item whatever
the reader's stored choice. Turning the switch on writes the chosen
row's id into the address as `detail`; turning it off removes it, so
that a reload keeps the mode the user chose.

**htmx fetches, `lab.js` chooses and keeps the address.** Each row
carries `data-item="<id>"`, `hx-get` to
`/lab/inventory/items/<id>/detail/` and `hx-trigger="item-select"`;
the `tbody` carries `hx-target="#item-detail"`, `hx-swap="outerHTML"`,
`hx-sync="this:replace"` and `hx-indicator="#item-detail"`, inherited
by the rows, so a newer choice aborts an older request. With
`allowEval` false, trigger filters are unavailable, so `lab.js`
decides when a row is chosen: while the switch is checked, a click in
a row that is not on its check box, without a modifier key or the
middle button, chooses it and keeps a link in the row from being
followed, as the owner decided on 2026-11-18; ↑ and ↓ in the table
choose the row above or below the focused one, or the marked one, and
focus it. Choosing fires `item-select` on the row and nothing else.
Only when htmx has swapped the new pane in (`htmx:afterSwap` on the
row) does `lab.js` move `aria-current` to that row and set `detail` in
the address with `history.replaceState`; an aborted request, or one
that fails, which htmx 2 does not swap, leaves pane, mark and address
naming the same item. While a request runs, the pane carries
`htmx-request` and `lab.css` dims it and lets no pointer reach its
links, so the old item's actions cannot be used for the new row. The
address is not left to `hx-replace-url`, because htmx then saves a
copy of the whole page to session storage before each swap, which on
a long list would run on every arrow key. `OrgSynLab.detailSearch`,
the query with `detail` set or removed, is pure and tested under
Node.

**One partial, two views.** The declared Django range moves to
`>=6.0,<6.1`, since template partials came with 6.0; the lockfile
already holds 6.0.10. The pane is the partial `detail` of
`item_list.html`, rendered inline by the list and alone by
`item_detail`, the view of `/lab/inventory/items/<id>/detail/`. That
view answers an htmx request (`HX-Request: true`) with the partial
and any other request with a redirect to the list with
`detail=<id>`, the complete page Scripts asks for; it sends
`Vary: HX-Request`, and answers 404 for an unknown id. No
`django-htmx`: one header check suffices.

**What the pane holds.** A head with the name, linking to the
substance's page as in the table, the article number, container,
category, the mark `neu` and the status when it is not active; the
quantity with its level and the coverage; a link to the item's page
and, signed in, the item page's links; the compartment and box,
`nicht hinterlegt` for each not set, with the open lots, each with
location, batch and amount, linking to the lot; the consumption: this
year so far, the means, bars for the quarters of the current year and
the table of three years, the years with entered values, and the note
that the current year is not over; and the note. The heats stay in
the table: they rank an item among all items, which the detail view
of one item does not compute.

**Popups that stay.** The stock menu, `Weitere Filter` and `Spalten`
remain popups, so `lab.js` keeps placing them. The `Lagerort` column
goes with its button; `Abgegeben` becomes a plain number; `Fach` and
`Box` become visible by default, leaving only `Bemerkung` hidden at
first. The note below the table keeps its sentence on the stock
colours and names the switch instead of the popups.

**Sorting stays, unspecified.** The column headers keep sorting the
list through `sort` and `dir`, and the order line stays, as the code
has them; the requirement no longer names them. Links and forms do not
carry `detail`: a new order or filter shows the first item's details.

## Risks / Trade-offs

- A user who never turns the switch on still receives the pane's
  markup for one item; it is small beside the table.
- A `detail` that the filters leave out shows the first listed
  item instead, so a link naming an item and filters that exclude it
  does not open on that item.
- Server tests cannot follow a choice in the browser: the HTTP
  scenario checks the rows' attributes and the detail view, the Node
  test the address, and the test server the rest (task 4.2).
- A narrow window cannot hold both: below `55rem` the pane follows the
  table instead of standing beside it.
