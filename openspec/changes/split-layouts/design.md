# Design: Split layouts

## Context

`c-split-layout` (`orgsyndb_web/templates/cotton/split_layout.html`)
renders `div.item-layout[data-controller=split-list]` around a
`table-scroll` slot and a `detail` slot; `split` adds
`item-layout--split`, which only the intermediate and commercial
chemical lists pass and which `lab.css` turns into a stacked 45/55 grid
in the details view. Every other list puts its pane beside the table.

`SplitListController` (`lab.js`) selects rows matching
`.main-table tbody tr[data-item]` anywhere on the page, fetches the
pane through the row's `hx-get`, writes `selected` into
`#filter-selected` and the address, relinks the list's own links, moves
with the arrow keys, and switches the view through `input[name=view]`
radio buttons and the list's cookie. Its identifiers are page-wide, so a
second level inside the pane would collide with the first.

The panes are ad hoc: `dl.detail-figures`, `h3` headings and loose
tables, except planning's, which already uses two widgets.

Owner decisions of 2026-11-28 (with the mockups of direction B in the
owner's workspace):

- terms: **stacked** (rows) and **side by side** (columns);
- option A: a layout element plus a reusable selection controller,
  nestable, like a tiling window manager; no resizing; the golden ratio;
- by default the table takes the larger share, and each list can give
  it to the pane instead, remembered per list in a cookie;
- per-widget scrolling; the widget grid follows the content (one
  column for the category lots, three for the item pane, two
  elsewhere), with no rule in the specs;
- the delivery list side by side, the pane larger;
- the category panes: a lot table beside the lot's details, `lot=<vessel
  id>`; the vessel's note and actions move into the lot's details; the
  lot table has the main look and sorts in the browser.

## Goals / Non-Goals

Goals: one layout element and one selection controller for every split,
nestable; every pane in widgets; the category lists' lots selectable.

Non-goals: resizing; more than two levels; server sorting of lot
tables; changing what any pane holds beyond the category lots.

## Decisions

### 1. The split element

`<c-split dir="rows|columns" major="first|second" cookie="...">` with
the slots `first` and `second` renders

```html
<div class="split split--rows" data-major="first" data-controller="split" data-split-cookie-value="...">
  <div class="split__pane">…first…</div>
  <div class="split__pane">…second…</div>
</div>
```

- The larger side takes `1.618fr` and the other `1fr` (`grid-template-rows`
  or `-columns`). `data-major` names the larger side.
- Each pane is a grid cell with `min-height: 0`/`min-width: 0`; what
  scrolls is the table box or each widget, never the pane as a whole.
- Below `55rem` a `columns` split becomes `rows`; a `rows` split lets
  the page scroll, each pane at its natural height, the table box capped
  at about a third of the window.
- Splits nest: a pane holds any content, another split included.
- The view switch (`Tabelle`/`Details`) zooms the outer split: in the
  table view only the first pane shows. It keeps its radio buttons, its
  list cookie and its no-script fallback.

The toggle is one button in the list's toolbar beside the view switch,
`Größere Fläche: Tabelle | Details` (`Larger area: table | details`),
shown only in the details view. The `split` controller swaps
`data-major` and writes the cookie `<list>-split` (`first` or `second`,
a year, `SameSite=Lax`, the list's path); `orgsyndb_web.lists` reads it
(`split_major(request, cookie, default)`) so the page renders the
remembered ratio without a flash. Defaults: `first` (the table) on every
list but the delivery list, `second` there.

Rejected: one setting for all lists (owner chose per list); a ratio in
the address (layout is not state worth bookmarking).

### 2. The master-detail controller

`master-detail` sits on the split and takes values instead of page-wide
identifiers:

| Value | Outer level | Category lot level |
|---|---|---|
| `rows` (tbody id) | `item-rows` | `lot-rows` |
| `pane` (pane id) | `item-detail` | `lot-detail` |
| `param` | `selected` | `lot` |
| `field` (hidden-field host) | `filter-selected` | `filter-selected` |

It binds only the rows of its own `tbody` (`#<rows> > tr[data-item]`),
so the outer level never reacts to lot rows and the reverse. A row click
(ignoring links, buttons, labels and form controls) or an arrow key in
its table selects, marks `aria-current`, triggers the row's `hx-get`,
writes its `param` into the hidden field and into the address with
`history.replaceState`, and relinks the list's own links
(`OWN_LINKS`) with that parameter. A new outer selection drops `lot`
from the address, the field and the links, since the new pane brings
its own lots. The view radio buttons stay the outer controller's.

Each level's pane carries `data-item`; after an htmx swap the
controller re-reads it, as `split-list` does today. Form-dialog refresh
(`data-refresh`) covers `#lot-rows` and `#lot-detail` too.

Rejected: keeping fixed identifiers (they collide when nested; this
reverses the unified-list-tables decision, which predates nesting);
a server-side layout tree (layout moves out of the templates); a custom
element (a second component model).

### 3. Widgets in panes

Each pane is `aside#item-detail` (or `#lot-detail`) holding:

- a pane head (`c-pane-head`): the record's title linking to its page,
  its key facts, the main action, an `Aktionen ▾` menu (a popover) for
  the others, and `…seite öffnen →`;
- a widget grid (`c-widget-grid columns="1|2|3"`): `c-widget`s whose
  heading is an `h3` (the pane title is the `h2`), each body scrolling
  on its own within the pane's height.

Figures become key–value rows inside a widget, not tiles. Breakdown:

| Pane | Columns | Widgets |
|---|---|---|
| item | 3 | Bestand & Lagerort (stock, coverage, means, this year, compartment, box, note); Verbrauch (bars, quarter table); Bulk (vessels, fill count) |
| bulk | 2 | Letzte Buchungen; Gefäßdaten |
| delivery | 1 | Lieferschein (date, recipient, marks); Zeilen |
| batch | 2 | Offene Gefäße; Chargendaten |
| vessel | 2 | Letzte Buchungen; Gefäßdaten |
| task | 2 | Stufen, Notiz; Aufgabendaten |
| substance | 2 | Gebinde, Chargen, Aufgaben; Verbindung |
| planning | 2 | Gebinde & Bedarf; Planungsdetails |
| category | — | a nested `columns` split: the lot table; the lot's details (Gefäßdaten, Letzte Buchungen, one column) |

The ui-specialist may adjust the grid where a pane reads better
otherwise; the specs fix none of it.

### 4. The category lots

- Routes `intermediates/<str:key>/lots/<int:pk>/` and
  `chemicals/<str:key>/lots/<int:pk>/` render the lot partial
  (`#lot-detail`) through the existing `htmx_detail_or_redirect`,
  keeping `HX-Current-URL`'s filters and adding `selected` and `lot`
  (omitted for the first lot).
- The substance pane (`/lab/inventory/<category>/<key>/`) renders the
  lot table and the selected lot (`lot` from the request, else the
  first).
- The lot table drops `Bemerkung` and the action links; the lot's
  details reuse the vessel list's details partial content.
- Unknown key, unknown id, or an id of another substance or category
  answers 404.

### 5. Removals

`c-split-layout`, `SplitListController`, `.item-layout*`,
`.split-detail-*`, `.split-vessel-*`, `.split-movements-*`,
`.detail-figures`, `.detail-location`, `.detail-lots`, the single-vessel
movements block and its context (`single_vessel`, `ledger` in the
category pane), and every string only they used.

## Risks / Trade-offs

- **Two levels of keyboard selection.** Arrow keys act on the table that
  holds focus; the outer table keeps focus after a click in it, the lot
  table after a click there.
- **Address noise.** `lot` appears only off the first lot.
- **Print.** Panes stay off paper, as today.

## Migration Plan

None. Pre-1.0: the old component, controller and classes go outright.
