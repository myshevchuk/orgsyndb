## MODIFIED Requirements

### Requirement: Matching tasks and articles
A task SHALL match the article of its substance, when the substance has one. Planning works on articles, each the items of one substance; an article without an article number has no consumption and no forecast, and the tasks that match it show their entered priority.

#### Scenario: Match by substance
- **WHEN** items of 10 µmol and of 50 µmol of the article `CH-0012`, of the substance `cinnamic-acid`, and an item of the article `NV-0007`, of `new-compound-7`, exist, and tasks name the substances `cinnamic-acid` and `new-compound-7`
- **THEN** the first task matches the article `CH-0012` and both its items, and the second matches `NV-0007`

#### Scenario: A position without an article number
- **WHEN** an item of the substance `1-phenylethanol`, whose article has no article number, has 8 containers, and a planned task names `1-phenylethanol`
- **THEN** the planning list with `all=1` lists no article for the item, and the task shows its entered priority

### Requirement: Batches between tasks and bulk
A task and a bulk lot SHALL belong to each other when their batches are equal and not empty and the task's substance is the lot's. The task page and the lot page link the records that belong to theirs, and an ended task with a batch offers to record it as a lot, as `task-tracker` and `end-product-inventory` state.

#### Scenario: Bulk from an ended task
- **WHEN** a signed-in user opens the link on an ended task of `cinnamic-acid` with the batch `B-2026-031`, and saves the form with an amount
- **THEN** a lot of `cinnamic-acid`, made in the lab, with the batch `B-2026-031` exists, and the task's page and the lot's page link to each other

#### Scenario: Same batch, other substance
- **WHEN** a lot of `new-compound-7` and a task of `cinnamic-acid` both have the batch `B-001`
- **THEN** neither page links the other

### Requirement: Item forecast
An item's forecast, shown on the item page, SHALL hold for an item with demand: its model, with `λ`, the number of orders and their median and largest size, or `m`, `v` and the number of quarters, marked `grob`; its runway on hand; and for its article the bulk, runway, synthesis time with its basis, slack, latest start and priority. It shows the amount a new synthesis must yield: for the converting items with demand, the sum of the whole containers each lacks for `L + buffer_days + target_days` days at `q_k`, its need minus its quantity where positive, rounded up, times its container size, minus the usable bulk, at least zero, in the bulk unit rounded up to a whole mg or µmol, and, when the bulk unit is µmol, also in mg, the unrounded amount converted and rounded up to a whole mg; and for each item that does not convert, the whole containers it lacks for that time, rounded up, as a count of its own size. It shows the delivery rhythm: the last delivery's date, the number of delivery notes in the past 365 days, and, given at least three notes in the past 730 days, the median number of days between their consecutive dates, rounded half up to a whole day, and the next delivery expected that many days after the last. Lines of reversed movements and reversed historical notes do not count. Each figure names the parameters it used. A dormant item shows `Ruhend, keine Prognose.` (`Dormant, no forecast.`), and every other item without demand `Kein Verbrauch, keine Prognose.` (`No consumption, no forecast.`).

#### Scenario: Forecast figures
- **WHEN** on 2026-11-04 with the default parameters the page of the 1 mg item with 10 containers, `m` 9, `v` 9, no bulk and a substance without molar mass is requested
- **THEN** it shows the runway 60 days, the synthesis time 21 days by default, the slack 11 days, the latest start 2026-11-15, the priority high, and 42 mg for a new synthesis, all marked `grob`

#### Scenario: Delivery rhythm
- **WHEN** on 2026-11-04 an item has delivery notes dated 2026-06-01, 2026-07-01, 2026-08-31 and 2026-10-01
- **THEN** the page shows the last delivery 2026-10-01, four deliveries in the past year, a usual interval of 31 days and the next delivery expected on 2026-11-01

