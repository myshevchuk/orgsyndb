# Change: Unified list tables

## Why

The lab's lists grew one at a time, and each built its table by hand.
Of the ten lists in Bestand, Planung, Aufgaben and Substanzen, one sorts
on the server (the item list), one sorts in the browser (the planning
list) and eight do not sort at all. Six select a row and load its
details, five of them through HTMX and the planning list through a
second, browser-only mechanism. The batch list, the vessel list, the
task list and the substance list cannot select a row. Among the
secondary tables, one (the item page's movements) sorts and the rest do
not. Six CSS families style the tables, partly duplicating one another
and partly reaching single tables by `id`.

The owner wants one experience for the lab's lists. Every main list
sorts on the server, selects a row and shows its details in a pane, the
way the Bestand item list does. Every secondary table in a widget or a
detail pane sorts in the browser, the way the movements table does. There
are exactly two table styles, main and auxiliary.

## What Changes

- **Main lists** (`web-app`, ADDED): one requirement naming the ten main
  lists with their column keys, default orders, details endpoints and
  view cookies. It states the shared contract:
  - server sorting through `sort` and `dir`;
  - header links and `aria-sort`;
  - how column values order;
  - the canonical address, which names the order only when it is not the
    default;
  - row selection and the `#item-rows` / `#item-detail` split layout;
  - the `Tabelle` / `Details` views;
  - the two table classes `main-table` and `aux-table`.
- **Widgets** (`web-app`, MODIFIED): every auxiliary table in a widget or
  a detail pane that lists records one per row is client-sortable. The
  exceptions are key–value tables, the consumption quarter tables and the
  change history.
- **Batch details** and **Vessel details** (`end-product-inventory`,
  ADDED): the batch list and the vessel list become split lists with
  details endpoints.
- **Live inventory lists** (`end-product-inventory`, MODIFIED): every
  inventory list's live response pushes the order and the selection, and
  the item list no longer pushes its default order.
- **Task details** (`task-tracker`, ADDED) and **Live task list**
  (MODIFIED): the task list becomes a split list.
- **Substance details** (`lab-registry`, ADDED) and **Live substance
  list** (MODIFIED): the substance list becomes a split list.
- **Planning list** (`production-planning`, MODIFIED): the planning list
  becomes a main list:
  - it sorts on the server;
  - a live filter form with `show` and `all` replaces the browser-only
    filter buttons and the `all=1` link;
  - an HTMX details pane replaces the inspector's hidden blocks;
  - the list widget is gone, and the article's name links to its
    substance's page.
- `lab.js` loses the split list's local mode and the planning-only
  helpers. `lab.css` replaces `inventory-table`, `item-table`,
  `task-table`, `widget-table`, `detail-table`, `planning-table` and the
  `#movements` rules with `main-table` and `aux-table`.

## Impact

- Affected specs: `web-app`, `end-product-inventory`, `task-tracker`,
  `lab-registry`, `production-planning`.
- Affected code:
  - `webapp/orgsyndb_web/lists.py` (shared sorting);
  - the view modules of the ten lists and their new details endpoints
    (`inventory/views/*.py`, `tasks/views.py`, `registry/views.py`,
    `planning/views.py`) and their URL confs;
  - every template holding a `<table>` under `webapp/*/templates/`;
  - the Cotton components `sort_th` and `split_layout`;
  - `lab.js`, `lab.css`, and the German message catalogues.
- Affected tests: the list, live-list, planning, widget and script tests
  under `webapp/tests/`.
- Not affected: the Laborjournale, Importe, Vokabulare and
  Zugangsschlüssel pages keep their tables unsorted and unselectable and
  only take the auxiliary class. The record pages of batches, vessels
  and delivery notes keep their tables unsorted.
