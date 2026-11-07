## MODIFIED Requirements

### Requirement: Item list
`/lab/inventory/end-products/` SHALL list the items of the inventory `end-products` under the heading `Endprodukte` (`End products`), followed by the number of items of the inventory, in a table with the columns `Artikelnr.`, `Name`, `Kategorie`, `Gebinde`, `Bestand`, `Ø Jahr`, `Abgegeben`, `Reichweite`, `Lagerort`, `Fach`, `Box`, `Bulk verfügbar` and `Bemerkung` (`Article no.`, `Name`, `Category`, `Container`, `Stock`, `Mean per year`, `Delivered`, `Coverage`, `Location`, `Compartment`, `Box`, `Bulk available`, `Note`). Under its label, in a `small`, the header of `Bestand` reads `Gebinde` (`containers`), that of `Ø Jahr` `Gebinde / Jahr` (`containers / year`), that of `Abgegeben` the current year and `Gebinde`, as `2026 · Gebinde`, and that of `Reichweite` `Quartale` (`quarters`). The cells hold:

- the article number, linking to the item's page;
- the name, linking to the compound when there is one and to the item's page when the item has no article number, followed by the mark `neu` (`new`), a `sup.mark-new`, for a new item;
- the category, and the size with its unit;
- the quantity alone, its cell carrying its level as Stock levels states;
- the mean per year, and the current year's consumption as a button that opens its statistics, each cell carrying its heat as Consumption heat states;
- the coverage;
- a button `Ort` (`Location`), labelled for screen readers with `Lagerort` (`Location`) and the item, that opens its location;
- the compartment, the box, the bulk and the note.

Every cell carries the class `col-<key>`, the key being its column's `sort` value below, or `location` for `Lagerort`. Means and a coverage projected from the current year are marked in their cells as Consumption states.

Each popup is an element with the `popover` attribute inside the cell of the button that opens it, which names it in `popovertarget`; it holds a heading, the item's article number, container and quantity, a button that closes it with `popovertargetaction="hide"`, and a link to the item's page. The row whose popup is open is highlighted.

- The location popup, headed `Lagerort · <name>` (`Location · <name>`), lists under `Fertige Gebinde` (`Finished containers`) the compartment and the box, each `nicht hinterlegt` (`not recorded`) when it is not set, and under `Bulk, separat gelagert` (`Bulk, stored separately`) each open lot of the item's article number with its location, or `nicht hinterlegt`, its batch and its amount, linking to the lot's page.
- The statistics popup, headed `Abgegeben · <name>` (`Delivered · <name>`), shows the current year's consumption up to today, the mean per year and the mean per quarter, `–` for a mean there is not; a bar for each quarter of the current year, as high as its share of the year's largest quarter, the current quarter's marked `laufend` (`running`) and the quarters to come without a bar; and a table of the consumption of each quarter of the two years before the current one and of the current year, with each year's sum, the quarters to come left empty. It names the years whose quarters hold an entered value above zero, and says that the current year is incomplete.

The GET parameter `sort` names the column that orders the rows, one of `number`, `name`, `category`, `container`, `stock`, `mean_year`, `this_year`, `coverage`, `compartment`, `box`, `bulk` and `note`, any other value or none being `category`; `dir=desc` reverses the order, any other value or none keeping it. The columns order:

- `number` by article number;
- `name`, `category` and `note` by their text regardless of case, the name being the item's;
- `container` with units of mass before units of amount of substance, then by size in mg or µmol;
- `compartment` and `box` with runs of digits by their value, so that `2` comes before `10`, and the rest regardless of case;
- `stock` by level in the order of Stock levels, out first, then by coverage, smallest first and items without one last;
- `mean_year`, `this_year` and `coverage` by their value, smallest first;
- `bulk` by the number of the item's containers its open lots would fill.

Items without a value in the sorting column, being without an article number, category, note, compartment, box, mean per year, coverage or open lot, come after the others in either direction. Items that tie, these included, keep the default order: by article number, items without one after the others and by name, then by container as `container` orders. Each column's header but that of `Lagerort` holds a link to the list with the filters in force and `sort` naming that column, with `dir=desc` when the list is sorted by it already and not reversed; the header of the sorting column carries `aria-sort`, `ascending` or `descending`. Sorted by `category`, the first row of each category after the first carries the class `category-start`.

