# Design: Uniform main tables

## Context

After `unified-list-tables` the ten main lists share `table.main-table`,
server sorting and one selection mechanism. Screenshots of the demo data
set at 1920×1080 (2026-11-28) show:

- `body` is `max-width: 96rem` and centred (`base.css` `margin: 0 auto`,
  `screen.css` grid `17rem minmax(0, 1fr)`), so `main` is about 1,150 px
  wide and about 450 px of the window stay empty;
- the item list overflows it (`Reichweite`, `Fach`, `Box`, `Bulk` cut),
  the vessel list overflows (`Ort` cut, `Bemerkung` off screen), and the
  task list's `Status` cell with two badges overflows;
- names such as `9,10-Dihydro-9,10-ethanoanthracen-11,12-dicarbonsäureanhydrid`
  set the width of the name columns of the item, substance and planning
  lists;
- the task and substance lists render their filter controls stacked
  (`:inline="False"`), and their search field as a tall empty box;
- planning's `Artikel` cell is two lines high (name over number).

The item list carries controls no other list has: the `Spalten` menu
(`#columns-menu`, one `remember`ed check box per table-only column and an
inline `<style>` that hides unchecked columns), the `Ansicht` menu
(`details.lab-view-menu`: `#row-height` compact or tight, `#heat-switch`
with the heat scale), the `table-only` class that the details view hides,
and `SplitListController`'s disabling of the `Spalten` button in the
details view. `RememberController` and `ViewMenuController` serve only
these controls. `.projected` (italic, with the title `hochgerechnet aus
dem laufenden Jahr`) marks projected means and coverage in the item list,
its details pane and the item page's figure tiles.

## Goals / Non-Goals

Goals: one look, one row height and all columns for every main table;
every main table fits a window 1650 px wide with the sidebar open, a
compromise the owner chose on 2026-11-28 between older and newer
monitors; no control or mark without a stated purpose.

Non-goals:

- the stacked split and widget panes (next change);
- a requirement on widths or row heights (owner: interface decisions);
- changing what any column holds or how it sorts, beyond the removals and
  shortenings of decision 1 and the owner's amendment.

## Decisions

### 1. Specs only lose text

The owner asked that specs governing these controls be removed, not
corrected or extended. The deltas delete:

- "Item list": the split into base and table-only columns, "of which a
  user may hide each", "a base column is as wide in one view as in the
  other", the projected mark, the `note` column, and the scenarios "Base
  columns first" and "Columns a user may hide". The column list stays,
  as one list, because it states what the list shows;
- "Consumption": the projected mark and "each marked as projected";
- "Vessel list": the `Bemerkung` column;
- "Main lists": `note` among the item and vessel lists' keys;
- "Measure and tables": "with a shell up to 96rem wide".

The owner's amendment of 2026-11-28 adds, all as deletions or
shortenings:

- "Item list": the bulk cell shows the bulk by unit; the details gain
  the number of containers it would fill, which the cell gave before;
- "Filling from bulk": "wherever an item shows its bulk, it shows that
  amount by unit and the number of its containers" goes; the number's
  definition stays;
- "Vessel list": `Artikelnr.` and `Angebrochen` go (the opening date
  stays in the details pane), and `Herkunft` shows only the task or the
  supplier;
- "Delivery list": the lines in the table go; the details keep them;
- "Main lists": the keys `contents` (delivery), `article` and `opened`
  (vessel), and the item list's own `bulk` order go. Its two scenarios
  that sorted the vessel list by `opened` move to the commercial chemical
  list's `opened`.

No width, height, weight or position becomes a requirement. Fitting a
window 1650 px wide is a design goal, checked by screenshot (tasks 5.2).

Rejected: a width test in the suite. The owner called fitting a design
goal, and a test would pin column widths that the next change revisits.

### 2. The shell

The Navigation requirement (site-theme) keeps the site title, search,
navigation and the start of `main` in the same place on every page, the
site's and the lab's alike. So the sidebar moves to the window's left
edge everywhere: `body` loses its centring (`margin-left: 0`) in
`screen.css`, which both the site and the lab load. Pages other than the
main lists keep the 96rem cap, now left-aligned. `body.lab-frame`, the
main lists' pages, drops the cap, so `main` runs to the window's right
edge.

Rejected: moving only the lab's sidebar. It breaks the Navigation
requirement's "the same position on every page".

### 3. The item list's columns and controls

- `ColumnSpec` loses `group` and `shown`, and `Column` loses `table_only`
  and `shown`; the `table-only` class and the `table_columns` context go.
