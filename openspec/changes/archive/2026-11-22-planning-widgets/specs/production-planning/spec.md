## MODIFIED Requirements

### Requirement: Planning list
`/lab/planning/` SHALL list the articles with a forecast whose priority is high or medium or for which an action is due, and with `all=1` every article with a forecast, ordered by slack, smallest first, then by article number. It shows its data in widgets (web-app "Widgets"): the list, the inspector of one article and the planning parameters.

**The list** is the widget `Planungsliste` (`Planning list`), whose count is the number of its rows that show, holding a table marked `data-sortable` with an `id` and the columns `Artikel`, `Reichweite`, `Synthesedauer`, `Spätester Start`, `Priorität`, `Aufgaben` and `Maßnahmen` (`Article`, `Runway`, `Synthesis time`, `Latest start`, `Priority`, `Tasks`, `Actions`). Each row carries `data-article` with its article number, `data-priority` with its priority, `high`, `medium` or `low`, `data-action="1"` when `Maßnahmen` holds an action and `data-late="1"` when `Aufgaben` holds a task marked `verspätet`, the last two absent otherwise.
- `Artikel` holds the article's name, the shown name of its substance, as a link to `/lab/planning/?selected=<article number>`, the number URL-encoded, keeping `all=1` when the list has it, and the article number.
- `Reichweite` the runway, marked `grob` when the model is rough; `Synthesedauer` the synthesis time; `Spätester Start` the latest start, or `–`; `Priorität` the priority. Their `data-sort` keys are the runway and the synthesis time in whole days, rounded down and written as digits; the latest start as `YYYY-MM-DD`, or `–` when there is none; and the priority's rank, `1` for high, `2` for medium and `3` for low.
- `Aufgaben` lists every matching planned or running task, running first, then by number, with its number linking to it and its state, marked `verspätet` (`late`) when its slack is below zero, or reads `–`.
- `Maßnahmen` gives each action that applies, or reads `–`:
  - `Abfüllen <size>` (`Fill <size>`), for each item whose runway on hand is below `buffer_days` and of whose containers the open vessels of its substance would fill at least one, linking to its filling form;
  - `Bulk prüfen` (`Check bulk`), linking to the vessel list, when an open vessel of the article's substance does not convert;
  - a synthesis, when the priority is high or medium, no matching task is planned or running, and every open vessel of the article's substance converts, since a vessel that does not may hold enough: for each sequence that Starting from stock proposes, `Synthese planen über <ID>` (`Plan synthesis via <ID>`), followed when it starts at a later step `k` by ` ab Stufe <k>, <name> vorrätig` (` from step <k>, <name> in stock`), the name of the substance in stock, linking for a signed-in user to `/lab/tasks/new/?substance=<key>&sequence=<ID>&start_step=<k>`, `<key>` the key of the article's substance; and when it proposes none, `Synthese planen` (`Plan synthesis`), linking for a signed-in user to `/lab/tasks/new/?substance=<key>`.

The list widget has the filter buttons `Alle`, `Priorität hoch`, `Mit Maßnahme` and `Verspätet` (`All`, `High priority`, `With action`, `Late`), in a group carrying `hidden` until the script reveals it; without the script every row shows. A button shows only the rows whose `data-priority` is `high`, that carry `data-action`, or that carry `data-late`; `Alle` shows every row and is active when the page loads. The active button carries `aria-pressed="true"` and the others `aria-pressed="false"`. Filtering sets `hidden` on the other rows, changes no data and is not kept in the address. When it hides the selected row, the first row that shows is selected; when it hides every row, the list says `Keine Zeile passt zum Filter.` (`No row matches the filter.`) and the inspector keeps its article. Printing prints the rows that show.

