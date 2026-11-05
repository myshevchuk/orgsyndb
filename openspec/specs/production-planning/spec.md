# production-planning Specification

## Purpose
Compute when each end product must be synthesized again: demand models from the inventory's delivery notes and quarterly totals, runways at a certainty with the bulk shared out per article, synthesis time from past tasks, slack, latest start and priority, the computed priority of active tasks, the item forecast, the planning list with its actions, the planning parameters, and the ties between tasks and bulk lots of one batch.
## Requirements
### Requirement: Planning parameters
The `planning` package SHALL keep one record of planning parameters, with a change history, that staff edit in the admin:

- `certainty`, the probability `p` with which a stock is to last its runway, from 0.5 to 0.999, default 0.95;
- `buffer_days`, the time from a synthesis's end until its product can be delivered, for QC, filling and the unforeseen, from 0 to 365, default 28;
- `default_synthesis_days`, from 1 to 730, default 21;
- `history_quarters`, from 4 to 40, default 12;
- `min_orders`, from 3 to 100, default 6;
- `high_days` and `medium_days`, the priority bands, `0 ≤ high_days < medium_days`, defaults 14 and 56;
- `target_days`, from 30 to 1095, default 365.

When no record exists, the defaults apply. `z` is `statistics.NormalDist().inv_cdf(certainty)`.

#### Scenario: Defaults
- **WHEN** no parameter record exists
- **THEN** the forecast uses 0.95, 28, 21, 12, 6, 14, 56 and 365, and `z` is 1.6449 to four places

#### Scenario: Bands out of order
- **WHEN** a staff user saves `high_days` 60 and `medium_days` 56
- **THEN** the admin shows an error and keeps the earlier record

### Requirement: Matching tasks and articles
A task SHALL match an item of the inventory `end-products` when the task's product equals the item's article number regardless of case, or when `compound_for` finds a compound for both and it is the same compound. A task matches an article when it matches one of its items. Planning works on articles: all items of the inventory `end-products` with one article number.

#### Scenario: Match by compound and by text
- **WHEN** the index is the demo collection's, items `CH-0012` of 10 µmol and of 50 µmol and an item `NV-7` exist, and tasks name the products `cinnamic-acid` and `nv-7`
- **THEN** the first task matches the article `CH-0012` and both its items, and the second matches `NV-7`

### Requirement: Demand models
An item's demand SHALL be described by one of two models, estimated from its history window: the last `history_quarters` complete quarters, leaving out quarters before the item's first quarter with data. An item whose history window is empty or holds no consumption has no demand and no forecast. Orders are the item's delivery-note lines that count as consumption, each with its date and count.

The order window is the latest quarters of the history window back to the latest quarter with an entered consumption value, not including it, or the whole history window when none has one. When it holds at least `min_orders` orders, the **order model** applies:

- the order rate `λ`, per day, is the larger of the number of orders in the order window divided by its calendar days and the number in its latest four quarters, or all of them when it has fewer, divided by their calendar days;
- the order size follows the empirical distribution of the counts of the orders in the order window;
- the demand over `H` days is compound Poisson: a Poisson number of orders with mean `λH`, each of a size drawn independently from that distribution;
- the need for `H` days at a certainty `q` is the smallest whole number `n` with `P(demand ≤ n) ≥ q`.

Otherwise the **quarterly model** applies, and every figure it gives is marked `grob` (`rough`):

- `m` is the larger of the mean consumption of the history window's quarters and that of its latest four quarters, or all of them when it has fewer;
- `v` is the larger of the sample variance of the history window's quarters, zero for one quarter, and `m`;
- per day, `μ = m / 91.3125` and `σ = √(v / 91.3125)`;
- the need for `H` days at a certainty `q` is `μH + z_q σ√H`, `z_q` being `statistics.NormalDist().inv_cdf(q)`.

The demand per year shows as `365.25 λ` times the mean order size, or as `4m`.