- The `note` column goes from `COLUMN_MODEL` and the cell partial. `q`
  still searches the note (Item list's filters are unchanged).
- The `Spalten` menu, its inline `<style>`, the `Ansicht` menu, and
  `SplitListController`'s columns-button handling go.
- `RememberController` and `ViewMenuController` go, with the `storage`
  helper only `RememberController` reads, `PopoverAnchorController`'s
  closing of `details.lab-view-menu`, the file's controller list entries
  for both, and
  every CSS rule that names `#row-height`, `#heat-switch`,
  `.lab-view-menu`, `.lab-view-controls`, `.heat-legend`, `.table-only`,
  `.lab-columns` or `#columns-menu`.
- The heat scale (`wenig`, five swatches, `viel`) moves into
  `.lab-table-note`, after the stock legend. Its hint says the details
  view shows the chosen item's details; it stops listing columns the
  details view no longer hides. The item list's `View` string (context
  `item list`) stays: the view switch uses it.
- Values users stored under `orgsyndb:item-list:*` in `localStorage` are
  left alone; nothing reads them again.

### 4. No projected mark

`.projected`, its title and the string go from the item list, its pane
and `item_page.html`. `figures.projected` stays in the model: it still
decides how means are computed.

### 5. One main-table look

- Row height: the compact one, `1.875rem` at `0.8125rem`, for all ten
  lists; no list overrides it. A cell of one value stays on one line;
  cells that list several values (planning tasks and actions) may
  grow. Planning's `Artikel` cell puts the article number
  before the name on one line, as the bulk list does, without the
  `kv-sub` block. The intermediate and chemical lists' rule
  `.category-table td:first-child { white-space: normal; min-width:
  14rem }` goes.
- Bold: the column naming the record, plus one column per list:

  | List | Record column | Second column |
  |---|---|---|
  | item | `name` | `container` |
  | bulk | `article` | `amount` |
  | delivery | `number` | `recipient` |
  | intermediate | `substance` | `amount` |
  | chemical | `substance` | `amount` |
  | batch | `name` | `stock` |
  | vessel | `name` | `amount` |
  | planning | `article` | `start` |
  | task | `product` | `priority` |
  | substance | `name` | `article` |

  Bold comes from one rule on a class (`col-strong`) set on those
  columns' header and cells. Headers are already semi-bold, so the rule
  changes the look of cells (`.main-table td.col-strong`, links in them
  included). It replaces the per-list rules such as
  `.category-table td:first-child a` and `.bulk-table td:first-child a`;
  `.cat-amount` stays, as the category panes' tables use it.
- Widths: name columns are capped on screen (`max-width` with
  `overflow: hidden` and `text-overflow: ellipsis`, inside `@media
  screen`, so paper keeps whole names); the templates give each capped
  cell the whole name in `title`. In the table view every main table
  fills the width of its box (owner, 2026-11-28): 1650 px is the
  narrowest window at which no table scrolls sideways, and wider windows
  stretch the tables; narrower windows may scroll. The details view keeps
  its grid sizing until the next change. On paper every cell but a
  number's may wrap (print-layout "Wide tables"). The ui-specialist sets the cap so that each list fits. The
  vessel list's names are not capped (owner); `Ort` is not capped
  either, as German place names run long. Whether the caps suffice is
  unverified until the screenshots of tasks 5.2. Measured on
  2026-11-28 at 1920 px, the item list was ~1,460 px wide and the vessel
  list ~1,380 px against ~1,260 px available at 1650 px; the bulk cell's
  fill counts (~200 px) and the vessel list's three columns and shorter
  source bring both within it.
- Dead rules go: `.col-note`, the unused `.col-fill`, and the print test's
  assertion on it.

### 6. Filter bars

The task and substance lists use the inline filter controls
(`c-filter-select` and `c-filter-search` without `:inline="False"`), as
the inventory and planning lists do. Their labels stay, as the selects'
prefixes and as the search fields' visually hidden text. An inline search
field shows no label, so each gets a placeholder naming what it searches:
`Nr., Substanz, Charge oder Notiz` (`Number, substance, batch or note`)
on the task list and `Name, Kurzname, Schlüssel oder CAS` (`Name, short
name, key or CAS`) on the substance list.

## Risks / Trade-offs

- **Details view until the next change.** With all columns shown, the
  item list's side-by-side details view squeezes a wide table beside the
  pane; the table scrolls. The next change stacks the pane below.
- **Site pages move.** Every site page's shell moves to the left edge on
  wide windows. The Navigation requirement wants this consistency.
- **Cut names.** A name longer than the cap shows an ellipsis; the
  tooltip, the details pane and the record page show it whole.

## Migration Plan

None. Pre-1.0: the controls, classes, strings and the two columns are
removed outright.
