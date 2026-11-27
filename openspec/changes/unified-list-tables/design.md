# Design: Unified list tables

## Context

The lab has ten lists the owner calls main tables, in Bestand (seven),
Planung, Aufgaben and Substanzen. They share these pieces:

- `c-filter-bar`, `c-list-heading` and `c-split-layout`;
- `c-sort-th`, used only by the item list;
- the Stimulus controllers `sortable-table` and `split-list`.

`split-list` has two modes. The `htmx` mode is hard-wired to
`.item-table tbody tr[data-item]`, `#item-rows` and `#item-detail`. The
`local` mode is hard-wired to planning's `tr[data-article]` and
`.planning-*` classes. Server sorting lives in `inventory/views/items.py`
(`ColumnSpec`, `ItemFilters.link`, `columns()`), on top of
`orgsyndb_web.lists.sort_rows`. Six CSS families style the tables:

- `.inventory-table`;
- `.item-table`, layered on `.inventory-table`;
- `.task-table`;
- `.widget-table`, which has no rules of its own;
- `.detail-table`;
- `.kv-table`.

There are also one-off rules on `#movements` and `.planning-table`.

The owner decided the following on 2026-11-27:

- every main list gets a details pane, including the batch list, the
  vessel list, the task list and the substance list;
- every main list sorts on the server;
- the planning list moves to the HTMX split layout, with sorting and
  filtering in the address;
- widget and pane tables sort in the browser;
- there are two table styles;
- the Laborjournale, Importe, Vokabulare and Zugangsschlüssel tables only
  take the auxiliary style.

## Goals / Non-Goals

Goals: one sorting contract, one selection mechanism and two table
styles across the ten lists, with every secondary record table in a
widget or pane sortable in the browser.

Non-goals:

- paging;
- column hiding beyond the item list's;
- sorting the record pages' own tables (batch, vessel and delivery note
  pages);
- sorting or selecting on the lists outside the four views;
- changing what any list filters.

## Decisions

### 1. One generic requirement with a table of lists

`web-app` gains "Main lists". It states the contract once and names, in
one table, each list's path, column keys, default order, details
endpoint and view cookie. Each capability adds only what is its own: the
content of its new details panes, and its live-list wiring.

Rejected: restating sorting and selection in each list's requirement.
That gives ten copies to keep in step, and several of those requirements
run over a hundred lines.

### 2. Server sorting machinery in `orgsyndb_web.lists`

`lists.py` gains a list-agnostic column model:

- a column with a key, a label, a value function and whether it sorts;
- an `Order` parsed from `sort` / `dir` against a list's columns and its
  default (key and direction);
- the header links (the toggle rule, with the filters and `selected`
  kept);
- `aria-sort`;
- the canonical query pairs, which omit the default order.

A `sort_value` helper turns a shown value into an ordering key: numbers
and amounts first, then dates, then text, with empty values and `–`
last in either direction. It mirrors the client sorter's rules, so both
kinds of table order alike.

Amounts convert to the smallest unit of their kind (mg, µmol). Masses
come before amounts of substance.

`sort_rows` stays stable over rows given in the default order, so equal
values keep the default order. The item list's `ColumnSpec` and
`ItemFilters` move onto this model. Its own `TIES` text, the list
summary's "order in words", stays item-list specific.

Rejected: client sorting for the main lists. The owner chose server
sorting, which keeps the order in the address, works without the
script, and lets the item list keep its category grouping rows.

### 3. One selection mechanism, shared identifiers

Every main list renders its body as `#item-rows`, its rows with
`data-item`, `hx-get` to its details endpoint and `hx-trigger="item-select"`,
and its pane as `#item-detail` inside `c-split-layout`. `split-list`
keeps only its `htmx` mode, with its row selector widened to
`.main-table tbody tr[data-item]`. Its local mode goes, and so do the
planning-only `planFilterShows` helper and any helper the local mode
alone used.