#### Scenario: Order model
- **WHEN** on 2026-11-04 an item has one delivery note of 10 containers in each of the eight quarters from the fourth of 2024 to the third of 2026 and no entered values
- **THEN** the order model applies with `λ` 8/730 per day and every order of size 10

#### Scenario: Entered values leave too few orders
- **WHEN** an item has entered values up to the second quarter of 2026 and two delivery notes in the third
- **THEN** the quarterly model applies and its figures are marked `grob`

#### Scenario: Rising demand in the quarterly model
- **WHEN** on 2026-11-04 an item's twelve last complete quarters hold entered values of 4 each for the first eight and 12 each for the last four
- **THEN** `m` is 12 and `v` is 15.52 to two places

### Requirement: Runway
The runway of an item for a stock of `S` containers at a certainty `q` SHALL be the longest number of days `H` whose need at `q` is at most `S`, the same rule holding for `S` zero. In the quarterly model it is `((−z_q σ + √(z_q²σ² + 4μS)) / (2μ))²`, zero for `S` zero; in the order model, the `H` at which `P(demand over H ≤ S)` falls to `q`, to 0.01 days, which for `S` zero is the time within which no order arrives with probability `q`. An item's runway on hand is that of its quantity at `certainty`.

An article's runway uses, for each of its `k` items with demand, the certainty `q_k = 1 − (1 − certainty) / k`, so that by the union bound all of them are covered together with probability at least `certainty`, whatever the relation between their demands. Its bulk unit is µmol when the compound has a molar mass, else the kind of unit, mass or amount of substance, of the article's first item by unit and size. An item converts when its container size converts into that unit; `s_max` is the largest container size, in that unit, among the converting items with demand, and zero when none has demand. Each open lot that converts counts with its amount in that unit minus `s_max`, where positive, so that whatever is counted can be filled in whole containers of any size. The usable bulk is the sum of those amounts. The article's runway is the longest `H` that meets two conditions:

- the sum, over the converting items with demand, of the whole containers each lacks for `H` days at `q_k`, its need minus its quantity where positive, rounded up, times its container size, does not exceed the usable bulk;
- `H` is at most the runway on hand at `q_k` of every item with demand that does not convert.

An article has a forecast when one of its items has demand. Runways show as whole days, rounded down; comparisons use the unrounded values.

#### Scenario: Even demand
- **WHEN** with the default parameters an item of 1 mg with 10 containers, no bulk and the quarterly model with `m` 9 and `v` 9 is its article's only item
- **THEN** the item's runway on hand and the article's runway are 60 days, and at a certainty of 0.5 they are 101 days

#### Scenario: Lumpy orders
- **WHEN** with the default parameters the item of the order-model scenario holds 9, 10 or 20 containers
- **THEN** its runway on hand is 4, 32 or 74 days, where the quarterly model of the same history would give 47 days for 9

#### Scenario: Bulk shared by two sizes
- **WHEN** with the default parameters an article has items of 10 mg and 20 mg, each without containers and with twelve quarters of 9 in the quarterly model, and one open lot of 360 mg
- **THEN** each item is planned at a certainty of 0.975, the usable bulk is 340 mg, and the article's runway is 62 days, where giving each size the whole lot at 0.95 would claim 277 and 124

#### Scenario: Lots too small to fill
- **WHEN** an article's only item, of 10 mg, has 10 containers and two open lots of 6 mg each
- **THEN** its usable bulk is zero and its runway is its runway on hand

### Requirement: Synthesis time
An article's synthesis time `L` SHALL be the longest duration in days, end date minus start date and at least 1, among the last three ended tasks that match it and are not cancelled, ordered by end date, then start date, then number; with fewer than three such tasks, the longest of their durations and `default_synthesis_days`. Its basis shows as `Vorgabe` (`default`), `die letzte Synthese` (`the last synthesis`) when one synthesis decided it, or `längste der letzten <k> Synthesen` (`longest of the last <k> syntheses`). A planned task's remaining synthesis time is `L`; a running task's is `L` minus the days since its start, at least zero.

