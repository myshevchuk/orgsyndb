## Why

The item list has a table view and, since `item-detail-pane`, a
details view with a reading pane. Switching between them is abrupt:
the table stretches to the width it is given, so every column the two
views share changes its width, and the columns the details view drops
sit between the shared ones, so these move sideways too. Only the
details view lets a user select a row, so the table view offers no
row to carry over, and in the details view a click on a link selects
instead of following it. The checkbox `Details` reads as an option of
the table rather than as a choice between two views.

The owner decided on 2026-11-21 that the shared columns are one table
that both views show identically, with the table view adding its own
columns after them; that selection works the same in both views; that
the address names the selection and a browser cookie the view; and
that the switch animates with the browser's View Transitions API.

## What Changes

- **BREAKING** end-product-inventory "Item list": the list has two
  views, `Tabelle` (`Table`) and `Details`.
  - Base columns: the article number, the name, the category, the
    container and the quantity. Both views show them, first and in
    that order, each as wide in one view as in the other, and no user
    can hide them.
  - The table view adds its own columns after them: the means, the
    current year's consumption, the coverage, the compartment, the
    box, the bulk and the note. A user may hide each of them; the
    coverage leaves the details view, the category joins it.
  - The list opens in the view the browser remembers in the cookie
    `item-list-view`, else in the table view; the address no longer
    names the view.
  - `selected=<id>` replaces `detail=<id>` and names the selected
    item in both views; without it the first item listed is selected.
    The selected row is marked in both views.
  - In both views a plain click in a row, outside its links and its
    check box, or an arrow key selects; links always follow their
    targets.
  - Selecting loads the item's details in place in both views, so a
    switch to the details view shows them at once.
  - Filtering and reordering the list keep the selected item while the
    list still holds it.
  - The redirect of the details' URL names the item in `selected`.
- **BREAKING** web-app "Form dialogs": the refresh keeps the selected
  item; the scenario's address uses `selected`.
- Code:
  - one column model in `views.py`, holding each column's key, label,
    unit, alignment, sort value, view group and default visibility;
    the template renders headers and cells by iterating it, and the
    rules that hide columns come from it;
  - a two-part switch replaces the checkbox `Details`;
  - the `Spalten` (`Columns`) menu offers the table view's own columns
    only, and is disabled in the details view;
  - the table keeps its natural width, the pane takes the rest;
  - `lab.js` animates the switch through `document.startViewTransition`
    where the browser has it and the user has not asked for reduced
    motion.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: "Item list" gains the two views with their
  base columns, the cookie for the view, and selection in both views
  through `selected`.
- `web-app`: "Form dialogs" keeps the selected item, with `selected`
  in its scenario's address.

## Impact

- `webapp/inventory/views.py` (the column model, the list's context,
  the details' redirect),
  `webapp/inventory/templates/inventory/item_list.html`,
  `webapp/orgsyndb_web/static/lab.css`,
  `webapp/orgsyndb_web/static/lab.js`, and the German catalogue of
  `inventory`.
- Tests: `webapp/tests/test_inventory_table.py`,
  `test_inventory_detail.py`, `test_inventory_lists.py`,
  `test_inventory_dialogs.py` and `test_lab_script.py`.
- `README.md`, whose section on the item list describes the checkbox
  `Details`, selection in the details view only and `detail=<id>`.
- No new dependency.
