# end-product-inventory Specification

## Purpose
Count the lab's end products in the lab application: articles, each one substance of the registry with its article number and category; items, an article in containers of one size, changed only by movements, delivery notes current and historical, consumption per quarter with its means and coverage, stock levels, bulk lots and filling from them, their lists, pages and forms, and the admin.
## Requirements
### Requirement: Items
The `inventory` package SHALL keep items, each a container size of an article (Articles), with a change history:

- `article`, fixed once the item is created;
- `size`, a decimal greater than zero with up to three places, and `unit`, one of `mg`, `umol` (shown `µmol`), `g` and `mmol`;
- `quantity`, the whole number of containers left, at least zero, changed only by movements;
- `note`, optional text;
- `status`, one of `active` (`aktiv`, `active`), the default, `not_needed` (`nicht benötigt`, `not needed`) and `discontinued` (`auslaufend`, `discontinued`), the state set by hand of a size that is set aside;
- `stocked_on` (`Im Bestand seit`, `In stock since`), the day the item entered stock, or none, never after today;
- `compartment` (`Fach`, `Compartment`) and `box` (`Box`, `Box`), where its containers are kept, each optional and at most 30 characters.

The first movement that leaves an item holding containers while it has no `stocked_on` sets it to that movement's date; it may be edited. An item whose `stocked_on` lies in the current calendar year is new (`neu`, `new`).

No two items of one article share size and unit. The size and unit are fixed once the item is created, in the views and the admin alike. An item's substance, name, article number and category are its article's, so every size of an article has the same substance and molar mass. An item without an article number, one whose article has none, cannot be delivered and cannot have consumption entered. An item shows as its article number, container and name, or as its container and name when it has no article number.

#### Scenario: Substance through the article
- **WHEN** the demo data set is written and an item has the article number `CH-0012`
- **THEN** its substance is `cinnamic-acid`, and its name `(E)-Zimtsäure` links to `/lab/registry/substances/cinnamic-acid/` wherever it shows

#### Scenario: One article in two sizes
- **WHEN** a signed-in user creates items of the substance `cinnamic-acid` of 10 µmol and of 50 µmol, then a third of 10 µmol
- **THEN** the first two are saved, as sizes of one article, and the third is refused with an error at the size

#### Scenario: Positions without an article number
- **WHEN** a signed-in user creates an item of 10 mg of a substance `new-compound-9` that has no article
- **THEN** the item is saved as the first size of a new article of that substance, without an article number

#### Scenario: Stock entry by the first filling
- **WHEN** on 2026-11-04 a signed-in user creates an item with an opening count of 0, fills 3 containers dated 2026-10-20, and fills 2 more dated 2026-11-02
- **THEN** its `stocked_on` is 2026-10-20 and it is new

#### Scenario: Stock entry by the opening count
- **WHEN** on 2026-11-04 a signed-in user creates an item with an opening count of 5, and then gives it the `stocked_on` 2019-05-02 in its edit form
- **THEN** its `stocked_on` was 2026-11-04 and is 2019-05-02, its history records the change, and it is not new

### Requirement: Item movements
Every change of an item's quantity SHALL be a movement holding `kind`, `count`, `quantity_after`, `date`, `booked_at`, `user`, `note`, and `delivery_note`, `bulk_movement` and `reverses` where they apply:

- `opening` (`Anfangsbestand`, `Opening count`): the first movement of every item, its `count` the quantity entered on creation;
- `delivery` (`Abgabe`, `Delivery`): `count` containers out, more than zero and at most the quantity, booked by a line of the current delivery note `delivery_note` and dated as the note;
- `filling` (`Abfüllung`, `Filling`): `count` containers in, more than zero; `bulk_movement` the lot's movement when a lot was named;
- `correction` (`Korrektur`, `Correction`): `count` the quantity counted, at least zero; a note is required;
- `reversal` (`Storno`, `Reversal`): undoes one delivery or filling, named by `reverses`, adding back a delivery's count or taking back a filling's, and returning a filling's amount to its lot with a lot reversal; a movement is reversed at most once, a reversal of a filling whose containers are no longer there is refused, and a note is required.

`date` is the day the movement took place, today by default and never after today; `booked_at` is the time it was booked. The quantity changes by one atomic conditional update in the transaction that stores the movement, so two bookings prepared from the same quantity can never take more than it holds, on PostgreSQL and SQLite alike, and `quantity_after` is the quantity after that update. A refused movement changes nothing. Movements are never edited or deleted, in the views or the admin, except that deleting an item in the admin deletes its opening movement with it.

#### Scenario: Delivery
- **WHEN** user `KL` books a delivery note `LS-2026-117` to `Produktion` with one line of 2 containers of an item with 5
- **THEN** the item has 3, and its newest movement is a delivery of 2 with `quantity_after` 3, by `KL`, naming that note