#### Scenario: Longest of the last three
- **WHEN** four ended tasks match an article, taking 90, 20, 30 and 40 days in the order of their end dates
- **THEN** its synthesis time is 40 days

#### Scenario: The default until three exist
- **WHEN** one ended task of 10 days matches an article
- **THEN** its synthesis time is 21 days, the default

### Requirement: Slack and priority
An article's slack SHALL be its runway minus `buffer_days` minus `L`; its latest start is today plus its slack in whole days, rounded down, or none, shown as `–`, when that date lies beyond the calendar's last, and slack shows as whole days, rounded down. The priority of a slack is `high` below `high_days`, `medium` below `medium_days`, and `low` otherwise. The priority of an article is that of its slack and says how urgently a new synthesis is needed; work under way does not change it. A planned or running task's slack is the smallest, over the articles it matches that have a forecast, of the article's runway minus `buffer_days` minus the task's remaining synthesis time, and says whether that task will deliver in time; it is late when its slack is below zero. Ended and cancelled tasks have no slack.

#### Scenario: Priority bands
- **WHEN** on 2026-11-04 with the default parameters articles of one item of 1 mg, with `m` 9, `v` 9, no bulk and no matching tasks, hold 10, 15 and 25 containers
- **THEN** their slacks are 11, 50 and 133 days, their priorities high, medium and low, and the first's latest start is 2026-11-15

#### Scenario: A running synthesis
- **WHEN** with the default parameters a task started 14 days ago matches the article with 10 containers above
- **THEN** the task's slack is 25 days and its priority medium, while the article's stays high

#### Scenario: Two sizes, one priority
- **WHEN** the article of the shared-bulk scenario has no matching tasks
- **THEN** its slack is 13 days and its priority high

### Requirement: Computed priority on tasks
A planned or running task with a slack SHALL have the priority of that slack, its computed priority, shown with `berechnet` (`computed`) and the slack in days as its title; every other task has its entered priority, shown with `manuell` (`entered`). Wherever the application shows, orders or filters tasks by priority, it uses that priority, and there is no override.

#### Scenario: Computed priority
- **WHEN** on 2026-11-04 with the default parameters a planned task with the entered priority low matches an article whose slack is 11 days
- **THEN** its priority is high, shown with `berechnet` and the title `11 Tage`

#### Scenario: Ended task keeps its entered priority
- **WHEN** an ended task with the entered priority low matches that article
- **THEN** it shows `niedrig` with `manuell`

### Requirement: Item forecast
An item's forecast, shown on the item page, SHALL hold for an item with demand: its model, with `λ`, the number of orders and their median and largest size, or `m`, `v` and the number of quarters, marked `grob`; its runway on hand; and for its article the bulk, runway, synthesis time with its basis, slack, latest start and priority. It shows the amount a new synthesis must yield: for the converting items with demand, the sum of the whole containers each lacks for `L + buffer_days + target_days` days at `q_k`, its need minus its quantity where positive, rounded up, times its container size, minus the usable bulk, at least zero, in the bulk unit rounded up to a whole mg or µmol, and, when the bulk unit is µmol, also in mg, the unrounded amount converted and rounded up to a whole mg; and for each item that does not convert, the whole containers it lacks for that time, rounded up, as a count of its own size. It shows the delivery rhythm: the last delivery's date, the number of delivery notes in the past 365 days, and, given at least three notes in the past 730 days, the median number of days between their consecutive dates, rounded half up to a whole day, and the next delivery expected that many days after the last. Lines of reversed movements and reversed historical notes do not count. Each figure names the parameters it used. An item without demand shows `Kein Verbrauch, keine Prognose.` (`No consumption, no forecast.`).

#### Scenario: Forecast figures
- **WHEN** on 2026-11-04 with the default parameters the page of the 1 mg item with 10 containers, `m` 9, `v` 9, no bulk and an article number that names no compound of the index is requested
- **THEN** it shows the runway 60 days, the synthesis time 21 days by default, the slack 11 days, the latest start 2026-11-15, the priority high, and 42 mg for a new synthesis, all marked `grob`

