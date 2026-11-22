## MODIFIED Requirements

### Requirement: Planning list
`/lab/planning/` SHALL list the articles with a forecast whose priority is high or medium or for which an action is due, and with `all=1` every article with a forecast, ordered by slack, smallest first, then by article number. It shows its data in widgets (web-app "Widgets"): the list, the inspector of one article and the planning parameters.

**The list** is the widget `Planungsliste` (`Planning list`), whose count is the number of its rows, holding a table marked `data-sortable` with an `id` and the columns `Artikel`, `Reichweite`, `Synthesedauer`, `Spätester Start`, `Priorität`, `Aufgaben` and `Maßnahmen` (`Article`, `Runway`, `Synthesis time`, `Latest start`, `Priority`, `Tasks`, `Actions`). Each row carries `data-article` with its article number.
- `Artikel` holds the article's name, the shown name of its substance, as a link to `/lab/planning/?selected=<article number>`, keeping `all=1` when the list has it, and the article number.
- `Reichweite` the runway, marked `grob` when the model is rough; `Synthesedauer` the synthesis time; `Spätester Start` the latest start, or `–`; `Priorität` the priority. Their `data-sort` keys are the runway and the synthesis time in days, the latest start as an ISO date, and the priority's rank, high first.
- `Aufgaben` lists every matching planned or running task, running first, then by number, with its number linking to it and its state, marked `verspätet` (`late`) when its slack is below zero.
- `Maßnahmen` gives each action that applies:
  - `Abfüllen <size>` (`Fill <size>`), for each item whose runway on hand is below `buffer_days` and of whose containers the open vessels of its substance would fill at least one, linking to its filling form;
  - `Bulk prüfen` (`Check bulk`), linking to the vessel list, when an open vessel of the article's substance does not convert;
  - a synthesis, when the priority is high or medium, no matching task is planned or running, and every open vessel of the article's substance converts, since a vessel that does not may hold enough: for each sequence that Starting from stock proposes, `Synthese planen über <ID>` (`Plan synthesis via <ID>`), followed when it starts at a later step `k` by ` ab Stufe <k>, <name> vorrätig` (` from step <k>, <name> in stock`), the name of the substance in stock, linking for a signed-in user to `/lab/tasks/new/?substance=<key>&sequence=<ID>&start_step=<k>`, `<key>` the key of the article's substance; and when it proposes none, `Synthese planen` (`Plan synthesis`), linking for a signed-in user to `/lab/tasks/new/?substance=<key>`.

Above the table, filter buttons `Alle`, `Priorität hoch`, `Mit Maßnahme` and `Verspätet` (`All`, `High priority`, `With action`, `Late`) show only the rows of high priority, with an action, or with a task marked `verspätet`; `Alle` shows every row and is active when the page loads. The active button carries `aria-pressed="true"` and the others `aria-pressed="false"`. The buttons are `hidden` until the script reveals them, and without the script every row shows. Filtering hides rows and changes no data; it is not kept in the address.

**The inspector** shows the selected article: the one named by `selected` when the list has a row of that article number, else the first row. It holds one block per row, `id="plan-<article number>"`, and every block but the selected one carries `hidden`. A block holds two widgets:
- `Gebinde & Bedarf` (`Containers and demand`), with the article number as note: a table with the columns `Gebinde`, `Bestand`, `Reichweite` and `Bedarf/Jahr` (`Container`, `Stock`, `Runway`, `Demand per year`), one row per item in the item list's order: its size linking to its page; its quantity with its level; its runway on hand, or `–`; and its demand per year in containers, rounded half up to one place, or `–`.
- `Planungsdetails` (`Planning details`), with the priority as note: a key–value table with `Substanz` (`Substance`), linking the substance's page with its shown name; `Letzte Lieferung` (`Last delivery`), the latest date of the delivery notes of the article's items that count, or `–`; `Bulk`, the usable bulk in the bulk unit; `Reichweite` (`Runway`), marked `grob` when rough; `Synthesedauer` (`Synthesis time`), with its basis; `Spätester Start` (`Latest start`), or `–`; and `Aufgaben` (`Tasks`), each task of the `Aufgaben` column with its expected end, today plus its remaining synthesis time, marked `verspätet` like there, or `–`.

The selected row carries `aria-current="true"`. With the script, a plain click in a row, but not on a link or button other than its `Artikel` link, or the arrow keys up and down in the list, select a row without loading a page: its block shows, the others are hidden, the row is marked and `selected=<article number>` is written into the address. Without the script, the `Artikel` link loads the page with that selection.

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
