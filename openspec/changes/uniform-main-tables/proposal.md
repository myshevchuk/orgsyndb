## Why

The ten main lists now share one sorting and selection contract, but not
one look or one width. The item list alone offers a `Spalten` menu to
hide columns, an `Ansicht` menu to choose the row height and switch off
the consumption heat, and a details view that hides seven of its
columns. Its means and coverage carry an italic "projected" mark that
nothing on the page explains. At 1920×1080 the lab's main column stops at
about 1,150 px inside a centred shell, and the item, vessel and task
tables already overflow it, while long names stretch the name columns.

The owner decided on 2026-11-28 that every main table shows all its
columns in one uniform style and fits a standard monitor, and that the
controls and marks above go. These are interface decisions: the specs
lose the text that governs the removed controls and gain none.

## What Changes

- **BREAKING** The item list drops its `note` column, its `Spalten` menu
  with the column hiding it drives, and its `Ansicht` menu with the row
  height and heat switch. Both views show every column. The consumption
  heat is always shown, and its legend moves into the hint line below the
  table.
- **BREAKING** The vessel list drops its `note`, `article` and `opened`
  columns, and its `Herkunft` shows only the task that made the batch or
  the supplier. Notes and the opening date show in its details pane.
- **BREAKING** The item list's bulk cell shows the bulk's amount alone;
  the number of containers it would fill moves to the details pane, and
  the column sorts as an amount.
- **BREAKING** The delivery list drops its `contents` column; the details
  pane shows a note's lines.
- **BREAKING** Projected means and coverage are no longer marked, on the
  item list, its details or the item page. They are still computed as
  before.
- All ten main tables share one row height, today's compact one, and one
  rule for bold text: the column naming the record and one column the
  design names per list. Column widths are set so that each table fits
  a window 1650 px wide with the sidebar open; long names are cut with
  an ellipsis and shown whole in a tooltip.
- The sidebar sits at the window's left edge on every page, the site's
  and the lab's alike, and the main lists' pages use the full width to
  the right of it. The task and substance lists' filter bars use the
  inline controls of the other lists.
- The script's `view-menu` and `remember` controllers, and every rule,
  string and test only the removed controls used, are removed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: "Item list" loses its base and table-only
  column groups, column hiding, the `note` column and the projected mark,
  and its bulk cell shows the amount alone; "Consumption" loses the
  projected mark; "Vessel list" loses three columns and shortens its
  source; "Filling from bulk" no longer prescribes where the bulk shows;
  "Delivery list" loses its lines column.
- `web-app`: "Main lists" drops the removed columns' keys and the item
  list's own bulk order.
- `site-theme`: "Measure and tables" no longer fixes the shell's width.

## Impact

- The views and list templates of all ten main lists
  (`inventory/views/{items,bulk,notes,categories,batches,vessels}.py`,
  `planning/views.py`, `tasks/views.py`, `registry/views.py`), and
  `item_page.html`.
- `webapp/orgsyndb_web/static/lab.css`, `lab.js`; `site/assets/css/screen.css`.
- German catalogues: dead strings go; the new hint line and the two
  search placeholders are translated.
- `README.md`, which describes the removed controls and the projected
  mark.
- Tests of the item table, the script, the vessel list, the consumption
  figures and the shell.
- Not affected: the sorting and selection contract, the details panes'
  content, the stacked split layout (next change).
