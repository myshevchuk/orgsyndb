## 1. Tests (red-first)

- [ ] 1.1 Split element and cookie (`test_lists_support.py`,
  `test_main_lists.py`): `split_major` reads `<list>-split`, `first` or
  `second`, else the list's default; every main list renders one outer
  `div.split` holding its table in the first pane and `#item-detail` in
  the second, `split--rows` with `data-major="first"` by default, the
  delivery list `split--columns` with `data-major="second"`; the cookie
  flips `data-major`; the page has the toggle in the details view; no
  `item-layout` and no `c-split-layout` output remain.
- [ ] 1.2 Selection controller (`test_stimulus_controllers.py`,
  `test_lab_script.py`): `lab.js` registers `master-detail` and `split`,
  not `split-list`; on a nested fixture the outer controller ignores lot
  rows and the lot controller ignores outer rows; a lot click writes
  `lot` into the field and the address and keeps `selected`; an outer
  selection drops `lot`; arrow keys move within the focused table; the
  split toggle swaps `data-major` and writes the cookie.
- [ ] 1.3 Widgets in panes (`test_main_lists.py` and the details tests:
  `test_inventory_detail.py`, `test_inventory_batch_details.py`,
  `test_inventory_vessel_details.py`, `test_task_details.py`,
  `test_registry_details.py`, `test_planning_inspector.py`, and the bulk
  and delivery panes in `test_inventory_bulk.py` and
  `test_inventory_lists.py`): every `#item-detail` with a record holds a
  pane head with an `h2` and the record's page link, and its data in
  `.widget` elements with `h3` headings; existing content assertions keep
  passing against the widgets.
- [ ] 1.4 Category lots (`end-product-inventory` "Lists by substance",
  "Live inventory lists"; `test_inventory_categories.py`,
  `test_inventory_live_lists.py`, `test_inventory_dialogs.py`): the
  scenarios "Containers of the selected substance", "Booking in a
  dialog", "One bottle with its movements", "Selecting a lot", "A lot of
  another substance"; the lot table's columns and `main-table` class;
  `#lot-rows`/`#lot-detail` with `data-refresh`; the address and
  `HX-Push-Url` naming `lot` only off the first lot; no single-vessel
  movements block.
- [ ] 1.5 Main lists (`test_main_lists.py`): the "Two table classes"
  sweep accepts lot tables as main tables.
- [ ] 1.6 Styles (`test_widgets_print.py`, `test_inventory_table.py`):
  `lab.css` names no `.item-layout`, `.split-detail-`,
  `.split-vessel-`, `.split-movements-`, `.detail-figures`,
  `.detail-location` or `.detail-lots`; the split's two tracks use
  `1.618fr` and `1fr`; panes stay off paper.

## 2. Server

- [ ] 2.1 `orgsyndb_web/lists.py`: `split_major`.
- [ ] 2.2 Each list view passes its split's `major` from its cookie.
- [ ] 2.3 Category lots: routes, the lot details view, the substance
  pane's lot selection, `lot` in the canonical address.

## 3. Layout and selection

- [ ] 3.1 `c-split`, `c-pane-head`, `c-widget-grid` (and an `h3` heading
  option on `c-widget`); remove `c-split-layout`.
- [ ] 3.2 `lab.js`: `master-detail` and `split` controllers; remove
  `split-list`.
- [ ] 3.3 `lab.css`: split, pane head, widget grid, per-widget scroll,
  narrow-window rules; remove the old families.

## 4. Panes

- [ ] 4.1 Move the ten list templates onto `c-split` with
  `master-detail`.
- [ ] 4.2 Rebuild each details pane as a pane head and widgets (design
  decision 3); the category pane as a nested split with the lot table
  and the lot's details.
- [ ] 4.3 German catalogues: new strings, dead strings removed, compiled.

## 5. Documents

- [ ] 5.1 `README.md` (via `codex-docs`): the split toggle, the panes in
  widgets, the delivery list's layout, and the category lots.

## 6. Verification

- [ ] 6.1 Area tests serially: every file section 1 names.
- [ ] 6.2 On the local demo database, screenshot each list in the
  details view at 1650×1050 and 1920×1080, both ratios, and the category
  lists with a second lot selected; check keyboard selection on both
  levels by hand.
