## Why

The lab's record pages stack their data as headings, definition lists
and prose, one section under the next. The item page runs to about
3200 px at 1440 px width: its forecast buries each figure in a
sentence, and its change history is a nested bullet list. The same
kinds of data look different on each page that shows them.

The owner decided on 2026-11-22, after a UI survey with mockups
(kept outside the repository), that record pages group their data
into widgets: framed sections with a short title that look the same
wherever the same data appears. Tables replace bullet lists, text is
cut and the type is smaller. The layout changes; the data and logic
do not. The owner chose a mockup for each of four pages, to be built
one change per page; this change builds the shared machinery and the
first page, the item page. Where a spec stands in the way of the new
layout, it is removed rather than re-specified.

## What Changes

- Shared widget machinery, in the site's stylesheets so that the
  Hugo pages can use it later as well as the lab:
  - a widget frame with a title bar holding the title, an optional
    count and a muted note;
  - a compact table and a key–value table, the latter with a muted
    line under a value for the basis it was computed from;
  - a figures strip of small tiles;
  - a collapsible widget, built on `details`;
  - smaller type inside widgets.
- Tables a template marks as sortable sort in the browser by the
  column whose header is activated, through `lab.js`; without the
  script they keep the server's order.
- The change history, which every record page shows through one
  template, becomes a collapsible widget holding a table of time,
  user, subject and change, one row per changed field. This changes
  the item, batch, vessel, delivery note and task pages alike.
- The item page as the owner's chosen mockup: a figures strip of
  stock, coverage, means, the current year, usable bulk and latest
  start; two columns of widgets, consumption, movements (sortable)
  and bulk on the left, item data, containers by batch, forecast,
  delivery rhythm and history on the right. The forecast becomes a
  key–value widget: each figure in bold, the parameters it used on
  the line under it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-app`: a new requirement, Widgets, states the shared rules:
  record pages group their data into widgets, the same data in the
  same widget on every page, and sortable tables keep their server
  order without the script.

The Item page (end-product-inventory), Item forecast
(production-planning) and Change history (web-app) requirements stay
true: they name the data and its order, not its layout, and each
forecast figure still names the parameters it used.

## Impact

- `site/assets/css/screen.css` (widget classes), `webapp/orgsyndb_web/
  static/lab.css` and `lab.js` (sorting).
- Templates: `inventory/item_page.html`, `inventory/history.html`,
  `planning/item_forecast.html`; the German message catalogue for the
  forecast's split strings.
- Tests that read the history as `ul.lab-history` move to the table.
- The help pages, if they show or describe the item page.