A line above the table reads `<n> von <m> Artikeln` (`<n> of <m> items`), the items listed and those of the inventory, then the order in force: the sorting column's label, and after it those of `Artikelnr.` and `Gebinde` that it is not, followed by `aufsteigend` (`ascending`), as `Kategorie, Artikelnr., Gebinde aufsteigend`; when reversed, the sorting column's label followed by `absteigend` (`descending`), and then the others followed by `aufsteigend`. While a filter is in force the line ends with a link `Zurücksetzen` (`Reset`) to the list in the same order without filters.

Above the table, the GET form `filters` holds the search `q`, labelled `Artikel suchen` (`Search items`), listing the items in whose article number, name, category, note or compound's name the text is found regardless of case; the choice `category`, labelled `Kategorie`, of `Alle Kategorien` (`All categories`) and each category in use; hidden fields for `stock`, `sort` and `dir` as in force; and the button `Filtern` (`Filter`). Beside it:

- a button labelled `Bestandsstatus` (`Stock status`), reading the label of the level in force, or `Alle` (`All`), and in parentheses the number of items it admits, opens a popup that lists `Alle Bestandsstatus` (`All stock statuses`) and the seven levels in their order. Each level shows its colour, its label, what it means and how many items are at it. Each entry counts the items that every filter but `stock` admits, and links to the list with the filters and order in force and `stock` set to the level, or without `stock` for `Alle Bestandsstatus`. The entry in force carries `aria-current="true"`. `stock` lists exactly the items at that level.
- a button `Weitere Filter` (`More filters`), followed in parentheses by the number of its filters in force when there are some, opens a popup with the choices `container`, `compartment` and `box`, which belong to the form `filters`. Each offers `Alle` (`All`) and each value in use once, in the column's order, and lists the items with that value. Containers are given as the size without trailing zeros and the unit's code, such as `2.5 mg` or `10 umol`, and labelled as the column shows them.

Each filter's control shows the value in force. Choices that submit the form when they change carry `data-submit`.

Three view controls belong to no form:

- a button `Spalten` (`Columns`) opens a popup with a check box for each column but `Artikelnr.`, `Name` and `Bestand`. All are checked but those of `Fach`, `Box` and `Bemerkung`. An unchecked box hides its column's cells, on screen and on paper.
- a choice `Zeilenhöhe` (`Row height`) of `Kompakt` (`Compact`), the default, and `Sehr kompakt` (`Very compact`) sets the rows' height.
- a check box `Verbrauch einfärben` (`Colour consumption`), checked by default, followed by the five heats in their order between `wenig` (`little`) and `viel` (`much`). Unchecked, it shows the cells of `Ø Jahr` and `Abgegeben` without their heat's colours.

Each view control carries `data-remember` and takes effect through `lab.css` alone.

The page loads `/lab/static/lab.js` (web-app Page shell), which:

- places each popup beside the button that opened it, below it or, without room there, above it, and else as low as the window allows, always inside the window;
- submits the form of a choice marked `data-submit` when its value changes, and hides that form's button `Filtern`;
- restores, when the page loads, the state of each control marked `data-remember` from the browser's local storage, and saves it there whenever it changes.

Without the script the page still works: a popup opens in the window's centre, `Filtern` submits the form, and the view controls take effect until the page is left.

Below the table, a line reads `Bestand: Farben und Bedeutungen im Filter „Bestandsstatus". Ort öffnet Fach, Box und Bulk. Abgegeben öffnet Jahres- und Quartalsstatistik.` (`Stock: colours and meanings in the filter "Stock status". Location opens compartment, box and bulk. Delivered opens statistics by year and quarter.`).

The table sits in a box `div.table-scroll.table-sticky` that, on screen, is at most the window's height, scrolls in both directions and keeps the table's header row at its top and its first column at its left; `lab.css` states these rules for the screen alone, so on paper the box neither scrolls nor limits its height and the table prints whole, without the form, the buttons and the view controls above and below it. A signed-in user sees a link `Neuer Artikel` (`New item`), and, before the article number of each item that has one, a check box `item` with the item's id, belonging to a form that requests `/lab/inventory/deliveries/new/` with the button `Lieferschein mit Auswahl` (`Delivery note from selection`). `/lab/inventory/` redirects to this list.

#### Scenario: Urgent items first
- **WHEN** the database holds items at the levels dormant, watch, ok, undelivered, out and low, and a test client requests the list with `sort=stock`
- **THEN** the rows show out, low, watch, ok, undelivered and dormant