#### Scenario: Concurrent deliveries
- **WHEN** two deliveries of 4 are validated against an item with 5 and then stored one after the other
- **THEN** the first is stored, the second is refused, and the item has 1

#### Scenario: Correction needs a note
- **WHEN** a signed-in user posts a correction to 4 without a note
- **THEN** the form shows an error at the note and nothing changes

#### Scenario: Reversing a delivery
- **WHEN** a signed-in user reverses a delivery of 2 dated in the third quarter of 2026, with the note `falsch gebucht`
- **THEN** the item has 2 containers more, the delivery no longer counts in that quarter's consumption, and a second reversal of it is refused

### Requirement: Delivery notes
The `inventory` package SHALL keep delivery notes (`Lieferscheine`), each with a change history: `number`, optional, at most 30 characters, unique among notes when given; `date`, never after today; `recipient`, optional, at most 100 characters; `note`; `historical`; `reversed` and `reversal_note`, the flag of a reversed historical note and the note it was reversed with; `created_by` and `created_at`; and one or more lines, each an item with an article number and a `count` above zero, no item twice in one note. A line of an item without an article number is refused, current or historical. A note shows as its number, or as `#<id>` when it has none.

A current note, `historical` off, books one `delivery` movement per line, dated as the note, all in one transaction: when one line's count exceeds its item's quantity, the whole note is refused and nothing changes. A historical note, `historical` on, records deliveries made before they could be booked, such as those of old paper delivery notes: its lines change no quantity. A historical note is refused when one of its lines' items has an entered consumption value for the quarter of the note's date, and an entered value is refused for a quarter in which the item has lines of a historical note that is not reversed. A signed-in user may mark a historical note reversed, with a required note; a current note's lines are reversed one by one through their movements, and the note shows as reversed when all its lines are, and as partly reversed when some are. A note's date, kind and lines are fixed once it is created, its number, recipient and note may be edited, and no note is deleted, in the views or the admin.

#### Scenario: Note with several lines
- **WHEN** a signed-in user books a current note with 2 containers of one item holding 5 and 3 of another holding 3
- **THEN** both items are reduced, to 3 and 0, and the note lists both lines

#### Scenario: One line too many refuses the note
- **WHEN** a signed-in user books a current note with 2 containers of an item holding 5 and 4 of an item holding 3
- **THEN** the form shows an error at the second line, no note exists, and both items keep their quantities

#### Scenario: Historical note
- **WHEN** a signed-in user enters a historical note dated 2025-03-12 with 4 containers of an item holding 5 that has no entered value for the first quarter of 2025
- **THEN** the item still has 5, and its consumption in the first quarter of 2025 is 4

#### Scenario: Historical note in a quarter with an entered value
- **WHEN** an item has the entered value 6 for the first quarter of 2025 and a signed-in user enters a historical note dated 2025-03-12 with a line of that item
- **THEN** the form shows an error at that line and nothing is saved

#### Scenario: First delivery needs the article number
- **WHEN** an item without an article number holds 5 containers and a signed-in user posts a current note with a line of 2 of it
- **THEN** the form shows an error at that line, no note exists and the item keeps 5

### Requirement: Consumption
An item SHALL keep entered consumption per quarter, a whole number of containers of at least zero for a year and a quarter 1 to 4, not after the current quarter, at most one per quarter; entering a value replaces the quarter's earlier one, and entering none removes it. Entering a value for an item without an article number is refused, zero included. A quarter's consumption is its entered value, zero when there is none, plus the counts of the item's lines, in notes current or historical, dated in it, leaving out reversed movements and reversed historical notes. Quarters and years follow the calendar in `Europe/Berlin`.

The mean per year is the sum of the consumption of the complete calendar years before the current one, from the year of the item's first entered value, zero included, or delivery line that counts as consumption, divided by the number of those years; with none, there is no mean. The mean per quarter is a quarter of the mean per year. An item whose consumption above zero all lies in the current year has projected means instead: the mean per quarter is the current year's consumption times 91.3125 divided by the number of days from the first day of the quarter of its first consumption above zero to today, today included, or by 91.3125 when that is fewer; the mean per year is four times that. Projected means, and a coverage computed from them, are marked `hochgerechnet aus dem laufenden Jahr` (`projected from the current year`) wherever they show. The current year's consumption is that of the current year so far, shown beside the mean for comparison. The coverage is the quantity divided by the mean per quarter, in quarters, and has no value without a mean above zero or for an item whose level is `dormant` or `undelivered`. Means and coverage show to one decimal place, rounded half up; levels compare the unrounded values.

