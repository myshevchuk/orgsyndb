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
- The change history becomes one collapsible widget, closed by
  default, holding a table of time, user, subject and change, one row
  per changed field. The item, batch, vessel and delivery note pages
  share its template already; the task page, which writes its own
  copy, moves onto it.
- Collapsible widgets print open, and a widget's open state and a
  table's sorting survive the refresh after a form saved in a
  dialog.
- The item page as the owner's chosen mockup: a figures strip of
  stock, coverage, means, the current year, usable bulk and latest
  start; two columns of widgets, consumption, movements (sortable)
  and bulk on the left, item data, containers by batch, the
  forecast with its delivery rhythm, and history on the right. The forecast becomes a
  key–value widget: each figure in bold, the parameters it used on
  the line under it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-app`: a new requirement, Widgets, states the shared rules for
  pages whose spec shows their data in widgets: the same data in the
  same kind of widget, collapsible widgets kept in the page and
  printed open, sorting in the browser with the server's order
  without the script, and both kept across a dialog's refresh.

The Item page (end-product-inventory), Item forecast
(production-planning) and Change history (web-app) requirements stay
true: they name the data and its order, not its layout; the
forecast widget keeps everything it holds under `Prognose`, the
delivery rhythm included, and each figure still names the parameters
it used.

## Impact

- `site/assets/css/screen.css` (widget classes; `print.css` is not
  touched), `webapp/orgsyndb_web/static/lab.css` and `lab.js`
  (sorting, refresh state, printing).
- Templates: `inventory/item_page.html`, `inventory/history.html`,
  `tasks/page.html`, `planning/item_forecast.html`; the German
  catalogues of `inventory`, `tasks` and `planning`.
- Tests that read the old item-page and history markup move to the
  new markup (listed in tasks).
- The help pages, if they show or describe the item page.
