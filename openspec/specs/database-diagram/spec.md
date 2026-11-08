# database-diagram Specification

## Purpose
Draw the lab application's tables as a standalone page generated from its models: the boxes, columns, keys and links of the diagram, their arrangement on a hand-kept grid, the page's lists of constraints, delete rules, history tables, docstrings and Django's tables, and the command that writes the page and checks that it is current.
## Requirements
### Requirement: Diagram command
`manage.py schema_diagram` SHALL write the table diagram to `webapp/docs/database-schema.html`, creating `webapp/docs/` when it does not exist, and print the path it wrote; `--output <path>` names another file in its place. With `--check` it writes nothing: it exits 0 when the file holds exactly the text the command would write, and otherwise exits 1 with a message naming the file and the command that regenerates it. The text depends only on the models and the generator: it carries no date, commit or path of the machine, and it is the same whichever database the settings name. The suite runs the check against the committed file, so a change of the models that leaves the diagram stale fails the suite.

#### Scenario: Writing and checking
- **WHEN** a test runs `schema_diagram` with the output path pointed into an empty temporary directory, then `schema_diagram --check` on that path, then changes one byte of the file and checks again, then removes it and checks again
- **THEN** the first run creates the file and prints its path, the first check exits 0, and the second and third exit 1 naming the file and `schema_diagram`

#### Scenario: The committed diagram is current
- **WHEN** the suite runs `schema_diagram --check` against `webapp/docs/database-schema.html`, on SQLite and on PostgreSQL
- **THEN** it exits 0

### Requirement: Tables and columns
The diagram SHALL show one box per table of the application's own models, the models the packages under `webapp/` declare, and no other: not the history tables of django-simple-history, not the many-to-many tables Django creates for a model of those packages, and not the models of Django or other dependencies. A box is headed by the table's name and lists the table's columns in the order the model declares its fields, which may differ from the order of the columns in a database the migrations built. Each row shows:

- the column name;
- its type as PostgreSQL creates it, with `timestamp with time zone` written `timestamptz`, `double precision` written `float8`, and no spaces in type arguments, such as `numeric(10,3)`; and `?` after the type when the column is nullable;
- a key mark: `PK` for the primary key, `1:1` for a unique foreign key, `FK` for any other foreign key, `UQ` for another unique column, and none otherwise.

A row's tooltip names the column, its type and nullability, the table and column a foreign key references, and the notes the model gives: the stored values of its choices; the bounds of the minimum and maximum validators the field declares, as `from <a> to <b>`, `at least <a>` or `at most <b>`, leaving out the range Django derives from the database; a non-callable default, as `default <value>`; `CHECK >= 0` when the column carries that check; its help text; and `not in history` when the table's history leaves the column out. A box whose table keeps a history carries the mark `HISTORY`. A box's tooltip is the first paragraph of the model's docstring. Every text taken from the models is rendered in English, whatever language is active.

#### Scenario: An item's columns
- **WHEN** a test generates the diagram
- **THEN** the box `inventory_item` lists `id`, `inventory`, `article_number`, `name`, `category`, `size`, `unit`, `quantity`, `note`, `status`, `stocked_on`, `compartment` and `box`, in this order, with `id` marked `PK` and typed `bigint`, `article_number` typed `varchar(30)?`, `size` typed `numeric(10,3)`, the box marked `HISTORY`, the tooltip of `status` naming `active`, `not_needed` and `discontinued`, and the tooltip of `quantity` saying `not in history` and `CHECK >= 0` and naming no upper bound

#### Scenario: Keys of a movement
- **WHEN** a test generates the diagram
- **THEN** in the box `inventory_movement`, `item_id` is marked `FK` and typed `bigint`, `delivery_note_id` is marked `FK` and typed `bigint?`, `bulk_movement_id` and `reverses_id` are marked `1:1`, and `booked_at` is typed `timestamptz`

#### Scenario: Notes in English
- **WHEN** a test generates the diagram with German active
- **THEN** the tooltip of `planning_parameters.certainty` holds `from 0.5 to 0.999`, `default 0.95` and `The probability with which a stock is to last its runway.`, and that of `inventory_enteredconsumption.quarter` holds `from 1 to 4`

#### Scenario: Only the application's tables
- **WHEN** a test generates the diagram
- **THEN** its boxes are exactly `accounts_user`, `inventory_item`, `inventory_movement`, `inventory_deliverynote`, `inventory_deliveryline`, `inventory_lot`, `inventory_lotmovement`, `inventory_enteredconsumption`, `tasks_task`, `tasks_counter`, `planning_parameters`, `demo_demomark` and the box of the history tables
- **AND** Django's tables list `accounts_user_groups`, `accounts_user_user_permissions`, `auth_group` and `django_session`, and no table that has a box or is a history table

### Requirement: Links between tables
The diagram SHALL draw each foreign key between two boxes as a line from the referencing box to the referenced one, except foreign keys to `accounts_user`. The referencing end shows zero or more, or zero or one for a unique foreign key; the referenced end shows exactly one, or zero or one when the column is nullable. A line whose delete rule is not `PROTECT` carries that rule, `cascade` or `set null`. The key mark of a foreign key to `accounts_user` takes the colour of the `accounts` package instead of a line. The diagram also draws, as dashed lines without ends, the links that the generator declares and the models do not hold: from `inventory_lot.article_number` to `inventory_item.article_number`, labelled as matched by inventory and article number, and from `tasks_counter.name` to `tasks_task.number`. Each history table's layout is drawn once, as a dashed box headed `‹app›_historical‹model›` and marked with the number of history tables: the columns of one history table, its tracked columns other than `id` given as one row.

