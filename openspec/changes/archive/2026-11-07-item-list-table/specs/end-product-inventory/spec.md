## MODIFIED Requirements

### Requirement: Item list
`/lab/inventory/end-products/` SHALL list the items of the inventory `end-products` in a table with the columns `Artikelnr.`, `Name`, `Kategorie`, `Gebinde`, `Fach`, `Box`, `Bestand`, `Ø Jahr`, `lfd. Jahr`, `Reichweite`, `Bulk` and `Bemerkung` (`Article no.`, `Name`, `Category`, `Container`, `Compartment`, `Box`, `Stock`, `Mean per year`, `This year`, `Coverage`, `Bulk`, `Note`): the article number linking to the item's page; the name, linking to the compound when there is one, and to the item's page when the item has no article number, followed by the mark `neu` (`new`), a `sup.mark-new`, for a new item; the category; the size with its unit; the compartment and the box; the quantity alone, its cell carrying its level as Stock levels states; the mean per year and the current year's consumption, the cell of each value above zero carrying its heat as Consumption heat states; the coverage; the bulk; and the note. The table sits in a box `div.table-scroll.table-sticky` that, on screen, is at most the window's height, scrolls in both directions and keeps the table's header rows at its top and its first column at its left; `lab.css` states these rules for the screen alone, so on paper the box neither scrolls nor limits its height and the table prints whole, without the filter row and the forms above it.

The GET parameter `sort` names the column that orders the rows, one of `number`, `name`, `category`, `container`, `compartment`, `box`, `stock`, `mean_year`, `this_year`, `coverage`, `bulk` and `note`, any other value or none being `number`; `dir=desc` reverses the order, any other value or none keeping it. The columns order:

- `number` by article number;
- `name`, `category` and `note` by their text regardless of case, the name being the item's;
- `container` with units of mass before units of amount of substance, then by size in mg or µmol;
- `compartment` and `box` with runs of digits by their value, so that `2` comes before `10`, and the rest regardless of case;
- `stock` by level in the order of Stock levels, out first, then by coverage, smallest first and items without one last;
- `mean_year`, `this_year` and `coverage` by their value, smallest first;
- `bulk` by the number of the item's containers its open lots would fill.

Items without a value in the sorting column, being without an article number, category, note, compartment, box, mean per year, coverage or open lot, come after the others in either direction. Items that tie, these included, keep the default order: by article number, items without one after the others and by name, then unit, then size. Each column's header holds a link to the list with the filters in force and `sort` naming that column, with `dir=desc` when the list is sorted by it already and not reversed; the header of the sorting column carries `aria-sort`, `ascending` or `descending`. Sorted by `number`, a row whose item has an article number, the same as the item of the row before, carries the class `same-article`, its name visually hidden and its article number muted; items without an article number are never grouped.

A second header row holds the filters, each a GET parameter whose control belongs to the form `filters` above the table and is labelled with its column, and each showing the value in force: under `Artikelnr.`, `Name` and `Bemerkung` the text fields `number`, `name` and `note`, listing the items whose article number, whose name or the name of whose compound, or whose note contains the text regardless of case; under `Kategorie`, `Gebinde`, `Fach` and `Box` the choices `category`, `container`, `compartment` and `box` of `Alle` (`All`) and each value in use once, in the column's order, listing the items with that value, the containers given as the size without trailing zeros and the unit's code, such as `2.5 mg` or `10 umol`, and labelled as the column shows them; and under `Bestand` the choice `stock` of `Alle` and the seven levels in their order, listing exactly the items at that level. The form `filters` holds the search `q`, text found regardless of case in the article number, name, category, note or the name of the item's compound; `sort` and `dir` as in force; the button `Filtern` (`Filter`); and a link `Zurücksetzen` (`Reset`) to the list in the same order without filters. A line above the table counts the items listed, and a legend below it names the seven levels in their order, each with its colour, what it means, and the number of items of the inventory at it, linking to the list with `stock=<level>`, and shows the five heats in their order between `wenig` (`little`) and `viel` (`much`). A signed-in user sees a link `Neuer Artikel` (`New item`), and, before the article number of each item that has one, a check box `item` with the item's id, belonging to a form that requests `/lab/inventory/deliveries/new/` with the button `Lieferschein mit Auswahl` (`Delivery note from selection`). `/lab/inventory/` redirects to this list.

#### Scenario: Urgent items first
- **WHEN** the database holds items at the levels dormant, watch, ok, undelivered, out and low, and a test client requests the list with `sort=stock`
- **THEN** the rows show out, low, watch, ok, undelivered and dormant

#### Scenario: Items without an article number last
- **WHEN** the database holds items `CH-0012`, `Neuverbindung 9` without an article number, `CH-0001` and `Brücke 3` without an article number, and a test client requests the list
- **THEN** the rows show `CH-0001`, `CH-0012`, `Brücke 3` and `Neuverbindung 9`, and the names of the last two link to their items' pages

#### Scenario: Numbers alone
- **WHEN** an item at the level low holds 3 containers and a test client requests the list
- **THEN** its stock cell carries `level-low` and the title `niedrig`, holds `niedrig` in a `span.visually-hidden`, and shows `3` and no other text

