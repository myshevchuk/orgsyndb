## MODIFIED Requirements

### Requirement: Planning list
`/lab/planning/` SHALL list the articles with a forecast whose priority is high or medium or for which an action is due, and, with `all=1`, every article with a forecast. Its default order is by slack, smallest first, then by article number. It is a main list (web-app "Main lists") under the heading `Planung` (`Planning`), followed by the number of its rows. The page also holds the planning parameters.

**The filters.** A filter form above the list holds:

- a choice `Anzeigen` (`Show`), the GET parameter `show`, offering `Alle`, `Priorität hoch`, `Mit Maßnahme` and `Verspätet` (`All`, `High priority`, `With action`, `Late`). `high` lists the rows whose priority is high; `action` those whose `Maßnahmen` holds an action; `late` those whose `Aufgaben` holds a task marked `verspätet`. Without `show`, or with another value, it lists every row.
- a check box `Alle Artikel` (`All articles`), the GET parameter `all=1`.

The form keeps their values and the order in force. It implements live list updates (web-app "Live lists"): it updates `#item-rows` in place with `morph:outerHTML`, and `#planning-count`, `#item-head`, `#item-detail` and `#filter-selected` out of band with `#planning-count:morph,#item-head:morph,#item-detail:morph,#filter-selected:morph`. Its column header links update `#item-rows` in place, and out of band `#planning-count:morph,#item-head:morph,#item-detail:morph,#filters:morph`. It uses `hx-get="/lab/planning/"`, `hx-push-url="true"`, `hx-sync="#main:replace"` and the triggers `submit, change target:(select, input[type=checkbox])`. It keeps `method="get"`, `action="/lab/planning/"` and a submit button. Its non-restore HTMX GET responses push `/lab/planning/` with:

- `all=1` when given;
- a valid `show`;
- `sort` and `dir=desc` as web-app "Main lists" states;
- the resolved `selected` article number, omitted when the list is empty.

**The list's table** has the columns `Artikel`, `Reichweite`, `Synthesedauer`, `Spätester Start`, `Priorität`, `Aufgaben` and `Maßnahmen` (`Article`, `Runway`, `Synthesis time`, `Latest start`, `Priority`, `Tasks`, `Actions`), and each row carries `data-item` with its article number.

- `Artikel` holds the article's name, the shown name of its substance, linking to the substance's page, and the article number.
- `Reichweite` holds the runway, marked `grob` when the model is rough; `Synthesedauer` the synthesis time; `Spätester Start` the latest start, or `–`; and `Priorität` the priority. The runway and the synthesis time sort by their days.
- `Aufgaben` lists every matching planned or running task, running first, then by number, with its number linking to it and its state, marked `verspätet` (`late`) when its slack is below zero. It reads `–` when there is none, and sorts by its first task's number.
- `Maßnahmen` gives each action that applies, or reads `–`:
  - `Abfüllen <size>` (`Fill <size>`), for each item whose runway on hand is below `buffer_days` and of whose containers the open vessels of its substance would fill at least one, linking to its filling form;
  - `Bulk prüfen` (`Check bulk`), linking to the vessel list, when an open vessel of the article's substance does not convert;
  - a synthesis, when the priority is high or medium, no matching task is planned or running, and every open vessel of the article's substance converts, since a vessel that does not may hold enough. For each sequence that Starting from stock proposes, it offers `Synthese planen über <ID>` (`Plan synthesis via <ID>`), followed, when the sequence starts at a later step `k`, by ` ab Stufe <k>, <name> vorrätig` (` from step <k>, <name> in stock`), the name of the substance in stock. For a signed-in user it links to `/lab/tasks/new/?substance=<key>&sequence=<ID>&start_step=<k>`, `<key>` the key of the article's substance. When Starting from stock proposes no sequence, it offers `Synthese planen` (`Plan synthesis`), linking for a signed-in user to `/lab/tasks/new/?substance=<key>`.

When the list has no article, `#item-rows` holds a single row whose one cell, spanning the columns, says:

- `Keine Zeile passt zum Filter.` (`No row matches the filter.`) when `show` is in force and the list without it has a row;
- otherwise `Kein Artikel braucht eine Synthese oder eine andere Maßnahme.` (`No article needs a synthesis or another action.`);
- or, with `all=1`, `Kein Artikel hat eine Prognose.` (`No article has a forecast.`).

**The details of an article**, `/lab/planning/<article number>/detail/`, the article number percent-encoded as one path segment, `/` among its characters, show the article's name and number as heading and two parts:

