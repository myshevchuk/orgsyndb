## 1. Tests

- [ ] 1.1 List: widget, count, seven columns in both languages, `data-article`,
  the `Artikel` link with `selected` (and `all=1`), sort keys, tasks
  and actions in the list.
- [ ] 1.2 Inspector: blocks per row, selection by `selected` and its
  fallback, `aria-current`, `Gebinde & Bedarf` rows, `Planungsdetails`
  rows including the tasks' expected end.
- [ ] 1.3 Filters: buttons present, `hidden`, `aria-pressed`, rows'
  `data-priority`, `data-action` and `data-late`.
- [ ] 1.4 Parameters widget closed with every parameter.
- [ ] 1.5 Rewrite the existing planning-list tests that read the old
  columns, the parameters line or the parallel lists.

## 2. Templates and view

- [ ] 2.1 `views.py`: pass `selected`.
- [ ] 2.2 `list.html` and inspector partials; `parameters.html` as a
  collapsible widget.
- [ ] 2.3 German catalogue for the new strings, `.mo` compiled.

## 3. Script and styles

- [ ] 3.1 `lab.js`: selection by click and arrow keys, address, filters.
- [ ] 3.2 `lab.css`: list beside the inspector on wide screens, stacked
  below; print shows list, selected inspector and parameters.

## 4. Verification

- [ ] 4.1 Browser on the demo at 1440, 1000 and 500 px, light and
  dark: no horizontal scrolling at 1440, filters, selection by click
  and keys, address, print preview.
- [ ] 4.2 Owner checks `/lab/planning/` on the test server.
