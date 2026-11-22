## ADDED Requirements

### Requirement: Batches of tasks
A batch made by a step of a task (end-product-inventory "Batches") SHALL belong to that task, and to no other. The task page lists, under each step, the batches it made, and the batch page links the step and its task; each step of a planned or running task offers to record a batch it made, as `task-tracker` and `end-product-inventory` state.

#### Scenario: A batch from a task's step
- **WHEN** a signed-in user opens `Charge erfassen` on the last step of a running task of `cinnamic-acid`, and saves the form with the number `KL0412` and the amount `2` g
- **THEN** a batch `KL0412` of `cinnamic-acid`, made in the lab by that step, exists with its flask holding `2` g, and the task's page and the batch's page link to each other

#### Scenario: A batch without a step
- **WHEN** a signed-in user records a made batch of `cinnamic-acid` without a step while a task of `cinnamic-acid` is running
- **THEN** neither the task's page nor the batch's page links the other

## MODIFIED Requirements

### Requirement: Runway
The runway of an item for a stock of `S` containers at a certainty `q` SHALL be the longest number of days `H` whose need at `q` is at most `S`, the same rule holding for `S` zero. In the quarterly model it is `((−z_q σ + √(z_q²σ² + 4μS)) / (2μ))²`, zero for `S` zero; in the order model, the `H` at which `P(demand over H ≤ S)` falls to `q`, to 0.01 days, which for `S` zero is the time within which no order arrives with probability `q`. An item's runway on hand is that of its quantity at `certainty`.

An article's runway uses, for each of its `k` items with demand, the certainty `q_k = 1 − (1 − certainty) / k`, so that by the union bound all of them are covered together with probability at least `certainty`, whatever the relation between their demands. Its bulk unit is µmol when the substance has a molar mass, else the kind of unit, mass or amount of substance, of the article's first item by unit and size among those whose level is neither `dormant` nor `undelivered`. An item converts when its container size converts into that unit; `s_max` is the largest container size, in that unit, among the converting items with demand, and zero when none has demand. Each open vessel of the article's substance that converts counts with its amount in that unit minus `s_max`, where positive, so that whatever is counted can be filled in whole containers of any size. The usable bulk is the sum of those amounts. The article's runway is the longest `H` that meets two conditions:

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
- **WHEN** with the default parameters an article has items of 10 mg and 20 mg, each without containers and with twelve quarters of 9 in the quarterly model, and one open vessel of 360 mg
- **THEN** each item is planned at a certainty of 0.975, the usable bulk is 340 mg, and the article's runway is 62 days, where giving each size the whole vessel at 0.95 would claim 277 and 124

#### Scenario: Vessels too small to fill
- **WHEN** an article's only item, of 10 mg, has 10 containers and two open vessels of 6 mg each
- **THEN** its usable bulk is zero and its runway is its runway on hand

#### Scenario: A dormant size does not choose the bulk unit
- **WHEN** with the default parameters an article whose substance has no molar mass has an item of 1 mg, dormant, and an item of 1 µmol with 10 containers and twelve quarters of 9 in the quarterly model, and an open vessel of 100 µmol
- **THEN** its bulk unit is µmol, the vessel converts, and its runway is that of the µmol item with the vessel

### Requirement: Planning list
`/lab/planning/` SHALL list the articles with a forecast whose priority is high or medium or for which an action is due, and with `all=1` every article with a forecast, ordered by slack, smallest first, then by article number. The table has the columns `Artikelnr.`, `Name`, `Gebinde`, `Bedarf/Jahr`, `Letzte Lieferung`, `Bulk`, `Reichweite`, `Synthesedauer`, `Spätester Start`, `Priorität`, `Aufgaben` and `Maßnahmen` (`Article no.`, `Name`, `Containers`, `Demand per year`, `Last delivery`, `Bulk`, `Runway`, `Synthesis time`, `Latest start`, `Priority`, `Tasks`, `Actions`). `Name` is the article's name. `Gebinde` lists each item, in that order, with its size, quantity with its level, and runway on hand; `Bedarf/Jahr` each item's demand per year in containers, rounded half up to one place, in the same order; `Letzte Lieferung` the latest date of the delivery notes of the article's items that count; and `Bulk` the usable bulk in the bulk unit. `Aufgaben` lists every matching planned or running task, running first, then by number, with its number linking to it, its state and its expected end, today plus its remaining synthesis time, marked `verspätet` (`late`) when its slack is below zero. `Maßnahmen` gives each that applies:

