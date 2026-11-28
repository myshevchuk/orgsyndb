## 1. Tests (red-first)

- [ ] 1.1 Item list (`end-product-inventory` "Item list"): in
  `test_inventory_table.py` and `test_inventory_lists.py`, both views
  show every column in the stated order and no `note` column; no cell or
  header carries `table-only`; the page has no `#columns-menu`, no
  `Spalten` button, no inline column-hiding `<style>`, no
  `details.lab-view-menu`, no `#row-height` and no `#heat-switch`; heat
  classes are on the mean and current-year cells; `.lab-table-note`
  holds the heat scale's five swatches. Remove the tests of the removed
  scenarios "Base columns first" and "Columns a user may hide".
- [ ] 1.2 Projected mark (`end-product-inventory` "Consumption"): no
  element carries `projected` and no page holds `hochgerechnet aus dem
  laufenden Jahr`, on the item list, its details and the item page, for
  an item with projected means (`test_inventory_consumption.py`,
  `test_inventory_detail.py`, `test_widgets_item_page.py`,
  `test_inventory_states.py`, `test_demo_records.py`); the figures keep
  their projected values.
- [ ] 1.3 Vessel list (`end-product-inventory` "Vessel list", `web-app`
  "Main lists"): no `Bemerkung` column and no `sort=note`
  (`test_inventory_vessels.py`, `test_main_lists.py` through
  `main_lists_support.py`'s table of lists); the vessel details still
  show the note.
- [ ] 1.4 Script (`test_lab_script.py`, `test_stimulus_controllers.py`):
  `lab.js` registers neither `view-menu` nor `remember`; the source names
  no `lab-view-menu`, `columns-menu` or `data-remember`.
- [ ] 1.5 Styles (`test_widgets_print.py`, `test_inventory_table.py`):
  `lab.css` names no `#row-height`, `#heat-switch`, `.lab-view-menu`,
  `.lab-view-controls`, `.heat-legend`, `.table-only`, `.lab-columns`,
  `#columns-menu`, `.projected`, `.col-note` or `.col-fill`; one rule
  makes `.main-table .col-strong` bold; `screen.css`'s `body` is not
  centred.
- [ ] 1.6 Main tables (`test_main_lists.py`): on every list the headers
  and cells of the two columns design decision 5 names carry
  `col-strong`, and no other column does; planning's `Artikel` cell holds
  the article number and the name with no line break between them; the
  task and substance lists' filter controls are inline.

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

## 3. Main-table look and shell

- [ ] 3.1 Mark the bold columns of the other eight lists (views or
  templates); planning's `Artikel` on one line.
- [ ] 3.2 `lab.css`: one row height; `.col-strong`; name-column caps with
  ellipsis and `title`; remove the dead rules of design decision 3 and 5.
- [ ] 3.3 Shell: `screen.css` `body` left-aligned; `lab.css`
  `body.lab-frame` without the width cap.
- [ ] 3.4 Task and substance lists: inline filter controls.
- [ ] 3.5 `lab.js`: drop `RememberController`, `ViewMenuController`, the
  view-menu closing in `PopoverAnchorController`, and the columns button
  in `SplitListController`.
- [ ] 3.6 German catalogue: remove the dead strings and compile.

## 4. Documents

- [ ] 4.1 Check user documents for the removed controls and the
  projected mark.

## 5. Verification

- [ ] 5.1 Run the area tests serially: the files of section 1,
  `test_inventory_*.py` touched, `test_live_tasks_registry.py`,
  `test_planning_list.py`, `test_lab_script.py`,
  `test_stimulus_controllers.py`.
- [ ] 5.2 On the local demo database, screenshot each of the ten lists in
  the table view at 1920×1080 with the sidebar open: no table scrolls
  sideways; the sidebar sits at the left edge on a lab page and a site
  page.
