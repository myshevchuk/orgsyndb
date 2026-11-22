## ADDED Requirements

### Requirement: Widgets
A record page of the application SHALL group its data into widgets: a `section.widget` headed by a title bar holding the widget's title as its heading, and, where the page gives them, the number of its rows and a short note. The same kind of data shows in the same kind of widget on every page that shows it; a page's spec names the data it shows and its order, not where a widget stands. Lists of records show as tables, not as bullet lists. A widget marked collapsible is a `details` element whose `summary` holds its title bar; its content is part of the page whether it is open or closed, and the print stylesheet prints it open.

A table marked `data-sortable` sorts in the browser when a user activates one of its column headers: by that column ascending, and descending on the next activation, numbers by their value, dates by their order and text by the language's collation, empty cells and cells reading `–` last in either direction, and rows of equal value keeping their order. The header of the sorted column carries `aria-sort`. Without the script, and until a user sorts it, the table shows the order its page's spec states. A widget's open or closed state and a table's sorting are view controls (Form dialogs): a part of the page refreshed after a form saved in a dialog keeps them.

#### Scenario: History as a widget
- **WHEN** a test client requests the page of an item whose priority was changed after its creation
- **THEN** the page holds one collapsible `section.widget` titled with the history, holding a table whose rows list the changed field with its old and new values above the creation, newest first, and no `ul.lab-history`

#### Scenario: Sorting in the browser
- **WHEN** the sorting function of `lab.js` sorts the rows `10 µmol`, `2 µmol` and `–` by that column ascending, and then descending
- **THEN** the order is `2 µmol`, `10 µmol`, `–`, and then `10 µmol`, `2 µmol`, `–`

#### Scenario: Server order without the script
- **WHEN** a test client requests an item's page
- **THEN** its movements table carries `data-sortable`, no header carries `aria-sort`, and its rows are in booking order, newest first