#### Scenario: Means and coverage
- **WHEN** on 2026-11-04 an item with 3 containers has the entered value 4 for each quarter of 2024, 5 for each quarter of 2025 and 10 for the first quarter of 2026, and a delivery of 3 dated 2026-10-15
- **THEN** its mean per year is 18, its mean per quarter 4,5, its current year's consumption 13, its coverage 0,7 quarters, and its level low

#### Scenario: Years counted
- **WHEN** on 2026-11-04 one item has the entered value 0 for the third quarter of 2024 and 8 for each quarter of 2025, and another has entered values only in 2026
- **THEN** the first item's mean per year is 16, and the second's means are projected

#### Scenario: A reversed note does not start the history
- **WHEN** on 2026-11-04 an item has the entered value 8 for each quarter of 2025 and a historical note dated 2024-05-02, which is then reversed
- **THEN** its mean per year is 32

#### Scenario: Entered value removed for old notes
- **WHEN** an item has the entered value 6 for the first quarter of 2025, a signed-in user removes it, and then enters a historical note dated 2025-03-12 with 4 of that item
- **THEN** the note is saved and the quarter's consumption is 4

#### Scenario: No consumption without an article number
- **WHEN** a signed-in user enters 3, and then 0, for the second quarter of 2026 on an item without an article number
- **THEN** the form shows an error each time and the item has no entered value

#### Scenario: No value for a quarter to come
- **WHEN** on 2026-11-04 a signed-in user enters 3 for the first quarter of 2027, and then 3 for the fourth quarter of 2026
- **THEN** the first is refused with an error and the second is saved

#### Scenario: Projected means
- **WHEN** on 2026-11-04 an item with 3 containers has the entered value 6 for the second quarter of 2026 and no other consumption
- **THEN** its mean per quarter is 2,5, its mean per year 10,1 and its coverage 1,2 quarters, each marked as projected, and its level is watch

#### Scenario: One early delivery
- **WHEN** on 2026-11-04 an item with 2 containers has a delivery of 3 dated 2026-10-15 and no other consumption
- **THEN** its projected mean per quarter is 3,0, its coverage 0,7 quarters and its level low

#### Scenario: No coverage for a dormant item
- **WHEN** on 2026-11-04 an item with 6 containers has the entered value 8 for each quarter of 2024 and nothing since
- **THEN** its mean per year is 16, it has no coverage, and its level is dormant

### Requirement: Stock levels
An item's level SHALL be the first of these that applies:

- `dormant` (`ruhend`, `dormant`): its `status` is `not_needed` or `discontinued`, or it has consumption above zero but none in the current calendar year or the one before;
- `undelivered` (`noch nie abgegeben`, `never delivered`): it has no consumption above zero;
- `out` (`aufgebraucht`, `out`): its quantity is zero;
- with its mean per quarter `Q`, projected or not: `critical` (`kritisch`, `critical`) below `Q/2`, `low` (`niedrig`, `low`) below `Q`, and `watch` (`beobachten`, `watch`) below `2Q`;
- `ok` (`ausreichend`, `sufficient`) otherwise.

Every item therefore has a level. Their order, from the most urgent, is out, critical, low, watch, ok, undelivered and dormant; planning applies to no item whose level is dormant or undelivered. Wherever a quantity shows with its level, its element carries the class `level-<level>`; the item list shows the level's label as its cell's `title` and in a `span.visually-hidden`, and every other page as text. `lab.css` gives the seven classes red, orange, yellow, pale green, a darker green, light slate blue and dark grey backgrounds as colour tokens with a dark-scheme variant, each keeping the text at a WCAG 2 contrast ratio of at least 4.5:1 against its background, unrounded, in both schemes.

#### Scenario: Thresholds
- **WHEN** items with a mean per quarter of 4 and consumption in the current year have 0, 1, 2, 3, 4, 7 and 8 containers
- **THEN** their levels are out, critical, low, low, watch, watch and ok

#### Scenario: No consumption
- **WHEN** an item without entered values or deliveries has 2 containers
- **THEN** its level is undelivered and it has no coverage

#### Scenario: Set aside by hand
- **WHEN** an item with a mean per quarter of 4 and no container has the `status` `discontinued`, and another with 1 container the `status` `not_needed`
- **THEN** both are dormant

#### Scenario: Nothing asked for in two years
- **WHEN** on 2026-11-04 one item has the entered value 5 for the fourth quarter of 2024 and none since, and another has 5 for the first quarter of 2025 and none since
- **THEN** the first is dormant and the second is not

