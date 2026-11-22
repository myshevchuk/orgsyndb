## Context

`planning/list.html` renders one table row per article from
`Plan.row(found)`: the forecast (`found`, with its items, figures,
runway, synthesis time and basis, latest start, priority, last
delivery, usable bulk) and the row's tasks and actions. The view sorts
rows by slack. The lab already has the pieces this page needs:
`section.widget` and `details.widget` with title bars, `.widget-table`
and `.kv-table`, `data-sortable` tables (web-app "Widgets"), and on the
item list a row choice by click or arrow keys that marks the row with
`aria-current="true"` and writes `selected` into the address. The
chosen mockup is `planning-B` in
`~/local/workspace/orgsyndb/ui-widgets-survey/mockups/`.

## Goals / Non-Goals

**Goals:** the decision columns visible without horizontal scrolling at
1440 px; one article's whole forecast in one place; containers and
their demand in one row each; the parameters out of the way.

**Non-Goals:** the mockup's figures strip (new data); counts on the
filter buttons; filtering on the server or keeping the filter in the
address; a fragment endpoint for the inspector; changes to the
forecast, the row selection rules or the actions.

## Decisions

1. **All inspector blocks are rendered; one shows.** The page renders
   a block per row and hides all but the selected one. The list holds
   the urgent articles, or every article with a forecast, a few dozen
   at most, so the page stays small, and a selection needs no request.
   Alternative rejected: an htmx fragment as on the item list — a new
   endpoint and view for data the page already has.

2. **Selection in the address, with a link for the no-script case.**
   The `Artikel` link is `?selected=<article number>` (keeping
   `all=1`); the view passes `selected` on, and the template shows that
   block or the first. The script intercepts the link and row clicks,
   switches blocks, sets `aria-current` and writes the address with
   `history.replaceState`. It follows the item list's conventions —
   plain click outside links and buttons, arrow keys — but is its own
   small handler, since the item list's fires htmx loads.

3. **Columns chosen for the decision.** The list keeps what decides the
   order of work: runway, synthesis time, latest start, priority, tasks
   and actions. Containers, demand, last delivery and bulk move to the
   inspector. The containers' demand stands in the same table row as
   its container, which ends the misaligned parallel lists. Bulk leaves
   the list also because its amounts are in mg or µmol and cannot be
   sorted together. Tasks show number, state and `verspätet` in the
   list and add the expected end in the inspector.

4. **Sort keys.** Runway and synthesis time sort by days, the latest
   start by ISO date, the priority by rank (`1` high, `2` medium, `3`
   low), the rest by text. Without the script, or until a user sorts,
   the rows stay in slack order.

5. **Filters in the browser.** The buttons set `hidden` on rows by the
   row's `data-priority`, `data-action` and `data-late` attributes,
   which the template writes from the row it already has. They are
   `hidden` until the script runs, so a page without the script shows
   no dead controls. No count: the owner kept the buttons, not numbers.

6. **Parameters as a closed `details.widget`.** Its note is the short
   line (`95 % · 28 T. · …`), its body a `.kv-table` with one row per
   parameter. Print opens it (web-app "Widgets").

7. **Print** shows the list, the selected article's inspector and the
   parameters: what the screen shows.

## Risks / Trade-offs

- [Selected row filtered out] → the inspector keeps showing it; the
  filter only hides rows.
- [Sorting moves the selected row] → selection follows the article,
  not the position; arrow keys move in the current order.
- [Tests read the old twelve columns] → rewritten to read the list's
  cells and the inspector's tables (tasks section 1).
- [Narrow windows] → the inspector follows the list; selecting a row
  there scrolls the inspector into view.