#### Scenario: Legend with counts
- **WHEN** the database holds two items at the level ok, one at low and one dormant, and a test client requests the list with `q=xyz`, which finds none
- **THEN** the legend's entries read 0 for out, critical, watch and undelivered, 2 for ok, 1 for low and 1 for dormant, and the entry of low links to `?stock=low`

#### Scenario: One level exactly
- **WHEN** the database holds items at the levels out, critical and low, and a test client requests the list with `stock=critical`
- **THEN** it lists the item at critical alone, and the choice `stock` shows `kritisch`

#### Scenario: New items marked
- **WHEN** on 2026-11-04 one item has the `stocked_on` 2026-02-01, another 2025-12-31, and a third none
- **THEN** the list marks the first `neu` and neither other

#### Scenario: Locations
- **WHEN** one item is kept in compartment `2`, box `7`, another in compartment `10`, box `7`, and a test client requests the list, once with `compartment=2` and once with `box=7`
- **THEN** both rows show their compartment and box, the first request lists the first item alone and the second both

#### Scenario: Ticking rows
- **WHEN** a signed-in user requests the list holding items `CH-0012` and `CH-0010` and an item without an article number
- **THEN** the rows of `CH-0012` and `CH-0010` hold a check box `item` with their ids and the third none, and the form of the boxes requests `/lab/inventory/deliveries/new/` by GET

#### Scenario: Sorting by a column
- **WHEN** the database holds `A-1` in the category `Säuren`, `A-2` without a category and `A-3` in `Ester`, and a test client requests the list with `sort=category`, then with `sort=category&dir=desc`
- **THEN** the rows show `A-3`, `A-1` and `A-2`, then `A-1`, `A-3` and `A-2`; on the first list the header `Kategorie` carries `aria-sort` `ascending` and links to the list with `sort=category` and `dir=desc`, and the header `Artikelnr.` to the list with `sort=number` and no `dir`

#### Scenario: Containers and locations in their order
- **WHEN** items of 1 g, 100 mg, 10 µmol and 250 mg are kept in the compartments `10`, `2`, none and `3`, and a test client requests the list with `sort=container`, then with `sort=compartment`
- **THEN** both lists show the items of 100 mg, 250 mg, 1 g and 10 µmol in this order

#### Scenario: Column filters
- **WHEN** the database holds `CH-0012` `(E)-Zimtsäure` of 100 mg with the note `Kühlschrank`, `CH-0010` `Aspirin` of 1 g and `CH-0016` `Isopentylacetat` of 100 mg, and a test client requests the list with `number=0012`, with `name=ZIMT`, with `container=100 mg`, with `note=kühl`, and with `container=100 mg&sort=name&dir=desc`
- **THEN** the lists show `CH-0012`; `CH-0012`; `CH-0012` and `CH-0016`; `CH-0012`; and `CH-0016` and `CH-0012`, each filter shows the value requested, the header `Name` of the last list links to the list with `container` `100 mg`, `sort=name` and no `dir`, and its link `Zurücksetzen` to the list with `sort=name` and `dir=desc` alone

#### Scenario: Sizes of one article grouped
- **WHEN** the database holds `CH-0012` in 100 mg and in 1 g, `CH-0010` in 1 g, and `Brücke 3` and `Neuverbindung 9` without an article number, and a test client requests the list, then with `sort=name`
- **THEN** the first list shows `CH-0010`, `CH-0012` in 1 g, `CH-0012` in 100 mg, `Brücke 3` and `Neuverbindung 9`, the third row alone carrying `same-article`, with its name in a `span.visually-hidden`, and the last two rows showing their names as links; no row of the second list carries `same-article`

#### Scenario: A table that keeps its headers
- **WHEN** a test client requests the list
- **THEN** the table sits in a `div.table-scroll.table-sticky`, its `thead` holds two rows, and no column is `Ø Quartal`
- **AND** every rule of `lab.css` naming `table-sticky` lies inside `@media screen`, and a rule inside `@media print` hides the filter row and the forms above the table

## ADDED Requirements

### Requirement: Consumption heat
The heat of an item's mean per year, and that of its current year's consumption, SHALL be, for a value above zero, `heat-<n>` with `n` being `1 + ⌊5B/N⌋`, where `N` is the number of items of the inventory `end-products` whose value of the same kind is above zero and `B` the number of those whose value is smaller. A value of zero, or none, has no heat. The heats run from a pale pink, `heat-1`, through red to a blackish red, `heat-5`; each cell carrying one shows its text with a contrast of at least 4.5:1 to the heat's background in both colour schemes.

#### Scenario: Fifths of the consuming items
- **WHEN** six items' consumption in the current year is 0, 1, 2, 2, 5 and 9 containers, and a test client requests the list, then with `number=` naming the item of 9 alone
- **THEN** their cells `lfd. Jahr` carry no heat, `heat-1`, `heat-2`, `heat-2`, `heat-4` and `heat-5`, and the cell of the item of 9 carries `heat-5` in the second list too

#### Scenario: Readable in both schemes
- **WHEN** a test reads the heat colours of `lab.css` for the light and the dark scheme
- **THEN** each heat's text and background have a contrast of at least 4.5:1