### Requirement: Bulk lots
The `inventory` package SHALL keep bulk lots, each with a change history: `substance`, a substance of the registry; `source` (`Herkunft`, `Source`), `made` (`hergestellt`, `made`) or `bought` (`gekauft`, `bought`); `supplier` (`Lieferant`, `Supplier`), optional, at most 100 characters; `unit`, one of `mg`, `g`, `umol` and `mmol`, in which the lot is entered and shown; `amount`, at least zero, kept in the lot's base unit, `mg` for `mg` and `g` and `µmol` for `µmol` and `mmol`, with six decimal places; `batch`, `location`, at most 100 characters, and `made_on`, each optional; and `note`. The substance, source and unit are fixed once the lot is created. A lot may be of any substance, intermediates and house-made reagents among them, and one substance may have made and bought lots side by side; a lot belongs to every item of its substance's article, when the substance has one. Its amount shows in its unit to three decimal places, rounded half up.

Its amount changes only by its movements, each holding `kind`, `amount`, `amount_after`, `date`, `booked_at`, `user` and `note`, by one atomic conditional update in the transaction that stores the movement, as for items: `opening`, the amount entered on creation; `filling`, the amount taken, more than zero and at most the lot's amount; `correction`, the amount weighed, with a required note; `reversal`, the amount a reversed filling returns. A lot at zero is used up. Lot movements are never edited or deleted, except that deleting a lot in the admin deletes its opening movement with it.

#### Scenario: Correction of a lot
- **WHEN** a signed-in user corrects a lot of `50` mg to `47,5` mg with the note `nachgewogen`
- **THEN** the lot holds `47,5` mg and its newest movement is that correction

#### Scenario: Made and bought lots
- **WHEN** a signed-in user creates a lot of `cinnamic-acid` made in the lab and another bought from the supplier `Sigma`
- **THEN** both lots exist with their sources, the second with its supplier, and the items of the article `CH-0012` count both among their bulk

#### Scenario: Lot of a substance without an article
- **WHEN** a signed-in user creates a lot of the substance `acetophenone`, which has no article
- **THEN** the lot exists and belongs to no item

### Requirement: Filling from bulk
Filling an item SHALL optionally name an open lot of its substance and the amount taken from it, in the lot's unit. The proposed amount is the count times the item's size, converted into the lot's base unit and rounded half up to six places, shown in the lot's unit. The filling form has, besides its button to book, a button `Menge vorschlagen` (`Propose amount`), which books nothing and shows the form again with the values entered and the amount set to the proposal for the count and lot entered. When a lot is named and the amount is left empty, the proposed amount is booked. Units of the same kind convert by their factors: 1 g is 1000 mg, and 1 mmol is 1000 µmol. Mass and amount of substance convert through the molar mass of the item's substance in g/mol. Without that molar mass across kinds, nothing is proposed, the amount is required, and `Menge vorschlagen` shows an error at the amount. The item's filling and the lot's filling are stored in one transaction. An amount above the lot's, or one that rounds to zero, refuses both.

Wherever an item shows its bulk, it shows the amount of its open lots by unit and the number of its containers they would still fill. That number is, for each open lot that converts into the item's unit, its amount converted and divided by the size and rounded down, summed over the lots. A lot that does not convert is left out of that number and counted as not convertible.

#### Scenario: Filling with conversion
- **WHEN** an item `CH-0012` of 10 µmol, whose substance has the molar mass 148.16, has a lot of `50` mg, and a signed-in user fills 5 containers from it
- **THEN** `Menge vorschlagen` shows the form with the amount `7,408` and books nothing; booking it gives the item 5 more containers, the lot holds `42,592` mg, and the item's movement names the lot's movement

#### Scenario: Small filling from a lot in grams
- **WHEN** an item `CH-0012` of 10 µmol, whose substance has the molar mass 148.16, has a lot of `1` g, and a signed-in user fills 1 container from it, leaving the amount empty
- **THEN** the lot holds 998,5184 mg, shown as `0,999` g

#### Scenario: Containers from bulk
- **WHEN** an item `CH-0012` of 10 µmol, whose substance has the molar mass 148.16, has one open lot of `50` mg
- **THEN** it shows `50 mg` and 33 containers

#### Scenario: Lots are not pooled
- **WHEN** an item of 10 mg has two open lots of `6` mg
- **THEN** it shows 0 containers from bulk

### Requirement: Item list
`/lab/inventory/end-products/` SHALL list the items under the heading `Endprodukte` (`End products`), followed by the number of items, in a table with the columns `Artikelnr.`, `Name`, `Kategorie`, `Gebinde`, `Bestand`, `Ø Jahr`, `Abgegeben`, `Reichweite`, `Lagerort`, `Fach`, `Box`, `Bulk verfügbar` and `Bemerkung` (`Article no.`, `Name`, `Category`, `Container`, `Stock`, `Mean per year`, `Delivered`, `Coverage`, `Location`, `Compartment`, `Box`, `Bulk available`, `Note`). Under its label, in a `small`, the header of `Bestand` reads `Gebinde` (`containers`), that of `Ø Jahr` `Gebinde / Jahr` (`containers / year`), that of `Abgegeben` the current year and `Gebinde`, as `2026 · Gebinde`, and that of `Reichweite` `Quartale` (`quarters`). The cells hold:

