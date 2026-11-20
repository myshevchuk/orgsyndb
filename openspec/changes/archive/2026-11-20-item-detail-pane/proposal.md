## Why

The item list is the lab's main working table, and it is used in two
ways: scanning and comparing many rows, and working through items one
at a time. For the second, the list offers two popups per row, `Ort`
for the location and bulk and `Abgegeben` for the consumption
statistics, each covering the table and showing one aspect of one
item. The owner decided on 2026-11-18 to replace them with a reading
pane: a switch among the view controls narrows the table to a few
columns and shows the chosen item's details beside it, loaded in place
with htmx when another row is chosen.

The requirement "Item list" also fixes far more than the list's
behaviour: column labels and units, the popups' headings, the view
controls and how they work, the per-column sort rules with their
`sort` and `dir` parameters, the order line, the sticky header and the
placement of popups. The owner decided on 2026-11-15 that specs fix no
layout, and on 2026-11-18 that the item list keeps only what is rooted
deeper than its look: its filter parameters, its default order, the
figures it shows, what a signed-in user can do, and one statement for
the details. Sorting by any column stays in the code, unspecified,
until all tables become sortable.

## What Changes

- end-product-inventory "Item list" is rewritten to its rooted layer:
  - the list, its heading and count, and the redirect from
    `/lab/inventory/`;
  - the figures its table offers, with the article number, the name and
    the quantity as columns no user can hide;
  - the default order, by category, then article number, then
    container;
  - the filter parameters `q`, `category`, `container`,
    `compartment`, `box` and `stock`, and the levels offered with
    their counts;
  - the details of one item, shown with the list and named by
    `detail=<id>` among the items listed, the first item listed's
    without it; while they show, a plain click in a row, on its links
    too, or an arrow key chooses an item instead of following a link;
    its details load in place, and the row's mark and the address
    follow them once they have arrived;
  - the signed-in user's link `Neuer Artikel` and the check boxes for
    a delivery note from the selection;
  - every row of the table on paper, without the details.

  It drops the column labels and units, the location and statistics
  popups, the `sort` and `dir` parameters with their per-column
  rules, the order line, the `category-start` mark, the view controls
  and their mechanics, the note below the table, the sticky box and
  the placement of popups, with their scenarios.
- end-product-inventory "Items": containers compare by amount, units
  of mass before units of amount of substance, then by size; the list's
  default order refers to it.
- end-product-inventory "Consumption heat": the sentence on the item
  list's check box `Verbrauch einfärben` goes with the view controls.
- Code: the item list loses its `Lagerort` column and both popups;
  `Fach` and `Box` show by default; a switch `Details` among the view
  controls, remembered like them and turned on by `detail` in the
  address, narrows the table to `Artikelnr.`, `Name`, `Gebinde`,
  `Bestand` and `Reichweite` and shows the pane. Choosing a row, by
  click or with ↑ and ↓, loads its details from
  `/lab/inventory/items/<id>/detail/` with htmx; once they are in
  place, the row is marked and `detail` set in the address. The pane
  holds the item's head, stock, actions, location and lots,
  consumption and note.
- Build: the declared Django range starts at 6.0, whose template
  partials render the pane; the lockfile already holds 6.0.10.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `end-product-inventory`: "Item list" is rewritten to its rooted
  layer and gains the details; "Items" states how containers compare;
  "Consumption heat" drops the item list's check box.

## Impact

- `webapp/inventory/views.py` (the list's context, the detail view),
  `webapp/inventory/urls.py`,
  `webapp/inventory/templates/inventory/item_list.html` (the pane as a
  template partial), the popup templates `location_popup.html`,
  `statistics_popup.html` and `popup_head.html` (removed),
  `webapp/orgsyndb_web/static/lab.css`,
  `webapp/orgsyndb_web/static/lab.js`, and the German catalogue of
  `inventory`.
- Tests: `webapp/tests/test_inventory_table.py`,
  `test_inventory_lists.py`, `test_inventory_locations.py`,
  `test_inventory_statistics.py` and `test_lab_script.py`.
- `README.md`, whose section on the item list describes the popups,
  the `Lagerort` column and the columns hidden at first.
- `webapp/pyproject.toml` and `webapp/uv.lock`: Django from 6.0.
  No new dependency.
