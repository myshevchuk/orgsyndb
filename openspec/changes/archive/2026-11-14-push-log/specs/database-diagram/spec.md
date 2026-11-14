## MODIFIED Requirements

### Requirement: Links between tables
The diagram SHALL draw every foreign key between two boxes as a line from the referencing box to the referenced one, and every link the generator declares that the models do not hold as a dashed line without ends. Each line has one of three kinds:

- `key`: a foreign key to a table other than `accounts_user`;
- `user`: a foreign key to `accounts_user`, drawn in the colour of the `accounts` package;
- `value`: a declared link.

The referencing end of a foreign key shows zero or more, or zero or one for a unique foreign key; the referenced end shows exactly one, or zero or one when the column is nullable. A line whose delete rule is not `PROTECT` carries that rule, `cascade` or `set null`. The key mark of a foreign key takes the colour of the package of the table it references. The declared links are:

- from `tasks_task.batch` to `inventory_lot.batch`: a lot belongs to a task when the two share a batch and the task's substance is the lot's;
- from `tasks_counter.name` to `tasks_task.number`: the counter `task` issues the task numbers.

A line's tooltip names its two columns and, for a foreign key, its delete rule, for a declared link, how it matches. A declared link's short label is drawn above its longest horizontal segment when the segment is long enough to hold it. Each history table's layout is drawn once, as a dashed box headed `‹app›_historical‹model›` and marked with the number of history tables: the columns of one history table, its tracked columns other than `id` given as one row.

#### Scenario: Links of an entered consumption
- **WHEN** a test generates the diagram
- **THEN** a line of kind `key` runs from `inventory_enteredconsumption` to `inventory_item` and carries `cascade`, a line of kind `user` runs from its `entered_by_id` to `accounts_user`, and the key mark of `entered_by_id` has the accounts colour

#### Scenario: Links to people
- **WHEN** a test generates the diagram
- **THEN** there is one line of kind `user` for each of `inventory_deliverynote.created_by_id`, `inventory_movement.user_id`, `inventory_lotmovement.user_id`, `inventory_enteredconsumption.entered_by_id`, `tasks_task.assignee_id`, `tasks_task.created_by_id`, `collection_procedureauthor.user_id`, `collection_issuedid.user_id`, `collection_import.pushed_by_id`, `accounts_accesstoken.user_id`, `journal_notebook.user_id` and the history box's `history_user_id`, the last carrying `set null`, and no line of another kind ends at `accounts_user`

#### Scenario: Links of a task
- **WHEN** a test generates the diagram
- **THEN** lines of kind `value` run from `tasks_task.batch` to `inventory_lot.batch` and from `tasks_counter.name` to `tasks_task.number`, each with a tooltip saying how it matches, and no other line of kind `value` is drawn

#### Scenario: Links to the registry
- **WHEN** a test generates the diagram
- **THEN** lines of kind `key` run from `tasks_task.substance_id`, `inventory_lot.substance_id` and `inventory_article.substance_id` to `registry_substance`, from `inventory_item.article_id` to `inventory_article`, from `registry_substance.group_id` to `vocabulary_group`, and from `registry_substanceclass` to `registry_substance` and `vocabulary_chemicalclass`; the key mark of `inventory_article.substance_id` has the colour of the `registry` package, and the boxes of the `registry` and `vocabulary` packages each have a colour of their own

#### Scenario: Line ends
- **WHEN** a test generates the diagram
- **THEN** the line of `inventory_movement.delivery_note_id` has zero or more at `inventory_movement` and zero or one at `inventory_deliverynote`, that of `inventory_movement.bulk_movement_id` zero or one at both ends, and that of `inventory_deliveryline.item_id` zero or more and exactly one

#### Scenario: A declared link to a missing column
- **WHEN** a unit test generates the diagram with a declared link naming a column the table does not have
- **THEN** generation raises an error naming the table and the column