- the article number, linking to the item's page;
- the name, linking to the substance's page (lab-registry "Registry pages") when the item has an article number and to the item's page when it has none, followed by the mark `neu` (`new`), a `sup.mark-new`, for a new item;
- the category, and the size with its unit;
- the quantity alone, its cell carrying its level as Stock levels states;
- the mean per year, and the current year's consumption as a button that opens its statistics, each cell carrying its heat as Consumption heat states;
- the coverage;
- a button `Ort` (`Location`), labelled for screen readers with `Lagerort` (`Location`) and the item, that opens its location;
- the compartment, the box, the bulk and the note.

Every cell carries the class `col-<key>`, the key being its column's `sort` value below, or `location` for `Lagerort`. Means and a coverage projected from the current year are marked in their cells as Consumption states.

Each popup is an element with the `popover` attribute inside the cell of the button that opens it, which names it in `popovertarget`; it holds a heading, the item's article number, container and quantity, a button that closes it with `popovertargetaction="hide"`, and a link to the item's page. The row whose popup is open is highlighted.

- The location popup, headed `Lagerort · <name>` (`Location · <name>`), lists under `Fertige Gebinde` (`Finished containers`) the compartment and the box, each `nicht hinterlegt` (`not recorded`) when it is not set, and under `Bulk, separat gelagert` (`Bulk, stored separately`) each open lot of the item's substance with its location, or `nicht hinterlegt`, its batch and its amount, linking to the lot's page.
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

A line above the table reads `<n> von <m> Artikeln` (`<n> of <m> items`), the items listed and all items, then the order in force: the sorting column's label, and after it those of `Artikelnr.` and `Gebinde` that it is not, followed by `aufsteigend` (`ascending`), as `Kategorie, Artikelnr., Gebinde aufsteigend`; when reversed, the sorting column's label followed by `absteigend` (`descending`), and then the others followed by `aufsteigend`. While a filter is in force the line ends with a link `Zurücksetzen` (`Reset`) to the list in the same order without filters.

Above the table, the GET form `filters` holds the search `q`, labelled `Artikel suchen` (`Search items`), listing the items in whose article number, category or note, or in whose substance's key, name, German name or short name, the text is found regardless of case; the choice `category`, labelled `Kategorie`, of `Alle Kategorien` (`All categories`) and each category in use; hidden fields for `stock`, `sort` and `dir` as in force; and the button `Filtern` (`Filter`). Beside it:

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
- **WHEN** an item `CH-0012` of 100 mg holding 3 containers has no compartment or box, and an open lot `B-7` of `50` mg of its substance lies in `Kühlschrank 2`, and a test client requests the list
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

### Requirement: Bulk list
`/lab/inventory/end-products/bulk/` SHALL list the open bulk lots, of every substance, with the columns `Name`, `Artikelnr.`, `Herkunft`, `Charge`, `Menge`, `Ort`, `Datum` and `Bemerkung` (`Name`, `Article no.`, `Source`, `Batch`, `Amount`, `Location`, `Date`, `Note`): the name being the lot's substance's, linking to its page; the article number that of the substance's article, empty when there is none; and the source `hergestellt` or `gekauft`, followed by the supplier when there is one. The lots are ordered by name regardless of case, then date, oldest first and lots without one last. `empty=1` adds the used-up lots. The item list, the bulk list and the delivery list carry section tabs `Artikel`, `Bulk` and `Lieferungen` (`Items`, `Bulk`, `Deliveries`) in the site's `nav.section-tabs` markup. A signed-in user sees a link `Neues Bulk` (`New bulk lot`).

#### Scenario: Used-up lots
- **WHEN** the database holds an open lot and a used-up lot, and a test client requests the bulk list with and without `empty=1`
- **THEN** it lists both with it and only the open lot without

#### Scenario: Lots of an intermediate
- **WHEN** the database holds an open lot of `acetophenone`, which has no article, made in the lab, and one of `cinnamic-acid` bought from `Sigma`, and a test client requests the bulk list
- **THEN** it lists the first with an empty article number and `hergestellt`, and the second with `CH-0012` and `gekauft · Sigma`

