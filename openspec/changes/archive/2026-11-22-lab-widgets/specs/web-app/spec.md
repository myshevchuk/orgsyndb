## ADDED Requirements

### Requirement: Widgets
The item page (end-product-inventory "Item page"), the change history of every record page (Change history), and every page whose spec says it shows its data in widgets SHALL show each widget as a `section.widget`, or, when it is collapsible, a `details.widget`, headed by a title bar holding the widget's title and, where the page gives them, a count and a short note; the title bar of a collapsible widget is its `summary`. The history widget is collapsible and closed when the page loads, and its count is the number of its entries. The same kind of data shows in the same kind of widget on every such page. A collapsible widget's content is part of the page whether it is open or closed. Printing the page from a browser prints every collapsible widget open and every sortable table with its column headers, with or without the script.

A table marked `data-sortable` sorts in the browser when a user activates one of its column headers: by that column ascending, then descending on each further activation, alternating. The header of the sorted column carries `aria-sort`, and no other header does. A cell's sort key is its `data-sort` attribute when it has one, otherwise its text; a template gives `data-sort` to every cell whose text is not its value: amounts in different units, and dates and times, whose key is ISO 8601 in every language. A key reads as a number when it is one, with a sign and a decimal comma or point; as a date when it reads `YYYY-MM-DD` or `DD.MM.YYYY`, either with an optional time `HH:MM`; and otherwise as text. Ascending, numbers come first by value, then dates by their order, then text by the language's collation; descending reverses that whole order. Empty keys and keys reading `–` come last in either direction, and rows of equal key keep their order. Without the script, and until a user sorts it, the table shows the order its page's spec states.

A collapsible widget's open or closed state and a sortable table's sorting are view controls (Form dialogs): when a part of the page is refreshed after a form saved in a dialog, each widget and table that the new part holds under the same `id` keeps them, its rows sorted anew, and its headers sort as before.

#### Scenario: Change history as a collapsible widget
- **WHEN** a test client requests the page of an item created with compartment `1` and box `A`, which a signed-in user `KL` then changed, in one save, to compartment `2` and box `B`
- **THEN** the page holds one `details.widget` without `open`, titled `Änderungen` with the count 2, holding a table of three rows, newest first: two of the save naming `KL`, one the field `Fach` with `1` and `2`, the other `Box` with `A` and `B`, and the creation's reading `Angelegt`

#### Scenario: Removed step in a task's history
- **WHEN** a test client requests the page of a task one of whose steps was removed
- **THEN** its history widget holds a row with the subject `Stufe <n> entfernt` and an empty change cell

#### Scenario: Numbers, dates and text
- **WHEN** the sorting function of `lab.js` orders the keys `Abgabe`, `10`, `2026-01-02T09:15`, `–`, `-3,5`, `01.01.2026`, an empty key and `2` ascending, and then descending
- **THEN** the order is `-3,5`, `2`, `10`, `01.01.2026`, `2026-01-02T09:15`, `Abgabe`, `–`, the empty key, and then `Abgabe`, `2026-01-02T09:15`, `01.01.2026`, `10`, `2`, `-3,5`, `–`, the empty key

#### Scenario: Equal keys keep their order
- **WHEN** the sorting function orders the keys `b`, `a`, `b` and `a` ascending
- **THEN** the order is the second, the fourth, the first and the third

#### Scenario: Server order without the script
- **WHEN** a test client requests the page of an item with three movements booked in the order of the dates 2026-03-01, 2026-01-15 and 2026-02-10
- **THEN** its movements table carries `data-sortable` and an `id`, no header carries `aria-sort`, its rows run newest booking first, 2026-02-10, 2026-01-15, 2026-03-01, and each date cell's `data-sort` is its ISO date
