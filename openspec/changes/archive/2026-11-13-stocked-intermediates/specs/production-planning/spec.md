## ADDED Requirements

### Requirement: Starting from stock
Planning SHALL propose, for an article whose row offers a synthesis (Planning list), each sequence of the collection that is not withdrawn and whose target is the article's substance, in order of ID, with the step to start at: the last step `k`, from 2, such that the intermediate of step `k - 1` (synthesis-sequences "Sequence continuity"), read from the entries the collection's sequence steps name, has an open lot, a lot whose amount is above zero, whatever its source; step 1 when no step has one. The proposal names that intermediate. It reserves nothing; whoever creates the task confirms or changes the step (task-tracker "Task forms").

#### Scenario: A stocked intermediate skips a step
- **WHEN** the demo data set is written, its planned task of `SEQ-0001` is cancelled, and a signed-in client requests `/lab/planning/`
- **THEN** the row of `CH-0010` offers `Synthese planen über SEQ-0001 ab Stufe 2, Salicylsäure vorrätig`, linking to `/lab/tasks/new/?substance=acetylsalicylic-acid&sequence=SEQ-0001&start_step=2`

#### Scenario: Nothing in stock
- **WHEN** the same test then sets the amount of every salicylic-acid lot to zero and requests the list again
- **THEN** the row offers `Synthese planen über SEQ-0001`, linking to `/lab/tasks/new/?substance=acetylsalicylic-acid&sequence=SEQ-0001&start_step=1`

## MODIFIED Requirements

### Requirement: Planning list
`/lab/planning/` SHALL list the articles with a forecast whose priority is high or medium or for which an action is due, and with `all=1` every article with a forecast, ordered by slack, smallest first, then by article number. The table has the columns `Artikelnr.`, `Name`, `Gebinde`, `Bedarf/Jahr`, `Letzte Lieferung`, `Bulk`, `Reichweite`, `Synthesedauer`, `Spätester Start`, `Priorität`, `Aufgaben` and `Maßnahmen` (`Article no.`, `Name`, `Containers`, `Demand per year`, `Last delivery`, `Bulk`, `Runway`, `Synthesis time`, `Latest start`, `Priority`, `Tasks`, `Actions`). `Name` is the article's name. `Gebinde` lists each item, in that order, with its size, quantity with its level, and runway on hand; `Bedarf/Jahr` each item's demand per year in containers, rounded half up to one place, in the same order; `Letzte Lieferung` the latest date of the delivery notes of the article's items that count; and `Bulk` the usable bulk in the bulk unit. `Aufgaben` lists every matching planned or running task, running first, then by number, with its number linking to it, its state and its expected end, today plus its remaining synthesis time, marked `verspätet` (`late`) when its slack is below zero. `Maßnahmen` gives each that applies:

- `Abfüllen <size>` (`Fill <size>`), for each item whose runway on hand is below `buffer_days` and of whose containers the open lots would fill at least one, linking to its filling form;
- `Bulk prüfen` (`Check bulk`), linking to the bulk list, when an open lot of the article does not convert;
- a synthesis, when the priority is high or medium, no matching task is planned or running, and every open lot of the article converts, since a lot that does not may hold enough: for each sequence that Starting from stock proposes, `Synthese planen über <ID>` (`Plan synthesis via <ID>`), followed when it starts at a later step `k` by ` ab Stufe <k>, <name> vorrätig` (` from step <k>, <name> in stock`), the name of the substance in stock, linking for a signed-in user to `/lab/tasks/new/?substance=<key>&sequence=<ID>&start_step=<k>`, `<key>` the key of the article's substance; and when it proposes none, `Synthese planen` (`Plan synthesis`), linking for a signed-in user to `/lab/tasks/new/?substance=<key>`.

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