### Requirement: Delivery list
`/lab/inventory/deliveries/` SHALL list the delivery notes, newest date first, then newest booking first, each with its number linking to its page, date, recipient, the mark `nachgetragen` (`entered later`) on a historical note and `storniert` (`reversed`) on a reversed one, and its lines with article number, name, size and count; a current note shows `storniert` when all its lines are reversed and `teilweise storniert` (`partly reversed`) when some are. GET parameters filter it and keep their values: `q`, text found regardless of case in the number or recipient, and `item`, an item's id. `/lab/inventory/deliveries/<id>/` shows one note with its lines, each with the article number, name, size, compartment, box and count, their movements and the change history, and an unknown id answers 404. A signed-in user sees a link `Neuer Lieferschein` (`New delivery note`).

#### Scenario: Deliveries of one item
- **WHEN** two notes have lines of an item and a third does not, and a test client requests the list with that item's id
- **THEN** it lists the two notes, the newer first

#### Scenario: A pick list
- **WHEN** a note has a line of an item kept in compartment `2`, box `7`, and a test client requests the note's page
- **THEN** the line shows `2` and `7` in the columns `Fach` and `Box`

### Requirement: Item page
`/lab/inventory/items/<id>/` SHALL show the article number and name as heading, or the name alone for an item without an article number, followed by the mark `neu` for a new item; the substance, linking to its page; the category, size and note; the `status` when it is not `active`; the `stocked_on`, `–` when there is none; the compartment and the box, `–` for each that is not set; the quantity with its level; the means and coverage; the current year's consumption; a chart of the consumption of each quarter of the two complete years before the current one and of the current year, an inline `svg` with one bar per quarter titled with the quarter and its value and, when the item has a mean, a line at the mean per quarter, followed by a table of each quarter's entered value, deliveries and total; the movements in booking order, newest first, with date, booking time, kind, count, quantity after, the user's initials, the delivery note with its number and recipient, the note, and the mark `storniert` (`reversed`) on a reversed movement; the open lots of its substance with the number of containers they would fill; under `Prognose` (`Forecast`), the item's forecast, as `production-planning` states under Item forecast; and the change history. A signed-in user sees the links `Abgabe buchen` (`Book delivery`), to the new delivery note with the item in its first line, `Abfüllen` (`Fill`), `Bestand korrigieren` (`Correct count`), `Verbrauch nachtragen` (`Enter consumption`), `Bearbeiten` (`Edit`), and `Stornieren` (`Reverse`) beside each delivery and filling not yet reversed; for an item without an article number, `Artikelnr. eintragen` (`Enter article number`), to its edit form, takes the place of `Abgabe buchen`, and `Verbrauch nachtragen` is left out. An unknown id answers 404.

#### Scenario: Chart and ledger
- **WHEN** on 2026-11-04 a test client requests the page of an item with entered values for three quarters of 2025 and two deliveries in 2026
- **THEN** the `svg` has twelve bars, the table lists the same values, and the movements list the deliveries before the opening count

#### Scenario: Page of a position without an article number
- **WHEN** a signed-in user requests the page of an item of 10 mg of the substance `new-compound-9`, named `Neuverbindung 9`, without an article number
- **THEN** its heading is `Neuverbindung 9`, its substance links to `/lab/registry/substances/new-compound-9/`, and it links `Artikelnr. eintragen` to its edit form and has neither `Abgabe buchen` nor `Verbrauch nachtragen`

#### Scenario: A discontinued size
- **WHEN** a test client requests the page of an item with the `status` `discontinued`, 4 containers and the `stocked_on` 2024-03-01
- **THEN** it shows `auslaufend`, `01.03.2024`, and 4 with the class `level-dormant` and the text `ruhend`

### Requirement: Bulk lot page
`/lab/inventory/bulk/<id>/` SHALL show the lot's substance, linking to its page, and the article number of the substance's article when there is one; its source and supplier; its batch, amount, location, date and note, the mark `aufgebraucht` (`used up`) at zero, its movements in booking order, newest first, with date, booking time, kind, amount, amount after, the user's initials, note and, for a filling, the item filled, each task that belongs to the lot through its batch, linking to it, and its change history. A signed-in user sees the links `Korrigieren` (`Correct`) and `Bearbeiten` (`Edit`). An unknown id answers 404.

#### Scenario: Lot page after a filling
- **WHEN** a test client requests the page of a lot from which 5 containers of an item were filled
- **THEN** its newest movement is that filling, linking to the item

### Requirement: Inventory forms
For a signed-in user, the application SHALL offer:

