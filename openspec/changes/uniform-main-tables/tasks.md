## 1. Tests (red-first)

- [ ] 1.1 Item list (`end-product-inventory` "Item list"): in
  `test_inventory_table.py` and `test_inventory_lists.py`, both views
  show every column in the stated order and no `note` column; no cell or
  header carries `table-only`; the page has no `#columns-menu`, no
  `Spalten` button, no inline column-hiding `<style>`, no
  `details.lab-view-menu`, no `#row-height` and no `#heat-switch`; heat
  classes are on the mean and current-year cells; `.lab-table-note`
  holds the heat scale's five swatches. Remove the tests of the removed
  scenarios "Base columns first" and "Columns a user may hide", and the
  `#row-height` and `#heat-switch` entries of `KEPT` in
  `test_inventory_dialogs.py`.
- [ ] 1.2 Projected mark (`end-product-inventory` "Consumption"): no
  element carries `projected` and no page holds `hochgerechnet aus dem
  laufenden Jahr`, on the item list (`test_inventory_lists.py`, whose
  assertion of `projected` on the `Ø Jahr` cell flips), its details
  (`test_inventory_detail.py`) and the item page
  (`test_widgets_item_page.py`), for an item with projected means; check
  `test_inventory_states.py` and `test_demo_records.py` for the same.
  `test_inventory_consumption.py` keeps its model-level checks of
  `figures.projected`.
