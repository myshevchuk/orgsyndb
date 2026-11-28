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
- **BREAKING** The vessel list drops its `note` column. Notes show in the
  details panes, which already hold them.
- **BREAKING** Projected means and coverage are no longer marked, on the
  item list, its details or the item page. They are still computed as
  before.
- All ten main tables share one row height, today's compact one, and one
  rule for bold text: the column naming the record and one column the
  design names per list. Column widths are set so that each table fits
  a 1920×1080 window with the sidebar open; long names are cut with an
  ellipsis and shown whole in a tooltip.
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
  column groups, column hiding, the `note` column and the projected mark;
  "Consumption" loses the projected mark; "Vessel list" loses its `note`
  column.
- `web-app`: "Main lists" drops `note` from the item and vessel lists'
  column keys.
- `site-theme`: "Measure and tables" no longer fixes the shell's width.

## Impact

- `webapp/inventory/views/items.py`, `vessels.py`; item, vessel, planning,
  task and substance list templates; `item_page.html`.
- `webapp/orgsyndb_web/static/lab.css`, `lab.js`; `site/assets/css/screen.css`.
- German catalogue: dead strings go.
- Tests of the item table, the script, the vessel list, the consumption
  figures and the shell.
- Not affected: the sorting and selection contract, the details panes'
  content, the stacked split layout (next change).
