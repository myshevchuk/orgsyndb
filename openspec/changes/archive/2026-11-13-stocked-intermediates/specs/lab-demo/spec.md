## MODIFIED Requirements

### Requirement: Demo tasks and parameters
The data set SHALL hold tasks for the articles of the demo inventory and for its item without an article number, each checked by the task's own validation before every save, as a form's would be, and numbered in the order they were created:

- tasks in each state: planned, running, ended with `report` and `qc_list` on, ended needing follow-up, failed, and cancelled; on `D` the task list's default filter counts at least two planned, three running and two follow-up tasks;
- at least three ended tasks matching `CH-0012`, so that its synthesis time is `längste der letzten 3 Synthesen`;
- tasks of the sequences `SEQ-0001`, of the substance of `CH-0010`, and `SEQ-0002`, of the substance of `CH-0002`, of the data set's import, each with one step per step of its sequence from the one it starts at (task-tracker "Task record"); the first step of an ended task of `SEQ-0001` made a lot of salicylic acid, from which the planned task of `SEQ-0001` starts at its second step; one of them running with the first of its two steps done, which made a lot of its intermediate, and that lot withdrawn in part into its second step;
- one task without an assignee;
- an ended task of `1-phenylethanol`, whose article has no article number, with a batch and its product lot;
- every other ended task that has not failed with a batch and a product lot of that batch, so that each such task lists its lots and each lot its task.

The planning parameters are stored, created with `target_days` 180 more than a year before `D` and changed to 365 since, every other value the default.

#### Scenario: Task list
- **WHEN** the data set is written as of `D` and a test client requests `/lab/tasks/` and `/lab/tasks/?state=all`
- **THEN** the first counts at least 2 planned, 3 running and 2 follow-up tasks, and the second shows each of the states `Geplant`, `In Arbeit`, `Abgeschlossen` and `Verworfen`

#### Scenario: Parameters with a history
- **WHEN** the data set is written and a test reads the stored planning parameters
- **THEN** their `target_days` is 365, every other value is its default, and their history lists a change of `target_days` from 180 to 365

#### Scenario: Ended tasks have their lots
- **WHEN** the data set is written as of `D`
- **THEN** every ended task that has not failed has a batch and a product lot, one task is failed and has no batch, and one lot was made by a task step and has a withdrawal into another step of the same task

#### Scenario: A demo task from stock
- **WHEN** the demo data set is written and a test client requests the page of the planned task of `SEQ-0001`
- **THEN** it shows `SEQ-0001 ab Stufe 2` and one step, of `OSDB-0002`, and an open lot of `salicylic-acid` lists the first step of an ended task of `SEQ-0001` as the step that made it