#### Scenario: Items without an article number last
- **WHEN** the database holds items `CH-0012`, `Neuverbindung 9` without an article number, `CH-0001` and `Brücke 3` without an article number, none with a category, and a test client requests the list
- **THEN** the rows show `CH-0001`, `CH-0012`, `Brücke 3` and `Neuverbindung 9`, and the names of the last two link to their items' pages

#### Scenario: By category first
- **WHEN** the database holds `A-2` in the category `Ester`, `A-1` in `Säuren`, `A-3` in `Ester` and `A-4` without a category, and a test client requests the list
- **THEN** the rows show `A-2`, `A-3`, `A-1` and `A-4`, the rows of `A-1` and `A-4` alone carry `category-start`, the header `Kategorie` carries `aria-sort` `ascending`, and the line above the table reads `4 von 4 Artikeln · Kategorie, Artikelnr., Gebinde aufsteigend`

#### Scenario: Sizes by amount
- **WHEN** the database holds `CH-0012` in 1 g, 100 mg and 500 mg, and a test client requests the list
- **THEN** the rows show 100 mg, 500 mg and 1 g in this order

#### Scenario: Numbers alone
- **WHEN** an item at the level low holds 3 containers and a test client requests the list
- **THEN** its stock cell carries `level-low` and the title `niedrig`, holds `niedrig` in a `span.visually-hidden`, and shows `3` and no other text

#### Scenario: Stock menu with counts
- **WHEN** the database holds two items at the level ok and one at low in the category `A`, and one dormant item in `B`, and a test client requests the list with `category=A`
- **THEN** the menu's entries read 0 for out, critical, watch, undelivered and dormant, 2 for ok and 1 for low, its button reads `Alle (3)`, and the entry of low links to the list with `category=A` and `stock=low`

#### Scenario: One level exactly
- **WHEN** the database holds items at the levels out, critical and low, and a test client requests the list with `stock=critical`
- **THEN** it lists the item at critical alone, the menu's button reads `Kritisch (1)`, and the menu's entry of critical carries `aria-current="true"`

#### Scenario: New items marked
- **WHEN** on 2026-11-04 one item has the `stocked_on` 2026-02-01, another 2025-12-31, and a third none
- **THEN** the list marks the first `neu` and neither other

#### Scenario: Locations
- **WHEN** one item is kept in compartment `2`, box `7`, another in compartment `10`, box `7`, and a test client requests the list, once with `compartment=2` and once with `box=7`
- **THEN** each row's location popup shows its compartment and box, the first request lists the first item alone and the second both, and `Weitere Filter` reads `Weitere Filter (1)` on both

#### Scenario: Location popup
- **WHEN** an item `CH-0012` of 100 mg holding 3 containers has no compartment or box, and an open lot `B-7` of `50` mg of `CH-0012` lies in `Kühlschrank 2`, and a test client requests the list
- **THEN** its button `Ort` names a popover in its own cell, headed `Lagerort` with the item's name, which shows `CH-0012`, `100 mg` and 3 containers, `nicht hinterlegt` for the compartment and the box, and `Kühlschrank 2` and `B-7` linking to the lot's page, and links to the item's page

#### Scenario: Statistics popup
- **WHEN** on 2026-11-04 an item has the entered values 4 for each quarter of 2024, and 6, 5 and 7 for the first three quarters of 2026, and a delivery of 2 dated 2026-10-15
- **THEN** its cell `Abgegeben` holds a button reading `20` that names a popover in the same cell, headed `Abgegeben` with the item's name, whose table reads 4, 4, 4, 4 and 16 for 2024, 0, 0, 0, 0 and 0 for 2025, and 6, 5, 7, 2 and 20 for 2026, whose bars mark the fourth quarter `laufend`, and which names 2024 and 2026 as holding entered values

#### Scenario: Ticking rows
- **WHEN** a signed-in user requests the list holding items `CH-0012` and `CH-0010` and an item without an article number
- **THEN** the rows of `CH-0012` and `CH-0010` hold a check box `item` with their ids and the third none, and the form of the boxes requests `/lab/inventory/deliveries/new/` by GET

