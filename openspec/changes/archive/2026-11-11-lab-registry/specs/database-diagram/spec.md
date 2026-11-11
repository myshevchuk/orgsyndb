## MODIFIED Requirements

### Requirement: Tables and columns
The diagram SHALL show one box per table of the application's own models, the models the packages under `webapp/` declare, and no other: not the history tables of django-simple-history, not the many-to-many tables Django creates for a model of those packages, and not the models of Django or other dependencies. A box is headed by the table's name and lists the table's columns in the order the model declares its fields, which may differ from the order of the columns in a database the migrations built. Each row shows:

- the column name;
- its type as PostgreSQL creates it, with `timestamp with time zone` written `timestamptz`, `double precision` written `float8`, and no spaces in type arguments, such as `numeric(10,3)`; and `?` after the type when the column is nullable;
- a key mark: `PK` for the primary key, `1:1` for a unique foreign key, `FK` for any other foreign key, `UQ` for another unique column, and none otherwise.

A row's tooltip names the column, its type and nullability, the table and column a foreign key references, and the notes the model gives: the stored values of its choices; the bounds of the minimum and maximum validators the field declares, as `from <a> to <b>`, `at least <a>` or `at most <b>`, leaving out the range Django derives from the database; a non-callable default, as `default <value>`; `CHECK >= 0` when the column carries that check; its help text; and `not in history` when the table's history leaves the column out. A box whose table keeps a history carries the mark `HISTORY`. A box's tooltip is the first paragraph of the model's docstring. Every text taken from the models is rendered in English, whatever language is active.

#### Scenario: An item's columns
- **WHEN** a test generates the diagram
- **THEN** the box `inventory_item` lists `id`, `article_id`, `size`, `unit`, `quantity`, `note`, `status`, `stocked_on`, `compartment` and `box`, in this order, with `id` marked `PK` and typed `bigint`, `article_id` marked `FK` and typed `bigint`, `size` typed `numeric(10,3)`, the box marked `HISTORY`, the tooltip of `status` naming `active`, `not_needed` and `discontinued`, and the tooltip of `quantity` saying `not in history` and `CHECK >= 0` and naming no upper bound

#### Scenario: Keys of a movement
- **WHEN** a test generates the diagram
- **THEN** in the box `inventory_movement`, `item_id` is marked `FK` and typed `bigint`, `delivery_note_id` is marked `FK` and typed `bigint?`, `bulk_movement_id` and `reverses_id` are marked `1:1`, and `booked_at` is typed `timestamptz`

#### Scenario: Notes in English
- **WHEN** a test generates the diagram with German active
- **THEN** the tooltip of `planning_parameters.certainty` holds `from 0.5 to 0.999`, `default 0.95` and `The probability with which a stock is to last its runway.`, and that of `inventory_enteredconsumption.quarter` holds `from 1 to 4`

#### Scenario: Only the application's tables
- **WHEN** a test generates the diagram
- **THEN** its boxes are exactly `accounts_user`, `registry_substance`, `registry_substanceclass`, `vocabulary_chemicalclass`, `vocabulary_group`, `vocabulary_project`, `vocabulary_reactiontype`, `inventory_article`, `inventory_item`, `inventory_movement`, `inventory_deliverynote`, `inventory_deliveryline`, `inventory_lot`, `inventory_lotmovement`, `inventory_enteredconsumption`, `tasks_task`, `tasks_counter`, `planning_parameters`, `demo_demomark` and the box of the history tables

#### Scenario: An article's key
- **WHEN** a test generates the diagram
- **THEN** in the box `inventory_article`, `substance_id` is marked `PK` and typed `bigint`, and `article_number` is marked `UQ` and typed `varchar(30)?`
- **AND** Django's tables list `accounts_user_groups`, `accounts_user_user_permissions`, `auth_group` and `django_session`, and no table that has a box or is a history table

### Requirement: Page
`webapp/docs/database-schema.html` SHALL be a standalone HTML document with a doctype, `<html lang="en">`, a UTF-8 charset, a viewport and the `title` `OrgSynDB tables`. It loads nothing from other hosts except one Google Fonts stylesheet, and every face it names has a local fallback. It follows the reader's light or dark colour scheme. Under its `h1` it holds:

- a line counting the application's tables, their packages and the history tables, and a key of each package's colour;
- a legend of the key marks, the line ends, the line of a link to `accounts_user`, the dashed lines and `?`;
- three switches, one per kind of line, `Foreign keys`, `To accounts_user` and `Matched by value`, each with the number of lines of its kind; the page hides them when a script cannot run;
- the diagram, an inline `svg` complete without a script, every line shown, in a container that scrolls sideways when the window is narrower;
- **Constraints**: each unique constraint, and each check constraint of the model's `Meta`, with its table, its columns or its condition and its name, a condition written as SQL from comparisons by `exact`, `gt`, `gte`, `lt`, `lte` and `isnull` of a field with a literal value or a field, joined by `AND` and `OR` and negated by `NOT`; the columns that carry a `>= 0` check; and, for each unique constraint over a nullable column, the note that rows with that column null never conflict;
- **On delete**: the foreign keys by delete rule;
- **History tables**: each history table and the columns it leaves out;
- **Tables**: each table with its model's docstring;
- **Django's tables**: the tables of the other installed models, many-to-many tables included, by name.

A script shows the switches and hides the lines of each kind switched off; `Foreign keys` and `Matched by value` start on and `To accounts_user` off. Hovering, focusing or tapping a box shows it, the boxes linked to it, its lines whatever their switches, and the rows that link them, and dims the rest; a second tap or `Escape` ends it. Hovering a row shows the lines that start or end at its column, whatever their switches. The page contains no text in another language.

#### Scenario: A standalone page
- **WHEN** a test reads the generated page
- **THEN** it begins with `<!doctype html>`, has `lang="en"` and the title `OrgSynDB tables`, its only `link` to another host is to `fonts.googleapis.com` and `fonts.gstatic.com`, it has no `script` element with a `src`, and its one `svg` holds every table's name and every column's name

#### Scenario: Switches
- **WHEN** a test reads the generated page
- **THEN** it has a hidden group of three checkboxes for the kinds `key`, `user` and `value`, each labelled with the number of lines of that kind in the `svg`, those for `key` and `value` checked and that for `user` not, and every line of the `svg` carries the class of its kind

#### Scenario: An unsupported condition
- **WHEN** a unit test renders a condition using the lookup `icontains`
- **THEN** it raises an error naming the lookup, and generation fails in the same way for a model whose check uses it

#### Scenario: Constraint lists
- **WHEN** a test reads the generated page
- **THEN** the constraints name `inventory_item_identity` with `article_id, size, unit`, `inventory_item_size_positive` with `size > 0`, `inventory_entered_quarter` with `quarter >= 1 AND quarter <= 4`, `registry_substance_cas_once` with `cas` and its condition, and `registry_substanceclass_once` with `substance_id, chemical_class_id`; and the history tables name `inventory_historicalitem` without `quantity`

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
- **THEN** there is one line of kind `user` for each of `inventory_deliverynote.created_by_id`, `inventory_movement.user_id`, `inventory_lotmovement.user_id`, `inventory_enteredconsumption.entered_by_id`, `tasks_task.assignee_id`, `tasks_task.created_by_id` and the history box's `history_user_id`, the last carrying `set null`, and no line of another kind ends at `accounts_user`

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
