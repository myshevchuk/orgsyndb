# lab-overview Specification

## Purpose
Show how the lab stands at a glance: an overview at `/lab/` of the stock by level, the year's deliveries against the year before, the syntheses due and next, the deliveries per month and the year's lists, and a summary at `/lab/summary/` that the site's home page frames in a lab build.
## Requirements
### Requirement: Overview page
The package `overview` SHALL answer `/lab/` with the page `Labor auf einen Blick` (`Lab at a glance`), readable without signing in, whose content below its `h1` is one `section.lab-overview` holding, in this order:

- **Stock.** The `h2` `Bestand` (`Inventory`), then a `div.stock-bar` of one link per level at which items of the inventory `end-products` are, in the order of Stock levels (end-product-inventory), each carrying `level-<level>`, linking to `/lab/inventory/end-products/?stock=<level>`, as wide as its share of the items, holding the number of items at that level and titled with the level's name and that number, and then a line counting the items.
- **Figures.** A `dl.lab-figures` holding, in this order:
  - `Abgegeben <year>` (`Delivered in <year>`), the current year: the containers delivered from 1 January through today, then `Vorjahr bis <date>: <n>` (`Last year to <date>: <n>`), the containers delivered from 1 January of the year before through `<date>`, the same day a year before, 28 February for 29 February;
  - `Fällige Synthesen` (`Syntheses due`), the number of articles whose forecast's priority is high or medium (production-planning "Slack and priority"), linking to `/lab/planning/`, then, when some planned or running task's slack is below zero, `<n> verspätet` (`<n> late`), the number of those tasks;
  - `Aufgaben` (`Tasks`), `<n> laufend · <m> geplant` (`<n> running · <m> planned`), the numbers of running and planned tasks, linking to `/lab/tasks/`;
  - `Offene Bulk-Lose` (`Open bulk lots`), the number of lots of `end-products` holding an amount above zero, linking to `/lab/inventory/end-products/bulk/`.
- **Next syntheses.** The `h2` `Nächste Synthesen` (`Next syntheses`), then a table of the five articles with a forecast of the smallest slack, ordered as the planning list orders them, with the columns `Artikelnr.`, `Name`, `Priorität`, `Spätester Start` and `Aufgabe` (`Article no.`, `Name`, `Priority`, `Latest start`, `Task`): the article number, linking to the page of its first item in the item list's order; that item's name; the priority; the latest start, or `–`; and the first of the article's planned and running tasks, running first, then by number, its number linking to its page, with its state and the mark `verspätet` when its slack is below zero, or `–`. A link `Zur Planung` (`To planning`) to `/lab/planning/` follows. Without a forecast, the text `Keine Prognosen.` (`No forecasts.`) takes the table's place.
- **Deliveries per month.** The `h2` `Abgaben je Monat` (`Deliveries per month`), then an inline `svg` with a bar per month of the twelve months ending with the current one, oldest first, its height the containers delivered in that month, and beside it a bar `.previous` for the same month a year before, each bar titled `<month> <year>: <n>`, the month as the language names it, and each month labelled below its bars.
- **Lists.** Each with an `h2` and an `ol`:
  - `Meistgefragt <year>` (`Most requested in <year>`): the five article numbers with the most containers delivered in the current year, most first, then by article number, each with the name of its first item and the containers;
  - `Empfänger <year>` (`Recipients in <year>`): the five recipients of the most containers delivered in the current year, most first, then by recipient regardless of case, notes without a recipient left out, each with the containers;
  - `Letzte Lieferscheine` (`Latest delivery notes`): the first five notes of the delivery list (end-product-inventory "Delivery list"), each with its date, its number linking to its page, or `–` linking to it for a note without one, its recipient, and the containers of its lines.

  A list without entries shows `Keine Abgaben.` (`No deliveries.`) in place of its `ol`.

The stock bar and the figures are the page's summary, which `/lab/summary/` shows alone (Summary for the home page). The containers delivered on a day are the counts of the delivery lines that count as consumption (end-product-inventory "Consumption") on notes of that day. The page carries no `script` element and no form beyond the page shell's.

#### Scenario: Stock bar
- **WHEN** the database holds two items at the level ok and one at low, and a test client not signed in requests `/lab/`
- **THEN** the page has one `section.lab-overview`, whose stock bar holds the links `level-low` reading 1 and `level-ok` reading 2, in this order, linking to `/lab/inventory/end-products/?stock=low` and `?stock=ok`, and the page has no `script` element

#### Scenario: Figures and lists
- **WHEN** on 2026-11-07 notes of 2026-03-02 deliver 3 containers of `CH-0012` to `AK Weber` and of 2026-10-01 2 of `CH-0010` without a recipient, notes of 2025-06-01 and 2025-12-01 deliver 4 and 5 of `CH-0012`, a current note of 2026-10-02 delivering 6 of `CH-0010` is reversed, one task is running and two are planned, and one lot is open, and a test client requests `/lab/`
- **THEN** the figures read 5 delivered in 2026, 4 to 07.11.2025, `1 laufend · 2 geplant` and 1 open lot; the most requested are `CH-0012` with 3 and `CH-0010` with 2; the recipients `AK Weber` with 3 alone; and the latest notes are those of 2026-10-02, 2026-10-01, 2026-03-02, 2025-12-01 and 2025-06-01

#### Scenario: Deliveries per month
- **WHEN** on 2026-11-07 the notes of 2026-03-02 deliver 3 containers and of 2025-03-15 4, and a test client requests `/lab/`
- **THEN** the `svg` holds twelve bars and twelve bars `.previous`, the first pair titled for December 2025 and December 2024, the bar of March 2026 titled with 3 and the `.previous` bar beside it, for March 2025, with 4

#### Scenario: Next syntheses
- **WHEN** seven articles have a forecast, the one of the smallest slack with a running task whose slack is below zero, and a test client requests `/lab/`
- **THEN** the table lists five articles in the planning list's order, the first naming the task with `verspätet`, and `Fällige Synthesen` counts the articles of high or medium priority with `1 verspätet`

#### Scenario: An empty lab
- **WHEN** the database holds no items, notes, tasks or lots, and a test client requests `/lab/`
- **THEN** the page answers 200, the stock bar holds no link, the figures read 0, `Keine Prognosen.` replaces the table, the `svg` holds twelve bars and twelve bars `.previous`, all of height 0, and each list shows `Keine Abgaben.`

#### Scenario: Overview in English
- **WHEN** the index's language is `en` and a test client requests `/lab/`
- **THEN** the `h1` reads `Lab at a glance` and the headings `Inventory`, `Next syntheses`, `Deliveries per month` and `Latest delivery notes`

### Requirement: Summary for the home page
`/lab/summary/` SHALL show, readable without signing in, the overview's summary alone: a `section.lab-summary` holding the `h1` `Labor auf einen Blick` (`Lab at a glance`), visually hidden, the stock bar and the figures as the overview page shows them, and a link `Zur Übersicht` (`To the overview`) to `/lab/`, every link opening in the top window. It is a page made to be framed: the web-app Page shell states its shell, without the site's header and with the demo note of a demo database. The site's home page frames it in a build that links the lab (site-theme "Home page").

#### Scenario: Summary
- **WHEN** the database holds two items at the level ok and one at low, one running task and one open lot, and a test client not signed in requests `/lab/summary/`
- **THEN** the page holds one `section.lab-summary` with the stock bar's links `level-low` and `level-ok`, the four figures with their links, and the link to `/lab/`, and no `section.lab-overview`, no table and no `svg`

