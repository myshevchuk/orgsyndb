## 1. Tests

- [x] 1.1 List: widget, count, seven columns in both languages, `data-article`,
  the `Artikel` link with `selected` (and `all=1`), sort keys, tasks
  and actions in the list.
- [x] 1.2 Inspector: blocks per row, selection by `selected` and its
  fallback, `aria-current`, `Gebinde & Bedarf` rows, `Planungsdetails`
  rows including the tasks' expected end.
- [x] 1.3 Filters: the button group present and `hidden`, the buttons'
  `aria-pressed`, the rows' `data-priority`, `data-action` and
  `data-late`; Node tests of the pure helpers for which rows a filter
  shows and which row an arrow key moves to (`test_lab_script.py`).
- [x] 1.6 `test_widgets_print.py`: the planning layout's grid only
  under `@media screen`, and the retired `.lab-parameters` and
  `.planning-cell` rules gone.
- [x] 1.4 Parameters widget closed with every parameter.
- [x] 1.5 Rewrite the existing tests that read the old columns, the
  parameters line or the parallel lists: `test_planning_list.py`
  (including `TasksColumnTests`, whose expected end moves to the
  inspector), `planning_support.py` (`rows_by_article` keyed on
  `data-article`), `test_planning_stock.py`, `test_planning_matching.py`,
  `test_demo_days.py` and `test_demo_records.py` (the synthesis-time
  basis moves to the inspector). Scope inspector reads to the selected
  block or to a block by `data-article`.

## 2. Templates and view

- [x] 2.1 `views.py`: resolve the selected article number (the matching
  row's, else the first row's, else none) and pass it.
- [x] 2.2 `list.html` and inspector partials; `parameters.html` as a
  collapsible widget.
- [x] 2.3 German catalogue for the new strings, `.mo` compiled.

## 3. Script and styles

- [x] 3.1 `lab.js`: selection by click and arrow keys over the rows that
  show, address, filters, the no-match note and the shown count; pure
  helpers on `OrgSynLab`.
- [x] 3.2 `lab.css`: list beside the inspector on wide screens, stacked
  below; print shows list, selected inspector and parameters.

## 4. Verification

- [x] 4.1 Browser on the demo at 1440, 1000 and 500 px, light and
  dark: no horizontal scrolling at 1440, filters, selection by click
  and keys, address, print preview.
- [ ] 4.2 Owner checks `/lab/planning/` on the test server.