- [ ] 1.3 Vessel list (`end-product-inventory` "Vessel list", `web-app`
  "Main lists"): no `Bemerkung` column and no `sort=note`
  (`test_inventory_lists.py`'s `VESSELS_DE`/`VESSELS_EN` and row checks,
  `main_lists_support.py`'s table of lists); the vessel details still
  show the note (`test_inventory_vessel_details.py`).
- [ ] 1.4 Script (`test_lab_script.py`, `test_stimulus_controllers.py`):
  `lab.js` registers neither `view-menu` nor `remember` and holds no
  `storage` helper; the source names no `lab-view-menu`, `columns-menu`
  or `data-remember`. Drop the positive `view-menu` and `columns-menu`
  assertions, and split `remember` out of
  `test_remember_and_batch_narrow_both_drivers`, keeping its
  `batch-narrow` coverage.
- [ ] 1.5 Styles (`test_widgets_print.py`, `test_inventory_table.py`,
  `test_shell.py`, and `tests/test_theme_static.py` at the repository
  root): `lab.css` names no `#row-height`, `#heat-switch`,
  `.lab-view-menu`, `.lab-view-controls`, `.heat-legend`, `.table-only`,
  `.lab-columns`, `#columns-menu`, `.projected`, `.col-note`, `.col-fill`
  or `.category-table td:first-child`; one rule makes
  `.main-table td.col-strong` bold; the name caps with `text-overflow`
  sit inside `@media screen`; `screen.css`'s `body` is not centred, and
  `body.lab-frame` has no `max-width`.
- [ ] 1.6 Main tables (`test_main_lists.py`): on every list the headers
  and cells of the two columns design decision 5 names carry
  `col-strong`, and no other column does; each capped name cell carries
  `title` with the whole name; planning's `Artikel` cell holds the
  article number before the name and no `.kv-sub`.
- [ ] 1.7 Filter bars (`test_task_list.py`, `test_live_tasks_registry.py`,
  `test_registry_pages.py`): the task and substance lists' controls are
  inline, and their search fields carry the placeholders of design
  decision 6.
- [ ] 1.8 Other lists the bold columns touch: update what
  `test_inventory_bulk.py`, `test_inventory_categories.py`,
  `test_inventory_batches.py` and `test_planning_list.py` assert about
  the cells' markup, where the change alters it.

- [ ] 1.9 Amendment of 2026-11-28 (`end-product-inventory` "Item list",
  "Filling from bulk", "Vessel list", "Delivery list"; `web-app` "Main
  lists"): the item list's bulk cell shows the amount by unit and no
  container count, its details show the count, and `sort=bulk` orders
  by amount; the vessel list has no `Artikelnr.` or `Angebrochen` column
  and its `Herkunft` reads the task number or the supplier without
  `gekauft`/`hergestellt`; the vessel details still show the opening
  date; the delivery list's table has no `contents` column, keeps its
  `lines` count and its reversal marks, and its details show the lines
  with their batches; the two moved "Main lists" scenarios on the
  commercial chemical list. Files:
  - item bulk: `test_inventory_numbers.py` (its fill counts read from
    the item table move to the selected item's details; the item page
    keeps amount and count), `test_inventory_table.py` (a `sort=bulk`
    fixture whose amount order differs from its fill-count order, for
    example two items of different sizes);
  - vessels: `test_inventory_lists.py`, `test_inventory_vessel_forms.py`
    (its `Angebrochen` header and cells move to the vessel details or the
    vessel page), `test_inventory_vessel_details.py`, `test_main_lists.py`
    with `main_lists_support.py`;
  - deliveries: `test_inventory_lists.py`, `test_inventory_stock_pages.py`
    (batch numbers of made, bought, multi-batch and historical lines move
    from the row to the selected note's details).

## 2. Item and vessel lists

- [ ] 2.1 `inventory/views/items.py`: drop `note`, `group`, `shown`,
  `table_only` and `table_columns`; mark the bold columns.
- [ ] 2.2 `item_list.html`: drop the `Spalten` and `Ansicht` menus, the
  inline `<style>` and the note cell; move the heat scale into the hint
  line and update its text.
- [ ] 2.3 `inventory/views/vessels.py` and `vessel_list.html`: drop the
  note column.
- [ ] 2.4 Drop the projected mark from `item_list.html`'s pane and
  `item_page.html`.
- [ ] 2.5 Item list: bulk cell by unit only, sorted as an amount; the
  pane shows the container count.
- [ ] 2.6 Vessel list: drop `article` and `opened`; `Herkunft` with the
  task or the supplier only, in its cell and its sort value, without
  changing the batch and bulk lists' shared source template and helper;
  names uncapped.
- [ ] 2.7 Delivery list: drop the `contents` column.

## 3. Main-table look and shell

- [ ] 3.1 Mark the bold columns of the other eight lists (views or
  templates); planning's `Artikel` on one line.
- [ ] 3.2 `lab.css`: one row height; `.col-strong`; name-column caps with
  ellipsis and `title`; remove the dead rules of design decision 3 and 5.
- [ ] 3.3 Shell: `screen.css` `body` left-aligned; `lab.css`
  `body.lab-frame` without the width cap.
- [ ] 3.4 Task and substance lists: inline filter controls.
- [ ] 3.5 `lab.js`: drop `RememberController`, `ViewMenuController`, the
  `storage` helper, the view-menu closing in `PopoverAnchorController`,
  the columns button in `SplitListController`, and their entries in the
  file's controller list.
- [ ] 3.6 Templates: `title` with the whole name on every capped name
  cell; search placeholders on the task and substance lists.
- [ ] 3.7 German catalogues: remove the dead strings (keeping the item
  list's `View`), translate the new hint line and the placeholders, and
  compile.

## 4. Documents

- [ ] 4.1 `README.md` (via `codex-docs`): the item list's columns, the
  removed `Spalten` and `Ansicht` menus, the stored choices, and the
  projected figures; and, from the amendment, the item list's bulk cell
  and its sort, the delivery list's rows without lines, and the vessel
  list without `Angebrochen`. Check `docs/` for the same.

## 5. Verification

- [ ] 5.1 Run the area tests serially: every file section 1 names, and
  `python3 -m pytest tests/test_theme_static.py -q` at the repository
  root.
- [ ] 5.2 On the local demo database, screenshot each of the ten lists in
  the table view at 1650×1050 with the sidebar open: no table scrolls
  sideways; the sidebar sits at the left edge on a lab page and a site
  page.
