## 1. Tests

- [ ] 1.1 Column model: base columns first in the stated order, then
  the table view's; every table-view cell carries `table-only`; the
  `Spalten` menu offers the table-view columns alone; the page's
  hiding rules name each table-view column and no base column; the
  note hidden at first
- [ ] 1.2 Views: no cookie, `item-list-view` `details`, `table` and an
  unknown value check the matching radio; the switch outside any form;
  no `#detail-switch`; no link or form names a view
- [ ] 1.3 Selection: `selected` names the marked row and the pane in
  both views; the first row without it, with an unknown id and with an
  id the filters leave out; none for an empty list; `detail` no longer
  read
- [ ] 1.4 Selection kept: the filter form's hidden field, the stock
  levels' links, the headers' links and the reset link carry the id of
  the row the server selected, named by `selected` or standing in as
  the first; a stale `selected` is not carried; an empty list carries
  none
- [ ] 1.5 Details' URL: a request without htmx redirects to the list
  with `selected`; the scenarios "Details of an item", "Links in the
  details" and "Another item in place" with `selected`; every test
  that requests the list with `detail`, the consumption widget's in
  `test_inventory_consumption_widget.py` among them, moved to
  `selected` and to an item other than the first
- [ ] 1.6 Stylesheet: `.table-only` hidden in the details view, on
  screen alone, by `[data-view="details"]` once scripted and by
  `#view-details:checked` otherwise; `.item-table` without
  `width: 100%`; the marked row styled in both views; no per-key
  hiding rule left in `lab.css`; the generated rules in the page's
  head; the view-transition names and the unscaled snapshots under
  `prefers-reduced-motion: no-preference` alone
- [ ] 1.7 `OrgSynLab.paramSearch` under Node: a parameter set,
  replaced and removed, repeated ones joined, others kept;
  `detailSearch` gone
- [ ] 1.8 Dialogs: the scenario "Signed out meanwhile" with
  `selected=3`; the refresh's parts unchanged; `.item-layout` carries
  `data-view` from the cookie

## 2. Implementation

- [ ] 2.1 `views.py`: the column model replacing `column_labels`,
  `SORT_VALUES`, `NUMERIC`, `FIXED_COLUMNS` and `HIDDEN_COLUMNS`; the
  view from the cookie; `selected` in `chosen_row`, in the filters'
  links and in the context; the details' redirect
- [ ] 2.2 `item_list.html`: header and cells from the model through
  the partial `cell`; the generated hiding rules; the two-part switch;
  the hidden field `selected`; the `Spalten` menu from the model
- [ ] 2.3 `lab.css`: natural width, the note taking the rest, the
  details grid, `.table-only` hidden in the details view, the marked
  row in both views, the switch, the view-transition names
- [ ] 2.4 `lab.js`: `paramSearch`; selection in both views, links
  followed; `follow(id)` after a row's swap and after a dialog's
  refresh, in either view; the cookie and `data-view`, `data-scripted`;
  the disabled `Spalten` button; the animated switch with native radio
  activation and its fallbacks; the header comment
- [ ] 2.5 The German catalogue of `inventory`: new strings, obsolete
  ones removed, compiled

## 3. Documentation

- [ ] 3.1 `README.md`: the item list's section with the two views, the
  base columns, selection in both views and `selected` (Codex doc
  writer)

## 4. Verification

- [ ] 4.1 Both suites pass
- [ ] 4.2 On the test server, in a real browser:
  - by script, the five base columns' widths and left edges relative
    to the table are equal in both views, with the note shown and
    hidden, with a long name, on both sides of 55rem, and with the box
    scrolled sideways;
  - the switch animates with the base columns standing still, neither
    moved nor scaled, and switches at once with reduced motion; the
    switch itself with click, Space, ←/→ and Tab, and clicked twice
    on the shown view, keeps focus and checked state as native radios
    do and switches once per change;
  - a click outside the links and ↑ and ↓ select in both views, a
    link follows; holding ↓ in the table view;
  - a reload, a filter, a reorder and a reset keep the selection; the
    cookie survives a new tab;
  - a save in a dialog keeps the selection, and a save that moves the
    selected item out of the stock filter selects the first row,
    after which a header link and the filter form carry that row;
  - the console shows no error

## 5. Review and archive

- [ ] 5.1 Codex reviewer
- [ ] 5.2 Archive and squash-merge into `develop`
