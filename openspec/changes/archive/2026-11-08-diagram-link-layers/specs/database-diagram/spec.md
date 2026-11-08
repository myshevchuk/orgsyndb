## MODIFIED Requirements

### Requirement: Links between tables
The diagram SHALL draw every foreign key between two boxes as a line from the referencing box to the referenced one, and every link the generator declares that the models do not hold as a dashed line without ends. Each line has one of three kinds:

- `key`: a foreign key to a table other than `accounts_user`;
- `user`: a foreign key to `accounts_user`, drawn in the colour of the `accounts` package;
- `value`: a declared link.

The referencing end of a foreign key shows zero or more, or zero or one for a unique foreign key; the referenced end shows exactly one, or zero or one when the column is nullable. A line whose delete rule is not `PROTECT` carries that rule, `cascade` or `set null`. The key mark of a foreign key takes the colour of the package of the table it references. The declared links are:

- from `inventory_lot.article_number` to `inventory_item.article_number`: a lot belongs to the item of the same inventory and article number;
- from `tasks_task.product` to `inventory_item.article_number`: a task belongs to an article when its product equals the article number regardless of case, or names the same compound of the collection index;
- from `tasks_task.batch` to `inventory_lot.batch`: a lot belongs to a task when the two share a batch and the task's product matches the lot's article number;
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
- **THEN** lines of kind `value` run from `tasks_task.product` to `inventory_item.article_number`, from `tasks_task.batch` to `inventory_lot.batch`, from `tasks_counter.name` to `tasks_task.number` and from `inventory_lot.article_number` to `inventory_item.article_number`, each with a tooltip saying how it matches

#### Scenario: Line ends
- **WHEN** a test generates the diagram
- **THEN** the line of `inventory_movement.delivery_note_id` has zero or more at `inventory_movement` and zero or one at `inventory_deliverynote`, that of `inventory_movement.bulk_movement_id` zero or one at both ends, and that of `inventory_deliveryline.item_id` zero or more and exactly one

#### Scenario: A declared link to a missing column
- **WHEN** a unit test generates the diagram with a declared link naming a column the table does not have
- **THEN** generation raises an error naming the table and the column

### Requirement: Arrangement
The generator SHALL place the boxes by a hand-kept grid of bands, top to bottom, each a row of slots, left to right; a slot is empty or holds one or more tables, placed one under another in the order the slot names them. All boxes have one width, the smallest that fits the longest header and row of any table by an estimate of their text. Between two columns lies a gap, and below each band a corridor, which hold no box. A reference is routed by the first rule that fits, whichever of the two tables lies left, right, above or below:

- **Loop.** The referenced table is the referencing one: from its side at the row of the foreign key out, down below the box, and back up into its bottom.
- **Elbow.** The referenced table lies in the next column, in any band: from the side of the referencing box that faces it, at the row of the foreign key, out to a vertical in the gap between the two columns, and to the facing side of the referenced box at the row of its primary key.
- **Vertical.** The referenced table lies in the same column with no box between the two: a straight vertical line from the referencing box's bottom to the referenced box's top, or from its top to the bottom.
- **Under.** The referenced table lies in the same band two or more columns away: down from the referencing box's bottom to a horizontal below that box and every box of the columns between, and along it to the facing side of the referenced box. The rule fits only when the horizontal meets that side and the line crosses no box.
- **Channel.** Any other reference: from the side of the referencing box that faces the referenced one, or its right side when both lie in one column and its left side in the last column, along the row of the foreign key into the gap beside it; along that gap to a corridor; along the corridor to the gap beside the referenced box on the side that faces the referencing one; and along that gap to the referenced box at the row of its primary key. When the two gaps are the same, the line stays in it and uses no corridor. The corridor is the one below the band when both tables lie in one band, and otherwise the one beside the referencing box's band towards the referenced box's band.

A declared link is routed the same way, from and to the rows of the columns it names. Lines whose verticals share a gap, or a column, over overlapping heights get distinct horizontal positions, 12 units apart in a gap; lines whose horizontals share a corridor over overlapping gaps get distinct heights 10 units apart. A gap is 66 units wide and 12 wider for each further position it holds; a corridor is 70 units high and 10 higher for each further height it holds. Generation SHALL fail with a message naming the problem when the grid misses a table, names a table that does not exist or names one twice, or when a line would cross a box other than its own two, naming the reference and the box.

#### Scenario: Routing rules
- **WHEN** a unit test arranges a band holding `a`, `e` and `d` and a band below holding `c` and `b`, where `a` has foreign keys to `b`, `c`, `d` and itself and `d` is taller than `a`
- **THEN** the line to `b` runs from the right side of `a` at the row of `b_id` through the gap to the left side of `b` at the row of `id`; the line to `c` is a vertical from the bottom of `a` to the top of `c`; the line to `d` leaves the bottom of `a`, runs below `e` and ends on the left side of `d`; the line to `a` starts on its right side at the row of `a_id` and ends on its bottom
- **AND** two foreign keys from one table to its neighbour in the next column get elbows with distinct verticals

#### Scenario: Channel between bands
- **WHEN** a unit test arranges a band holding `p` and `q` and a band below holding `r`, `s` and `t`, where `t` has a foreign key to `p`
- **THEN** the line leaves the left side of `t` at the row of `p_id`, runs up the gap between `s` and `t`, along the corridor between the bands, up the gap between `p` and `q`, and ends on the right side of `p` at the row of `id`, crossing no box

#### Scenario: Channel within a column
- **WHEN** a unit test arranges `a`, `b` and `c` in one column of three bands, beside a column holding `d`, where `a` has a foreign key to `c`
- **THEN** the line leaves the right side of `a`, runs down the gap beside the column and ends on the right side of `c`, using no corridor

#### Scenario: Channel in place of a crossing line
- **WHEN** a unit test arranges a band holding `a` with `s` stacked below it, a tall `b` and a taller `d`, where `a` has a foreign key to `d`
- **THEN** the line is routed by the channel rule and crosses no box

#### Scenario: Lanes and room
- **WHEN** a unit test routes two channel lines through the same corridor over overlapping gaps, and adds lines to one gap
- **THEN** the two lines run through the corridor at heights 10 apart, the corridor is 10 units higher than with one line, and the gap is 12 units wider for each further line it holds

#### Scenario: Refused arrangements
- **WHEN** a unit test arranges a grid that misses a table; one that names an unknown table; and one that names a table twice
- **THEN** each raises an error naming the table

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
- **THEN** the constraints name `inventory_item_identity` with `inventory, article_number, size, unit`, `inventory_item_size_positive` with `size > 0`, `inventory_entered_quarter` with `quarter >= 1 AND quarter <= 4`, and the note that rows with `article_number` null never conflict under `inventory_item_identity`; and the history tables name `inventory_historicalitem` without `quantity`
