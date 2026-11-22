## ADDED Requirements

### Requirement: Widgets
The item page (end-product-inventory "Item page"), the change history of every record page (Change history), and every page whose spec says it shows its data in widgets SHALL show each widget as a `section.widget`, or, when it is collapsible, a `details.widget`, headed by a title bar holding the widget's title and, where the page gives them, the number of its rows and a short note; the title bar of a collapsible widget is its `summary`. The same kind of data shows in the same kind of widget on every such page. A collapsible widget's content is part of the page whether it is open or closed, and printing the page prints every collapsible widget open.

A table marked `data-sortable` sorts in the browser when a user activates one of its column headers: by that column ascending, then descending on each further activation, alternating. The header of the sorted column carries `aria-sort`, and no other header does. A cell's sort key is its `data-sort` attribute when it has one, otherwise its text; a template gives `data-sort` to every cell whose text is not its value, such as amounts in different units. Keys that read as numbers, with a decimal comma or point and a sign, compare by value; keys that read as dates or times, `DD.MM.YYYY` with an optional `HH:MM`, by their order; other keys by the language's collation, after the numbers and dates. Empty keys and keys reading `–` come last in either direction, and rows of equal key keep their order. Without the script, and until a user sorts it, the table shows the order its page's spec states.

A collapsible widget's open or closed state and a sortable table's sorting are view controls (Form dialogs): when a part of the page is refreshed after a form saved in a dialog, each widget and table that the new part holds under the same `id` keeps them, its rows sorted anew.

#### Scenario: Change history as a collapsible widget
- **WHEN** a test client requests the page of an item whose compartment a signed-in user `KL` changed from `1` to `2` after its creation
- **THEN** the page holds one `details.widget` titled `Änderungen`, holding a table of two rows, newest first: the first naming `KL`, the field `Fach`, `1` and `2`, the second reading `Angelegt`

#### Scenario: Removed step in a task's history
- **WHEN** a test client requests the page of a task one of whose steps was removed
- **THEN** its history widget holds a row with the subject `Stufe <n> entfernt` and an empty change cell

#### Scenario: Sorting keys
- **WHEN** the sorting function of `lab.js` orders the keys `10`, `2`, `–`, `-3,5` and an empty key ascending, and then descending
- **THEN** the order is `-3,5`, `2`, `10`, `–`, the empty key, and then `10`, `2`, `-3,5`, `–`, the empty key

#### Scenario: Dates and text
- **WHEN** the sorting function orders the keys `02.01.2026 09:15`, `Abgabe`, `01.01.2026` and `28.12.2025 23:00` ascending
- **THEN** the order is `28.12.2025 23:00`, `01.01.2026`, `02.01.2026 09:15`, `Abgabe`

#### Scenario: Server order without the script
- **WHEN** a test client requests an item's page
- **THEN** its movements table carries `data-sortable` and an `id`, no header carries `aria-sort`, and its rows are in booking order, newest first
