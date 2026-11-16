## MODIFIED Requirements

### Requirement: Change history
Every model holding lab records SHALL keep a history with django-simple-history: each creation and change stores a copy of the record with the signed-in user and the time. A value the application derives from the record's other values and keeps as a cache, a substance's structure drawing (lab-registry "Structure images"), is left out of the copy. A record's page shows its history, newest first, each entry with its time, the user's initials and either `Angelegt` (`Created`) or the changed fields, each with its label and old and new values.

#### Scenario: History of a change
- **WHEN** a signed-in user `KL` creates a task and then changes its priority from medium to high
- **THEN** the task's page lists two history entries, the newer naming `KL`, the field `Priorität` and the values `mittel` and `hoch`
