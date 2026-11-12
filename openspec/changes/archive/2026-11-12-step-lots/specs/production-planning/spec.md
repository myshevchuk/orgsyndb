## MODIFIED Requirements

### Requirement: Synthesis time
An article's synthesis time `L` SHALL be the longest duration in days, end date minus start date and at least 1, among the last three ended tasks that match it and are neither cancelled nor failed, ordered by end date, then start date, then number; with fewer than three such tasks, the longest of their durations and `default_synthesis_days`. Its basis shows as `Vorgabe` (`default`), `die letzte Synthese` (`the last synthesis`) when one synthesis decided it, or `längste der letzten <k> Synthesen` (`longest of the last <k> syntheses`). A planned task's remaining synthesis time is `L`; a running task's is `L` minus the days since its start, at least zero.

#### Scenario: Longest of the last three
- **WHEN** four ended tasks match an article, taking 90, 20, 30 and 40 days in the order of their end dates
- **THEN** its synthesis time is 40 days

#### Scenario: The default until three exist
- **WHEN** one ended task of 10 days matches an article
- **THEN** its synthesis time is 21 days, the default

#### Scenario: A failed task does not count
- **WHEN** the last ended task matching an article failed after 40 days, and the three before it took 10, 12 and 15 days
- **THEN** the article's synthesis time is 15 days

### Requirement: Batches between tasks and bulk
A task and a bulk lot SHALL belong to each other when their batches are equal and not empty and the task's substance is the lot's. The task page and the lot page link the records that belong to theirs, and a lot made by a step of the task belongs to it too; each step of a planned or running task offers to record a lot it made, as `task-tracker` and `end-product-inventory` state.

#### Scenario: Bulk from a task's step
- **WHEN** a signed-in user opens `Los erfassen` on the last step of a running task of `cinnamic-acid` with the batch `B-2026-031`, and saves the form with an amount
- **THEN** a lot of `cinnamic-acid`, made in the lab by that step, with the batch `B-2026-031` exists, and the task's page and the lot's page link to each other

#### Scenario: Same batch, other substance
- **WHEN** a lot of `new-compound-7` and a task of `cinnamic-acid` both have the batch `B-001`
- **THEN** neither page links the other