- `Abfüllen <size>` (`Fill <size>`), for each item whose runway on hand is below `buffer_days` and of whose containers the open vessels of its substance would fill at least one, linking to its filling form;
- `Bulk prüfen` (`Check bulk`), linking to the vessel list, when an open vessel of the article's substance does not convert;
- a synthesis, when the priority is high or medium, no matching task is planned or running, and every open vessel of the article's substance converts, since a vessel that does not may hold enough: for each sequence that Starting from stock proposes, `Synthese planen über <ID>` (`Plan synthesis via <ID>`), followed when it starts at a later step `k` by ` ab Stufe <k>, <name> vorrätig` (` from step <k>, <name> in stock`), the name of the substance in stock, linking for a signed-in user to `/lab/tasks/new/?substance=<key>&sequence=<ID>&start_step=<k>`, `<key>` the key of the article's substance; and when it proposes none, `Synthese planen` (`Plan synthesis`), linking for a signed-in user to `/lab/tasks/new/?substance=<key>`.

The line above the table states the parameters in force.

#### Scenario: Actions
- **WHEN** on 2026-11-04 with the default parameters three articles of one 1 mg item each, every item with twelve quarters of 9 in the quarterly model and no tasks, exist: the first with 1 container and a vessel of 20 mg, the second with 10 containers and only a vessel in µmol, its substance without molar mass, the third with 10 containers and no vessel
- **THEN** the first is listed, though its priority is low, with `Abfüllen 1 mg`; the second shows check bulk and not plan synthesis; the third shows plan synthesis linking to the new-task form with its substance's key

#### Scenario: Created task matches its article
- **WHEN** a signed-in user follows an article's plan-synthesis link and saves the form
- **THEN** the article's row lists the new task and no longer offers plan synthesis

#### Scenario: Late synthesis
- **WHEN** a running task's slack is below zero
- **THEN** the row marks the task `verspätet`

### Requirement: Starting from stock
Planning SHALL propose, for an article whose row offers a synthesis (Planning list), each sequence of the collection that is not withdrawn and whose target is the article's substance, in order of ID, with the step to start at: the last step `k`, from 2, such that the intermediate of step `k - 1` (synthesis-sequences "Sequence continuity"), read from the entries the collection's sequence steps name, has an open vessel, a vessel holding an amount above zero, whatever its kind or its batch's source; step 1 when no step has one. The proposal names that intermediate. It reserves nothing; whoever creates the task confirms or changes the step (task-tracker "Task forms").

#### Scenario: A stocked intermediate skips a step
- **WHEN** the demo data set is written, its planned task of `SEQ-0001` is cancelled, and a signed-in client requests `/lab/planning/`
- **THEN** the row of `CH-0010` offers `Synthese planen über SEQ-0001 ab Stufe 2, Salicylsäure vorrätig`, linking to `/lab/tasks/new/?substance=acetylsalicylic-acid&sequence=SEQ-0001&start_step=2`

#### Scenario: Nothing in stock
- **WHEN** the same test then sets the amount of every vessel of `salicylic-acid` to zero and requests the list again
- **THEN** the row offers `Synthese planen über SEQ-0001`, linking to `/lab/tasks/new/?substance=acetylsalicylic-acid&sequence=SEQ-0001&start_step=1`

## REMOVED Requirements

### Requirement: Batches between tasks and bulk
**Reason**: A task and a lot were matched by equal batch text. A batch now names the step that made it.
**Migration**: "Batches of tasks".