### Requirement: Planning list
`/lab/planning/` SHALL list the articles with a forecast whose priority is high or medium or for which an action is due, and with `all=1` every article with a forecast, ordered by slack, smallest first, then by article number. The table has the columns `Artikelnr.`, `Name`, `Gebinde`, `Bedarf/Jahr`, `Letzte Lieferung`, `Bulk`, `Reichweite`, `Synthesedauer`, `Spätester Start`, `Priorität`, `Aufgaben` and `Maßnahmen` (`Article no.`, `Name`, `Containers`, `Demand per year`, `Last delivery`, `Bulk`, `Runway`, `Synthesis time`, `Latest start`, `Priority`, `Tasks`, `Actions`). `Name` is the article's name. `Gebinde` lists each item, in that order, with its size, quantity with its level, and runway on hand; `Bedarf/Jahr` each item's demand per year in containers, rounded half up to one place, in the same order; `Letzte Lieferung` the latest date of the delivery notes of the article's items that count; and `Bulk` the usable bulk in the bulk unit. `Aufgaben` lists every matching planned or running task, running first, then by number, with its number linking to it, its state and its expected end, today plus its remaining synthesis time, marked `verspätet` (`late`) when its slack is below zero. `Maßnahmen` gives each that applies:

- `Abfüllen <size>` (`Fill <size>`), for each item whose runway on hand is below `buffer_days` and of whose containers the open lots would fill at least one, linking to its filling form;
- `Bulk prüfen` (`Check bulk`), linking to the bulk list, when an open lot of the article does not convert;
- `Synthese planen` (`Plan synthesis`), linking for a signed-in user to `/lab/tasks/new/?substance=<key>`, the key of the article's substance, when the priority is high or medium, no matching task is planned or running, and every open lot of the article converts, since a lot that does not may hold enough.

The line above the table states the parameters in force.

#### Scenario: Actions
- **WHEN** on 2026-11-04 with the default parameters three articles of one 1 mg item each, every item with twelve quarters of 9 in the quarterly model and no tasks, exist: the first with 1 container and a lot of 20 mg, the second with 10 containers and only a lot in µmol, its substance without molar mass, the third with 10 containers and no lot
- **THEN** the first is listed, though its priority is low, with `Abfüllen 1 mg`; the second shows check bulk and not plan synthesis; the third shows plan synthesis linking to the new-task form with its substance's key

#### Scenario: Created task matches its article
- **WHEN** a signed-in user follows an article's plan-synthesis link and saves the form
- **THEN** the article's row lists the new task and no longer offers plan synthesis

#### Scenario: Late synthesis
- **WHEN** a running task's slack is below zero
- **THEN** the row marks the task `verspätet`

### Requirement: Runway
The runway of an item for a stock of `S` containers at a certainty `q` SHALL be the longest number of days `H` whose need at `q` is at most `S`, the same rule holding for `S` zero. In the quarterly model it is `((−z_q σ + √(z_q²σ² + 4μS)) / (2μ))²`, zero for `S` zero; in the order model, the `H` at which `P(demand over H ≤ S)` falls to `q`, to 0.01 days, which for `S` zero is the time within which no order arrives with probability `q`. An item's runway on hand is that of its quantity at `certainty`.

An article's runway uses, for each of its `k` items with demand, the certainty `q_k = 1 − (1 − certainty) / k`, so that by the union bound all of them are covered together with probability at least `certainty`, whatever the relation between their demands. Its bulk unit is µmol when the substance has a molar mass, else the kind of unit, mass or amount of substance, of the article's first item by unit and size among those whose level is neither `dormant` nor `undelivered`. An item converts when its container size converts into that unit; `s_max` is the largest container size, in that unit, among the converting items with demand, and zero when none has demand. Each open lot that converts counts with its amount in that unit minus `s_max`, where positive, so that whatever is counted can be filled in whole containers of any size. The usable bulk is the sum of those amounts. The article's runway is the longest `H` that meets two conditions:

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

#### Scenario: A dormant size does not choose the bulk unit
- **WHEN** with the default parameters an article whose substance has no molar mass has an item of 1 mg, dormant, and an item of 1 µmol with 10 containers and twelve quarters of 9 in the quarterly model, and an open lot of 100 µmol
- **THEN** its bulk unit is µmol, the lot converts, and its runway is that of the µmol item with the lot
