## Why

The planning list is a twelve-column table that runs off the right edge
at 1440 px: the four columns that decide what to do — latest start,
priority, tasks and actions — are pushed out of sight, the containers
and their demand sit in parallel lists of two cells that misalign when
a line wraps, and a two-line paragraph of parameters stands above it on
every load. The owner chose mockup B of the widget survey: a list to
choose from beside an inspector of the chosen article, because "a
human can only focus on that many things at a time". The owner kept
the mockup's filter buttons and dropped its figures strip, which would
show data the page does not have today.

## What Changes

- The list becomes the widget `Planungsliste` with seven sortable
  columns: article, runway, synthesis time, latest start, priority,
  tasks and actions. The article's name selects it.
- An inspector shows the selected article in two widgets:
  `Gebinde & Bedarf`, one table row per item with its stock, runway on
  hand and demand per year side by side, and `Planungsdetails` with
  the substance, last delivery, bulk, runway, synthesis time and its
  basis, latest start and the tasks with their expected end.
- The selection is `selected=<article number>` in the address, so it
  works without the script; with it, a click or the arrow keys select
  a row without loading a page.
- Filter buttons `Alle`, `Priorität hoch`, `Mit Maßnahme` and
  `Verspätet` hide rows in the browser.
- The parameters move into a collapsible widget, closed on load.

The rows, their order, the forecast and the actions are unchanged; no
figure is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `production-planning`: "Planning list" describes the list, the
  inspector, the selection, the filters and the parameters widget.

## Impact

- `webapp/planning/templates/planning/list.html`, `parameters.html`,
  and new partials for the inspector; the German catalogue of
  `planning` (`locale/de/LC_MESSAGES/django.po` and `.mo`).
- `webapp/orgsyndb_web/static/lab.js` (selection and filters) and
  `lab.css` (the master–detail layout).
- `webapp/planning/views.py` passes `selected` to the template.
- Tests in `webapp/tests/test_planning_list.py`, `planning_support.py`
  and others that read the old columns or the parameters line.