#### Scenario: Delivery rhythm
- **WHEN** on 2026-11-04 an item has delivery notes dated 2026-06-01, 2026-07-01, 2026-08-31 and 2026-10-01
- **THEN** the page shows the last delivery 2026-10-01, four deliveries in the past year, a usual interval of 31 days and the next delivery expected on 2026-11-01

### Requirement: Planning list
`/lab/planning/` SHALL list the articles with a forecast whose priority is high or medium or for which an action is due, and with `all=1` every article with a forecast, ordered by slack, smallest first, then by article number. The table has the columns `Artikelnr.`, `Name`, `Gebinde`, `Bedarf/Jahr`, `Letzte Lieferung`, `Bulk`, `Reichweite`, `Synthesedauer`, `Spätester Start`, `Priorität`, `Aufgaben` and `Maßnahmen` (`Article no.`, `Name`, `Containers`, `Demand per year`, `Last delivery`, `Bulk`, `Runway`, `Synthesis time`, `Latest start`, `Priority`, `Tasks`, `Actions`). `Name` is the name of the article's first item in the item list's order. `Gebinde` lists each item, in that order, with its size, quantity with its level, and runway on hand; `Bedarf/Jahr` each item's demand per year in containers, rounded half up to one place, in the same order; `Letzte Lieferung` the latest date of the delivery notes of the article's items that count; and `Bulk` the usable bulk in the bulk unit. `Aufgaben` lists every matching planned or running task, running first, then by number, with its number linking to it, its state and its expected end, today plus its remaining synthesis time, marked `verspätet` (`late`) when its slack is below zero. `Maßnahmen` gives each that applies:

- `Abfüllen <size>` (`Fill <size>`), for each item whose runway on hand is below `buffer_days` and of whose containers the open lots would fill at least one, linking to its filling form;
- `Bulk prüfen` (`Check bulk`), linking to the bulk list, when an open lot of the article does not convert;
- `Synthese planen` (`Plan synthesis`), linking for a signed-in user to `/lab/tasks/new/?product=<article number>`, when the priority is high or medium, no matching task is planned or running, and every open lot of the article converts, since a lot that does not may hold enough.

The line above the table states the parameters in force.

#### Scenario: Actions
- **WHEN** on 2026-11-04 with the default parameters three articles of one 1 mg item each, every item with twelve quarters of 9 in the quarterly model and no tasks, exist: the first with 1 container and a lot of 20 mg, the second with 10 containers and only a lot in µmol of a compound without molar mass, the third with 10 containers and no lot
- **THEN** the first is listed, though its priority is low, with `Abfüllen 1 mg`; the second shows check bulk and not plan synthesis; the third shows plan synthesis linking to the new-task form with its article number

#### Scenario: Created task matches its article
- **WHEN** a signed-in user follows an article's plan-synthesis link and saves the form
- **THEN** the article's row lists the new task and no longer offers plan synthesis

#### Scenario: Late synthesis
- **WHEN** a running task's slack is below zero
- **THEN** the row marks the task `verspätet`

### Requirement: Batches between tasks and bulk
A task and a bulk lot SHALL belong to each other when their batches are equal and not empty and the task matches the lot's article. The task page and the lot page link the records that belong to theirs, and an ended task with a batch offers to record it as a lot, as `task-tracker` and `end-product-inventory` state.

#### Scenario: Bulk from an ended task
- **WHEN** a signed-in user opens the link on an ended task with the batch `B-2026-031` naming `CH-0012`, and saves the form with an amount
- **THEN** a lot `CH-0012` with the batch `B-2026-031` exists, and the task's page and the lot's page link to each other

#### Scenario: Same batch, other product
- **WHEN** a lot of `NV-7` and a task naming `CH-0012` both have the batch `B-001`
- **THEN** neither page links the other

