## Why

Every main list pairs its table with a details pane, but the layout is
hard-wired: one `c-split-layout` puts the pane beside the table (or, on
the intermediate and commercial chemical lists, below it), and one
`split-list` controller binds rows to the pane through fixed identifiers
(`#item-rows`, `#item-detail`, `#filter-selected`). The panes are loose
headings and lists, and nothing can be nested: the category lists'
panes list a substance's vessels but cannot select one.

The owner decided on 2026-11-28 to treat splits like a tiling window
manager's: a split element, stacked (rows) or side by side (columns),
sized by the golden ratio, nestable, with selection bound per level;
panes organised in widgets; the delivery list side by side with the
pane larger; and the category lists' panes split again into a lot table
and the selected lot's details.

## What Changes

- A cotton split element, stacked or side by side, gives the larger
  golden-ratio share to one side, scrolls each widget on its own, nests,
  and stacks side-by-side splits in a narrow window. Each list offers a
  toggle that gives the larger share to the table or to the pane,
  remembered per list in a cookie.
- A Stimulus `master-detail` controller replaces `split-list`: it binds
  one table's rows to one pane and owns one address parameter
  (`selected`, `lot`), through values instead of fixed identifiers, so
  levels nest. The `Tabelle`/`Details` switch stays, as a zoom of the
  outer split.
- Every details pane shows its data in widgets, in a grid that follows
  its content; secondary actions move into an `Aktionen` menu in the
  pane's header.
- Lists stack their split, the table larger by default; the delivery
  list sits side by side with the pane larger.
- **BREAKING** The intermediate and commercial chemical lists' details
  hold a lot table and the selected lot's details: `lot=<vessel id>`,
  a lot details endpoint per category, and the vessel's note,
  movements and actions moved from the vessel rows into the lot's
  details. The single-vessel movements block goes.
- `c-split-layout`, `split-list` and their CSS go.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-app`: "Main lists" drops "beside", states that details show their
  data in widgets, and gives lot tables the main-table look; "Widgets"
  sorts lot tables in the browser; "Live lists" lets a nested level's
  endpoint answer with its own pane and parameter.
- `end-product-inventory`: "Lists by substance" gains the lot table, the
  lot selection and its endpoint; "Live inventory lists" adds `lot` to
  the category lists' addresses; "Bulk list" drops "beside".

## Impact

- `webapp/orgsyndb_web/templates/cotton/`: new split, pane-head and
  widget-grid components; `split_layout.html` goes.
- `lab.js` (`master-detail`, split toggle; `split-list` goes),
  `lab.css` (split and pane rules; the `item-layout` and `split-detail`
  families go).
- The ten list templates and their details partials;
  `inventory/views/categories.py` and `inventory/urls.py` for the lot
  endpoints; `orgsyndb_web/lists.py` for the split cookie.
- Tests of the lists, panes, script and styles; `README.md`.
- Not affected: sorting, filtering, the record pages, the planning
  parameters widget.