Each page holds one main list, so the fixed identifiers do not collide.
The existing count identifiers (`#task-counts`, `#substance-count`,
`#batch-count`, `#vessel-count`) stay. The row identifiers
`task-row-<pk>` and `substance-row-<pk>` stay too, for idiomorph.

Rejected: per-list identifiers passed to the controller as Stimulus
values. That adds configuration to every page for no behaviour the
owner asked for.

### 4. Details endpoints

| List | Endpoint |
|---|---|
| batch | `/lab/inventory/batches/<id>/detail/` |
| vessel | `/lab/inventory/vessels/<id>/detail/` |
| task | `/lab/tasks/<number>/detail/` |
| substance | `/lab/registry/substances/<key>/detail/` |
| planning | `/lab/planning/<article number>/detail/` |

They follow the `/detail/` suffix of the item and delivery endpoints.
The task route goes before `<number>/<action>/`, so `detail` never
reaches `task_action`. Each endpoint answers as web-app "Live lists"
states: for HTMX, the fragment with `HX-Replace-Url`; otherwise, a
redirect to the list with `selected`.

### 5. The planning list

- The planning list loses its list widget. Its main table sits in the
  split layout, and the parameters widget stays.
- A live filter form replaces the filter buttons and the "All articles"
  link. It has a `show` select (`Alle`, `Priorität hoch`, `Mit Maßnahme`,
  `Verspätet`) and an `all` check box. Filtering is server-side and kept
  in the address.
- The inspector's two widgets become the pane's two parts.
- The `Artikel` cell links to the substance's page, like every other
  list's name column, because a link in a row no longer selects the row.
- The planning list opens in the details view without a cookie. The
  inspector beside the list is its reason to exist, and its table is
  narrow.
- The default column is `Spätester Start` ascending. The latest start is
  today plus the slack, so this order equals the stated slack order,
  with ties broken by it.

Rejected: keeping local selection with server sorting. That leaves two
selection mechanisms and a filter state that does not survive a sort.

### 6. Two table styles

`lab.css` defines `.main-table` (dense, bordered cells, hover and
selection marks, sticky first column in the split layout) and
`.aux-table` (smaller type, lighter headers, no cell borders).
`.kv-table` stays as a modifier of `.aux-table` for its label column.
Modifiers remain only for column width and wrapping (`col-*`,
`category-table`, and similar). They do not restyle a table's look.

The rules on `inventory-table`, `item-table`, `task-table`,
`widget-table`, `detail-table`, `planning-table` and `#movements` go.
One sort-indicator style covers both the server header links and the
client `button.sort-header`.

Rejected: keeping `kv-table` as a third style. The owner asked for two
styles, and a key–value table is an auxiliary table with a label column.

### 7. Client-sortable auxiliary tables

Every auxiliary table in a widget or a detail pane that lists records
one per row gets `data-sortable`, a unique `id` and `data-sort` keys on
date, time and mixed-unit cells. This covers:

- the item page's tables;
- the substance page's tables;
- the overview's tables;
- the panes' movement, vessel, line, step, item and batch tables;
- the planning pane's container table.

It excludes:

- key–value tables, which are not row lists;
- the consumption quarter tables, which are time series headed by row
  headers;
- the change history, whose rows of one save share `rowspan` cells.

### 8. Canonical address

Live responses push `sort`, and `dir=desc` when descending, only when
the order in force is not the default. Today the item list always
pushes `sort=category`. That changes, and its live-list requirement is
amended. Header links may still name the default order explicitly.

## Risks / Trade-offs

- **Size.** The change touches every list template and view, so tasks
  are grouped by list, and the area tests are run per group.
- **Planning without the script.** Rows can no longer be selected through
  the article link. The pane still shows the first row, or the article
  `selected` names.
- **Losing the planning filter buttons' instant response.** The live form
  answers within one request. This is accepted for the filters being
  kept in the address.
- **Pane cost.** The planning details endpoint recomputes the whole plan.
  The plan is built per request today too, and the list holds tens of
  articles.

## Migration Plan

None. No data changes. Pre-1.0, the old classes, identifiers, the local
mode and the planning filter buttons are removed outright.
