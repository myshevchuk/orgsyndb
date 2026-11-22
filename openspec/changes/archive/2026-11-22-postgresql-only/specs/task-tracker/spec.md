## MODIFIED Requirements

### Requirement: Task numbers
A task's number SHALL be `T-` followed by a counter of at least three digits, zero-padded: `T-001`, `T-099`, `T-1000`. A counter row, incremented by one atomic update in the transaction that creates the task and read back in it, gives the next value, so tasks created at the same time get different numbers and a number is never given twice, even after its task was deleted. A task's page is `/lab/tasks/<number>/`; an unknown number answers 404.

#### Scenario: Numbers after a deletion
- **WHEN** a test creates three tasks, deletes `T-003` and creates another
- **THEN** the new task is `T-004`
