## Why

The Bestand pages spend about 360 px of a 900 px window on chrome
above their tables (the demo notice, a large heading, stacked filter
labels, a caption row), and the whole page scrolls, so the table
headers and filters leave the screen. The owner approved, in the
second screenshot series, a frame that fits the window and lets only
the tables scroll; the views by category to come are built in it.

## What Changes

- The sidebar and the Bestand pages (items, batches, vessels,
  deliveries) fit the window on screens at least 900 px wide: the
  page does not scroll, the table scrolls in its own box under its
  sticky header, and the item list's details pane scrolls in its own.
  Narrower screens and every other page scroll as before.
- The chrome above the tables shrinks to one heading line (title,
  count, actions), the section tabs and one single-line toolbar:
  filter labels go inside the controls, the item list's caption line
  folds into the toolbar, the row-height and heat controls move into
  a view menu, and `Tabelle | Details` sits at the toolbar's right
  end.
- The demo notice moves from the top of `main` into the sidebar,
  above the account links; it is no longer tied to a place.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `lab-demo`: Demo database — the notice shows once on every page, at
  no fixed place.

## Impact

- `webapp/orgsyndb_web/templates/orgsyndb_web/base.html`, the four
  Bestand list templates, `webapp/lab.css` (or the lab stylesheet
  in use), `lab.js` where the details pane is sized; tests of the
  demo notice.
- No data, no URL, no requirement on the lists' content changes.