#### Scenario: Sorting by a column
- **WHEN** the database holds `A-1` in the category `Säuren`, `A-2` without a category and `A-3` in `Ester`, and a test client requests the list with `sort=category`, then with `sort=category&dir=desc`
- **THEN** the rows show `A-3`, `A-1` and `A-2`, then `A-1`, `A-3` and `A-2`; on the first list the header `Kategorie` carries `aria-sort` `ascending` and links to the list with `sort=category` and `dir=desc`, the header `Artikelnr.` to the list with `sort=number` and no `dir`, and the header `Lagerort` holds no link; the second list's line reads `Kategorie absteigend, Artikelnr., Gebinde aufsteigend`

#### Scenario: Containers and locations in their order
- **WHEN** items of 1 g, 100 mg, 10 µmol and 250 mg are kept in the compartments `10`, `2`, none and `3`, and a test client requests the list with `sort=container`, then with `sort=compartment`
- **THEN** both lists show the items of 100 mg, 250 mg, 1 g and 10 µmol in this order

#### Scenario: Filters above the table
- **WHEN** the database holds `CH-0012` `(E)-Zimtsäure` of 100 mg in `Säuren` with the note `Kühlschrank`, `CH-0010` `Aspirin` of 1 g in `Säuren` and `CH-0016` `Isopentylacetat` of 100 mg in `Ester`, and a test client requests the list with `q=ZIMT`, with `q=kühl`, with `category=Ester`, with `container=100 mg`, and with `container=100 mg&sort=name&dir=desc`
- **THEN** the lists show `CH-0012`; `CH-0012`; `CH-0016`; `CH-0016` and `CH-0012`, in the order of their categories; and `CH-0016` and `CH-0012`, each filter shows the value requested, the header `Name` of the last list links to the list with `container` `100 mg`, `sort=name` and no `dir`, and its link `Zurücksetzen` to the list with `sort=name` and `dir=desc` alone; the list without filters has no link `Zurücksetzen`

#### Scenario: View controls
- **WHEN** a test client requests the list
- **THEN** the popup of `Spalten` holds check boxes for every column but `Artikelnr.`, `Name` and `Bestand`, those of `Fach`, `Box` and `Bemerkung` unchecked, the choice `Zeilenhöhe` selects `Kompakt`, the check box `Verbrauch einfärben` is checked, each of them carries `data-remember` and belongs to no form, and every cell of the table carries `col-<key>` for its column
- **AND** `lab.css` hides the cells of a column whose check box is unchecked, and drops the heat colours while `Verbrauch einfärben` is unchecked

#### Scenario: A table that keeps its headers
- **WHEN** a test client requests the list
- **THEN** the table sits in a `div.table-scroll.table-sticky`, its `thead` holds one row, and no column is `Ø Quartal`
- **AND** every rule of `lab.css` naming `table-sticky` lies inside `@media screen`, and a rule inside `@media print` hides the form `filters`, the buttons above the table and the view controls

#### Scenario: Placing a popup
- **WHEN** a test runs `OrgSynLab.place` of `lab.js` for a popup of 300 by 200 pixels in a window of 1000 by 800, for a button at the top left and at the bottom right, and in a window of 1000 by 300, too low for the popup below or above it, for a button in its middle
- **THEN** the popup lies below the first button, starting at its left edge; above the second, kept 16 pixels inside the window's right edge; and over the third, its bottom 16 pixels above the window's bottom edge

### Requirement: Consumption heat
The heat of an item's mean per year, and that of its current year's consumption, SHALL be, for a value above zero, `heat-<n>` with `n` being `1 + ⌊5B/N⌋`, where `N` is the number of items of the inventory `end-products` whose value of the same kind is above zero and `B` the number of those whose value is smaller. A value of zero, or none, has no heat. The heats run from a pale pink, `heat-1`, through red to a blackish red, `heat-5`; each cell carrying one shows its text with a contrast of at least 4.5:1 to the heat's background in both colour schemes. The item list's check box `Verbrauch einfärben` shows or hides the heats' colours (Item list).

#### Scenario: Fifths of the consuming items
- **WHEN** six items' consumption in the current year is 0, 1, 2, 2, 5 and 9 containers, and a test client requests the list, then with `q=` naming the item of 9 alone
- **THEN** their cells `Abgegeben` carry no heat, `heat-1`, `heat-2`, `heat-2`, `heat-4` and `heat-5`, and the cell of the item of 9 carries `heat-5` in the second list too

#### Scenario: Readable in both schemes
- **WHEN** a test reads the heat colours of `lab.css` for the light and the dark scheme
- **THEN** each heat's text and background have a contrast of at least 4.5:1