**The inspector** shows the selected article: the one named by `selected` when the list has a row of that article number, else the first row. It holds one block per row, carrying `data-article` with its article number, and every block but the selected one carries `hidden`. A block holds two widgets:
- `Gebinde & Bedarf` (`Containers and demand`), with the article number as note: a table with the columns `Gebinde`, `Bestand`, `Reichweite` and `Bedarf/Jahr` (`Container`, `Stock`, `Runway`, `Demand per year`), one row per item in the item list's order: its size linking to its page; its quantity with its level; its runway on hand, or `–`; and its demand per year in containers, rounded half up to one place, or `–`.
- `Planungsdetails` (`Planning details`), with the priority as note: a key–value table with `Substanz` (`Substance`), linking the substance's page with its shown name; `Letzte Lieferung` (`Last delivery`), the latest date of the delivery notes of the article's items that count, or `–`; `Bulk`, the usable bulk in the bulk unit; `Reichweite` (`Runway`), marked `grob` when rough; `Synthesedauer` (`Synthesis time`), with its basis; `Spätester Start` (`Latest start`), or `–`; and `Aufgaben` (`Tasks`), each task of the `Aufgaben` column with its expected end, today plus its remaining synthesis time, marked `verspätet` like there, or `–`.

The selected row carries `aria-current="true"`. With the script, a plain click in a row, but not on a link or button other than its `Artikel` link, or the arrow keys up and down in the list, which move to the previous or next row that shows and focus it, select a row without loading a page: its block shows, the others are hidden, the row is marked and `selected=<article number>` is written into the address. Without the script, the `Artikel` link loads the page with that selection.

When the list has no row, the page says `Kein Artikel braucht eine Synthese oder eine andere Maßnahme.` (`No article needs a synthesis or another action.`), or with `all=1` `Kein Artikel hat eine Prognose.` (`No article has a forecast.`), and has no list table and no inspector.

**The planning parameters** are the collapsible widget `Planungsparameter` (`Planning parameters`), closed when the page loads, whose note states the parameters in force in short and whose body lists each: the certainty, the buffer, the synthesis time until three syntheses exist, the history in quarters, the orders from which the order model applies, the high and medium priority bands, and the target.

#### Scenario: Actions
- **WHEN** on 2026-11-04 with the default parameters three articles of one 1 mg item each, every item with twelve quarters of 9 in the quarterly model and no tasks, exist: the first with 1 container and a vessel of 20 mg, the second with 10 containers and only a vessel in µmol, its substance without molar mass, the third with 10 containers and no vessel
- **THEN** the first is listed, though its priority is low, with `Abfüllen 1 mg`; the second shows check bulk and not plan synthesis; the third shows plan synthesis linking to the new-task form with its substance's key

#### Scenario: Created task matches its article
- **WHEN** a signed-in user follows an article's plan-synthesis link and saves the form
- **THEN** the article's row lists the new task and no longer offers plan synthesis

#### Scenario: Late synthesis
- **WHEN** a running task's slack is below zero
- **THEN** the row marks the task `verspätet`

#### Scenario: The inspector follows the selection
- **WHEN** a test client requests `/lab/planning/?all=1&selected=<the second row's article number>`, and then `/lab/planning/?all=1&selected=XX-0000`, which no row has
- **THEN** the first page's inspector shows the block of the second row's article, every other block carries `hidden`, the second row carries `aria-current="true"` and no other row does; the second page shows the first row's block

#### Scenario: Containers and demand in one table
- **WHEN** a test client requests the list on 2026-11-04 with an article of two items whose demands per year are 4.25 and 0.5 containers
- **THEN** the article's widget `Gebinde & Bedarf` holds one row per item, in the item list's order, each with its size linking its page, its quantity and level, its runway on hand and `4,3` and `0,5` under `Bedarf/Jahr` in its own row

#### Scenario: Filters in the browser
- **WHEN** the orchestrator opens the demo's planning list with `all=1` in a browser and activates each filter button, then selects rows by click and by the arrow keys (manual verification, tasks.md section 4)
- **THEN** each button shows the rows it names and only those, `Alle` shows every row again, and the inspector, the row mark and the address follow the selection

#### Scenario: Parameters closed
- **WHEN** a test client requests the list with the default parameters
- **THEN** the page holds a `details.widget` titled `Planungsparameter` without `open`, whose body states 95 %, 28 days, 21 days, 12 quarters, 6 orders, 14 and 56 days and 365 days
