## 1. Tests

- [x] 1.1 Item list, rewritten scenarios: by category first, levels
  with their counts, one level exactly, locations as cells, filters;
  the columns without `Lagerort`, and every cell naming its column
- [x] 1.2 Details of an item, of the first item, of an unknown id, of
  an item the filters leave out, of an empty list; the pane's
  `data-item` and the marked row; links in the details signed in and
  as a visitor; lots, locations and consumption as the popups' tests
  had them
- [x] 1.3 Another item in place: rows carry `data-item`, `hx-get` and
  `hx-trigger`, the body the target, swap and sync; the detail view
  answers htmx with the partial alone, matching the list's pane,
  redirects any other request, sends `Vary: HX-Request`, and answers
  404 for an unknown id
- [x] 1.4 View controls: the switch `Details`, remembered, outside any
  form, checked with `detail`; `Fach` and `Box` shown and `Bemerkung`
  hidden at first; no popup inside the table
- [x] 1.5 Stylesheet: the switch narrows the table to its five columns
  and shows the pane, on screen alone; a pane in a request is dimmed
  and takes no pointer; paper leaves the pane out
- [x] 1.6 `OrgSynLab.detailSearch` under Node: `detail` set, replaced
  and removed, other parameters kept
- [x] 1.7 Remove the tests of the popups and of the `Lagerort` column

## 2. Implementation

- [x] 2.1 `pyproject.toml`: Django from 6.0; `uv lock`
- [x] 2.2 `views.py`: the detail row of the list, its query for the
  switch, the view `item_detail`, and the `Lagerort` column and
  hidden columns as decided; `urls.py`: the detail's URL
- [x] 2.3 `item_list.html`: the pane as the partial `detail`, the
  switch, the rows' and body's htmx attributes, the note below the
  table; the three popup templates removed
- [x] 2.4 `lab.css`: the pane, the narrowed table and the chosen row,
  on screen; the popups' rules gone or turned into the pane's; paper
  without the pane
- [x] 2.5 `lab.js`: `detailSearch`, the switch's address, choosing a
  row by click and by ↑ and ↓, the mark and the address moved after
  the swap; its header comment
- [x] 2.6 The German catalogue of `inventory`: new strings, obsolete
  ones removed, compiled

## 3. Documentation

- [x] 3.1 `README.md`: the item list's section without the popups and
  the `Lagerort` column, with the switch and the pane (Codex doc
  writer)

## 4. Verification

- [x] 4.1 Both suites pass
- [x] 4.2 On the test server, with `category` in force: the switch,
  a click and ↑ and ↓ show items in the pane; a reload keeps both
  `category` and `detail`; with the network throttled the pane dims
  and the mark moves only when the details arrive; offline, a choice
  leaves pane, mark and address as they were; the console shows no
  error

## 5. Review and archive

- [x] 5.1 Codex reviewer
- [ ] 5.2 Archive and squash-merge into `develop`