#### Scenario: Links of an entered consumption
- **WHEN** a test generates the diagram
- **THEN** a line runs from `inventory_enteredconsumption` to `inventory_item` and carries `cascade`, no line ends at `accounts_user`, and the key mark of `entered_by_id` has the accounts colour

#### Scenario: Line ends
- **WHEN** a test generates the diagram
- **THEN** the line of `inventory_movement.delivery_note_id` has zero or more at `inventory_movement` and zero or one at `inventory_deliverynote`, that of `inventory_movement.bulk_movement_id` zero or one at both ends, and that of `inventory_deliveryline.item_id` zero or more and exactly one

#### Scenario: A declared link to a missing column
- **WHEN** a unit test generates the diagram with a declared link naming a column the table does not have
- **THEN** generation raises an error naming the table and the column

### Requirement: Arrangement
The generator SHALL place the boxes by a hand-kept grid of bands, top to bottom, each a row of slots, left to right; a slot is empty or holds one or more tables, placed one under another in the order the slot names them. All boxes have one width, the smallest that fits the longest header and row of any table by an estimate of their text. Each band starts below the lowest box of the band above. A reference is routed by the first rule that fits, whichever of the two tables lies left, right, above or below:

- **Elbow.** The referenced table lies in the next column, in any band: from the side of the referencing box that faces it, at the row of the foreign key, out to a vertical in the gap between the two columns, and to the facing side of the referenced box at the row of its primary key.
- **Vertical.** The referenced table lies in the same column with no box between the two: a straight vertical line from the referencing box's bottom to the referenced box's top, or from its top to the bottom.
- **Under.** The referenced table lies in the same band two or more columns away: down from the referencing box's bottom to a horizontal below that box and every box of the columns between, and along it to the facing side of the referenced box. The horizontal must meet that side; otherwise the reference fits no rule.
- **Loop.** The referenced table is the referencing one: from its side at the row of the foreign key out, down below the box, and back up into its bottom.

A declared link is routed the same way, from and to the rows of the columns it names. Lines whose verticals run through the same gap, or through the same column, over overlapping heights get distinct horizontal positions. Generation SHALL fail with a message naming the problem when the grid misses a table, names a table that does not exist or names one twice, when a reference fits none of the rules, naming the table and column, or when a line would cross a box other than its own two, naming the reference and the box.

#### Scenario: Routing rules
- **WHEN** a unit test arranges a band holding `a`, `e` and `d` and a band below holding `c` and `b`, where `a` has foreign keys to `b`, `c`, `d` and itself and `d` is taller than `a`
- **THEN** the line to `b` runs from the right side of `a` at the row of `b_id` through the gap to the left side of `b` at the row of `id`; the line to `c` is a vertical from the bottom of `a` to the top of `c`; the line to `d` leaves the bottom of `a`, runs below `e` and ends on the left side of `d`; the line to `a` starts on its right side at the row of `a_id` and ends on its bottom
- **AND** two foreign keys from one table to its neighbour in the next column get elbows with distinct verticals

#### Scenario: Refused arrangements
- **WHEN** a unit test arranges a grid that misses a table; one that names an unknown table; one that names a table twice; one where a reference goes two bands down in the same column past a box; one where a reference goes to another band two columns away; and one where a reference runs two columns away from a table with another table stacked below it
- **THEN** each raises an error naming the table or the reference, and the last also names the table its line would cross

### Requirement: Page
`webapp/docs/database-schema.html` SHALL be a standalone HTML document with a doctype, `<html lang="en">`, a UTF-8 charset, a viewport and the `title` `OrgSynDB tables`. It loads nothing from other hosts except one Google Fonts stylesheet, and every face it names has a local fallback. It follows the reader's light or dark colour scheme. Under its `h1` it holds:

- a line counting the application's tables, their packages and the history tables, and a key of each package's colour;
- a legend of the key marks, the line ends, the dashed lines and `?`;
- the diagram, an inline `svg` complete without a script, in a container that scrolls sideways when the window is narrower;
- **Constraints**: each unique constraint, and each check constraint of the model's `Meta`, with its table, its columns or its condition and its name, a condition written as SQL from comparisons by `exact`, `gt`, `gte`, `lt`, `lte` and `isnull` of a field with a literal value or a field, joined by `AND` and `OR` and negated by `NOT`; the columns that carry a `>= 0` check; and, for each unique constraint over a nullable column, the note that rows with that column null never conflict;
- **On delete**: the foreign keys by delete rule;
- **History tables**: each history table and the columns it leaves out;
- **Tables**: each table with its model's docstring;
- **Django's tables**: the tables of the other installed models, many-to-many tables included, by name.

A script adds the highlighting: hovering, focusing or tapping a box shows it, the boxes linked to it, its lines and the rows that link them, and dims the rest; a second tap or `Escape` ends it. The page contains no text in another language.

#### Scenario: A standalone page
- **WHEN** a test reads the generated page
- **THEN** it begins with `<!doctype html>`, has `lang="en"` and the title `OrgSynDB tables`, its only `link` to another host is to `fonts.googleapis.com` and `fonts.gstatic.com`, it has no `script` element with a `src`, and its one `svg` holds every table's name and every column's name

#### Scenario: An unsupported condition
- **WHEN** a unit test renders a condition using the lookup `icontains`
- **THEN** it raises an error naming the lookup, and generation fails in the same way for a model whose check uses it

#### Scenario: Constraint lists
- **WHEN** a test reads the generated page
- **THEN** the constraints name `inventory_item_identity` with `inventory, article_number, size, unit`, `inventory_item_size_positive` with `size > 0`, `inventory_entered_quarter` with `quarter >= 1 AND quarter <= 4`, and the note that rows with `article_number` null never conflict under `inventory_item_identity`; and the history tables name `inventory_historicalitem` without `quantity`