- `/lab/inventory/end-products/new/`: a new item with its opening count, its substance by key, the article number, optional, and the category with a `datalist` of the categories in use, the `stocked_on`, optional, left empty for the opening count to set, and the compartment and the box, each with a `datalist` of the values in use;
- `/lab/inventory/items/<id>/edit/`: the item's note, `status`, `stocked_on`, compartment and box, the last two each with a `datalist` of the values in use, and its article's category and, while the article has none, its article number, both saved on the article for every size of it, as the form says beside them;
- `/lab/inventory/deliveries/new/`: a delivery note with ten rows for lines, each offering the items with an article number, each shown as its article number, container and name and, where they are set, `Fach <compartment>` and `Box <box>` (`Compartment <compartment>`, `Box <box>`), joined by ` · ` and the locations by ` / `, rows left empty being ignored, and a check box `nachgetragen – Bestand bleibt unverändert` (`entered later – stock unchanged`) for a historical note; `?item=<id>`, given once or several times, puts those items in the first rows in the order given, up to ten, leaving out ids of items it does not offer and ids given twice;
- `/lab/inventory/deliveries/<id>/reverse/`: marking a historical note reversed, with its note;
- `/lab/inventory/items/<id>/fill/` and `/correct/`: a movement;
- `/lab/inventory/items/<id>/movements/<movement id>/reverse/`: the reversal of a delivery or filling, with its note;
- `/lab/inventory/items/<id>/consumption/`: the entered value of a year and quarter, replacing an earlier one of that quarter, or removing it when left empty;
- `/lab/inventory/deliveries/<id>/edit/`: a note's number, recipient and note;
- `/lab/inventory/bulk/new/`: a new lot with its opening amount, its substance by key, its source, `hergestellt` when none is chosen, and its supplier, and the location with a `datalist` of the locations in use; `?substance=<key>`, `?batch=<batch>` and `?made_on=<date>` fill in those fields;
- `/lab/inventory/bulk/<id>/edit/`, for the batch, location, date and note, and `/correct/`.

A substance is named by its key, offered through a `datalist` of every substance's key labelled with its name; an unknown key is an error at the field. On the new-item form, the article number and the category make the substance's article when it has none, an empty number giving it none. When the substance has an article, a field left empty leaves the article's value as it is; a category entered replaces the article's; an article number entered gives the article that number when it has none, as the edit form does, and must otherwise be its number, or the form shows an error at it. On the edit form, the category field holds the article's category and saves what it holds, empty included, and the article number, offered only while the article has none, gives it one when entered and leaves it without one when empty. Invalid input shows the form again with the errors beside their fields and saves nothing. A saved form leads, with a message naming the record, to the page of the delivery note for the forms of notes, and to the page of the item or lot for every other.

#### Scenario: New item
- **WHEN** user `KL` posts an item of the substance `cinnamic-acid`, whose article is `CH-0012`, of 10 µmol with an opening count of 12
- **THEN** the item exists with 12 containers, its only movement is the opening count by `KL`, and the response redirects to its page

#### Scenario: New item without an article number
- **WHEN** a signed-in user posts an item of the substance `new-compound-9`, which has no article, of 10 mg with an empty article number and an opening count of 4
- **THEN** the item exists with 4 containers, and its new article has no article number

#### Scenario: Another size of a numbered article
- **WHEN** the article of `cinnamic-acid` is `CH-0012` in the category `Säuren`, and a signed-in user posts an item of `cinnamic-acid` of 50 µmol with the article number and the category left empty, then one of 100 µmol with the article number `CH-0099`
- **THEN** the first item is saved and the article is still `CH-0012` in `Säuren`, and the second form shows an error at the article number and saves nothing

#### Scenario: Unknown substance
- **WHEN** a signed-in user posts the new-item form naming the substance `no-such-substance`
- **THEN** the form shows an error at the substance and nothing is saved

#### Scenario: Entered consumption replaced
- **WHEN** a signed-in user enters 4 for the second quarter of 2026 and then 5 for the same quarter
- **THEN** the item has one entered value for that quarter, 5

#### Scenario: Fixed identity
- **WHEN** a signed-in user posts the edit form of an item with an article number with a different article number, size and unit
- **THEN** those fields are unchanged

#### Scenario: New lot from the query
- **WHEN** a signed-in user requests `/lab/inventory/bulk/new/?substance=cinnamic-acid&batch=B-2026-031&made_on=2026-10-30`
- **THEN** the form holds the substance `cinnamic-acid`, the source `hergestellt`, the batch `B-2026-031` and the date 2026-10-30

#### Scenario: Substances offered
- **WHEN** the demo data set is written and a signed-in user requests the new-item form
- **THEN** its substances' `datalist` offers `cinnamic-acid` labelled `(E)-Zimtsäure`

#### Scenario: Delivery rows without positions lacking a number
- **WHEN** items `CH-0012` and `Neuverbindung 9` without an article number exist and a signed-in user requests the new delivery note form
- **THEN** each row offers `CH-0012` and not `Neuverbindung 9`

