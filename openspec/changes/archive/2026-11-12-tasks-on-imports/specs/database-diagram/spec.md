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
- **THEN** its boxes are exactly `accounts_user`, `registry_substance`, `registry_substanceclass`, `vocabulary_chemicalclass`, `vocabulary_group`, `vocabulary_project`, `vocabulary_reactiontype`, `inventory_article`, `inventory_item`, `inventory_movement`, `inventory_deliverynote`, `inventory_deliveryline`, `inventory_lot`, `inventory_lotmovement`, `inventory_enteredconsumption`, `tasks_task`, `tasks_taskstep`, `tasks_counter`, `collection_import`, `collection_procedure`, `collection_scopeentry`, `collection_entrysubstance`, `collection_sequence`, `collection_step`, `planning_parameters`, `demo_demomark` and the box of the history tables

#### Scenario: An article's key
- **WHEN** a test generates the diagram
- **THEN** in the box `inventory_article`, `substance_id` is marked `PK` and typed `bigint`, and `article_number` is marked `UQ` and typed `varchar(30)?`
- **AND** Django's tables list `accounts_user_groups`, `accounts_user_user_permissions`, `auth_group` and `django_session`, and no table that has a box or is a history table