- `Gebinde & Bedarf` (`Containers and demand`): a table with the columns `Gebinde`, `Bestand`, `Reichweite` and `Bedarf/Jahr` (`Container`, `Stock`, `Runway`, `Demand per year`), one row per item in the item list's order. Each row holds the item's size linking to its page; its quantity with its level; its runway on hand, or `–`; and its demand per year in containers, rounded half up to one place, or `–`.
- `Planungsdetails` (`Planning details`), with the priority: a key–value table with these entries:
  - `Substanz` (`Substance`), linking the substance's page with its shown name;
  - `Letzte Lieferung` (`Last delivery`), the latest date of the delivery notes of the article's items that count, or `–`;
  - `Bulk`, the usable bulk in the bulk unit;
  - `Reichweite` (`Runway`), marked `grob` when rough;
  - `Synthesedauer` (`Synthesis time`), with its basis;
  - `Spätester Start` (`Latest start`), or `–`;
  - `Aufgaben` (`Tasks`), each task of the `Aufgaben` column with its expected end, today plus its remaining synthesis time, marked `verspätet` like there, or `–`.

A row requests its article's details with the list's `all` and `show` in force as its query. The endpoint keeps that query in `HX-Replace-Url` and in its redirect without HTMX, so that an article listed only with `all=1` stays selected. An article number that names no article with a forecast answers 404.

**The planning parameters** are the collapsible widget `Planungsparameter` (`Planning parameters`), closed when the page loads. Its note states the parameters in force in short, and its body lists each: the certainty, the buffer, the synthesis time until three syntheses exist, the history in quarters, the orders from which the order model applies, the high and medium priority bands, and the target.

#### Scenario: Actions
- **WHEN** on 2026-11-04 with the default parameters three articles exist, each of one 1 mg item, every item with twelve quarters of 9 in the quarterly model and no tasks: the first with 1 container and a vessel of 20 mg; the second with 10 containers and only a vessel in µmol, its substance without molar mass; the third with 10 containers and no vessel
- **THEN** the first is listed, though its priority is low, with `Abfüllen 1 mg`; the second shows check bulk and not plan synthesis; the third shows plan synthesis linking to the new-task form with its substance's key

#### Scenario: Created task matches its article
- **WHEN** a signed-in user follows an article's plan-synthesis link and saves the form
- **THEN** the article's row lists the new task and no longer offers plan synthesis

#### Scenario: Late synthesis
- **WHEN** a running task's slack is below zero
- **THEN** the row marks the task `verspätet`

#### Scenario: The details follow the selection
- **WHEN** a test client requests `/lab/planning/?all=1&selected=<the second row's article number>`, and then `/lab/planning/?all=1&selected=XX-0000`, which no row has
- **THEN** the first page's second row carries `aria-current="true"`, no other row does, and `#item-detail` shows the second row's article; the second page selects the first row and shows its article

#### Scenario: Containers and demand in one table
- **WHEN** on 2026-11-04 a test client requests the details of an article of two items whose demands per year are 4.25 and 0.5 containers
- **THEN** its table `Gebinde & Bedarf` holds one row per item, in the item list's order, each with its size linking its page, its quantity and level, its runway on hand, and `4,3` and `0,5` under `Bedarf/Jahr` in its own row

#### Scenario: Filters on the server
- **WHEN** with `all=1` the list holds an article of high priority with no action and no late task, one of low priority with an action, and one of high priority with a late task, and a test client requests it with `show=high`, `show=action`, `show=late` and `show=bogus`
- **THEN** the answers list the first and third articles, the second, the third, and all three, and each shows its rows' number as the count

#### Scenario: A filter that matches no row
- **WHEN** the list without `all=1` holds only articles of medium priority with no late task, and a test client requests it with `show=late`, once with `HX-Request: true`
- **THEN** both answers' `#item-rows` hold a single row saying `Keine Zeile passt zum Filter.` and no article, and `#item-detail` holds no article's details

#### Scenario: An article number with reserved characters
- **WHEN** an article `XY 1&2+3#4/5` has a forecast, and a test client requests the list with `all=1` and `selected` naming it, and then its details endpoint with `all=1` and without HTMX headers
- **THEN** its row's `hx-get` names the number percent-encoded with `all=1`, the details show the article, and the redirect leads to `/lab/planning/` with `all=1` and `selected` naming it

#### Scenario: The canonical address
- **WHEN** with `all=1` the list holds an article with a late task, and a test client requests `/lab/planning/?all=1&show=late&sort=priority&dir=desc` and `/lab/planning/?show=bogus&sort=start` with `HX-Request: true`
- **THEN** the first pushes `/lab/planning/?all=1&show=late&sort=priority&dir=desc&selected=<resolved>`, and the second `/lab/planning/?selected=<resolved>`, or `/lab/planning/` when it lists no row

#### Scenario: Parameters closed
- **WHEN** a test client requests the list with the default parameters
- **THEN** the page holds a `details.widget` titled `Planungsparameter` without `open`, whose body states 95 %, 28 days, 21 days, 12 quarters, 6 orders, 14 and 56 days and 365 days