#### Scenario: Setting a size aside
- **WHEN** a signed-in user posts the edit form of an item with the `status` `not_needed`
- **THEN** the item has that status, its history records the change, and the list shows it as dormant

#### Scenario: Stock entry in the future
- **WHEN** on 2026-11-04 a signed-in user posts the edit form of an item with the `stocked_on` 2026-11-05
- **THEN** the form shows an error at it and the item is unchanged

#### Scenario: A note from the selection
- **WHEN** a signed-in user requests `/lab/inventory/deliveries/new/?item=<a>&item=<b>&item=<a>&item=<c>`, `<c>` the id of an item without an article number
- **THEN** the first row holds item `<a>`, the second `<b>`, and the other rows none

#### Scenario: Rows name the location
- **WHEN** an item `CH-0012` of 100 mg named `(E)-Zimtsäure` is kept in compartment `2`, box `7`, and a signed-in user requests the new delivery note form
- **THEN** its rows offer it as `CH-0012 · 100 mg · (E)-Zimtsäure · Fach 2 / Box 7`

### Requirement: Inventory in the admin
The admin SHALL list articles, items, bulk lots, delivery notes and the movements for staff, with search by article number and by the substance's key and names, and the change history of each record. It shows movements, delivery notes' dates, kinds and lines, and the fixed fields read-only, an article's number among them once it has one; an article number entered there is given as the edit form gives it, only while the article has none. It deletes no movement or delivery note, deletes an article only while it has no items, and deletes an item or lot only while its one movement is the opening and, for an item, no delivery note has a line of it.

#### Scenario: Deleting a booked item
- **WHEN** a staff user deletes an item that has a delivery
- **THEN** the admin refuses and the item remains

#### Scenario: Article number in the admin
- **WHEN** a staff user opens the change page of an article without a number and of the article `CH-0012`
- **THEN** the first offers the article number as an input and the second shows it read-only

#### Scenario: A stale change page keeps the number
- **WHEN** a staff user loads the admin's change page of an article without a number, a signed-in user then gives it `CH-0021` in the edit form of one of its items, and the staff user saves the change page with the article number left empty and a new category
- **THEN** the article keeps `CH-0021` and has the new category

### Requirement: Consumption heat
The heat of an item's mean per year, and that of its current year's consumption, SHALL be, for a value above zero, `heat-<n>` with `n` being `1 + ⌊5B/N⌋`, where `N` is the number of items whose value of the same kind is above zero and `B` the number of those whose value is smaller. A value of zero, or none, has no heat. The heats run from a pale pink, `heat-1`, through red to a blackish red, `heat-5`; each cell carrying one shows its text with a contrast of at least 4.5:1 to the heat's background in both colour schemes. The item list's check box `Verbrauch einfärben` shows or hides the heats' colours (Item list).

#### Scenario: Fifths of the consuming items
- **WHEN** six items' consumption in the current year is 0, 1, 2, 2, 5 and 9 containers, and a test client requests the list, then with `q=` naming the item of 9 alone
- **THEN** their cells `Abgegeben` carry no heat, `heat-1`, `heat-2`, `heat-2`, `heat-4` and `heat-5`, and the cell of the item of 9 carries `heat-5` in the second list too

#### Scenario: Readable in both schemes
- **WHEN** a test reads the heat colours of `lab.css` for the light and the dark scheme
- **THEN** each heat's text and background have a contrast of at least 4.5:1

### Requirement: Articles
The `inventory` package SHALL keep articles, each with a change history: `substance`, a substance of the registry (lab-registry "Substances") and the article's primary key, so that an article is that one substance and a substance has at most one article; `article_number`, the number the article's delivery notes carry, at most 30 characters, unique among articles when given, or none: an article has none until it is first delivered; and `category`, optional, at most 100 characters. An article's name is its substance's name. An article without an article number may be given one once, which is refused when another article has it; from then on the number is fixed, in the views and the admin alike. An article that has items cannot be deleted.

#### Scenario: Article number entered once
- **WHEN** a signed-in user gives an item whose article has no article number the number `CH-0021` in its edit form, and then posts its edit form with the number `CH-0022`
- **THEN** the article has the number `CH-0021`, its history records the change, and the second post leaves it unchanged

#### Scenario: Article number taken
- **WHEN** the article of `cinnamic-acid` has the number `CH-0012` and a signed-in user gives `CH-0012` to an item of another article
- **THEN** the form shows an error at the article number and that article keeps none

#### Scenario: One number for every size
- **WHEN** an article without a number has items of 10 µmol and of 50 µmol and a signed-in user gives the first the article number `CH-0021`
- **THEN** both items show `CH-0021`

