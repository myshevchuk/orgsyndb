## MODIFIED Requirements

### Requirement: Item list
`/lab/inventory/end-products/` SHALL list the items under the heading `Endprodukte` (`End products`), followed by the number of all items; `/lab/inventory/` redirects to it. It shows them in one of two views, `Tabelle` (`Table`) and `Details` (`Details`). Both views show its table, with these columns in this order:

- the article number, linking to the item's page;
- the name, linking to the substance's page (lab-registry "Registry pages") when the item has an article number and to the item's page when it has none, followed by the mark `neu` (`new`), a `sup.mark-new`, for a new item;
- the category;
- the container;
- the quantity, its cell carrying its level as Stock levels states;
- the mean per year and the current year's consumption, each cell carrying its heat as Consumption heat states;
- the coverage;
- the compartment, the box, and the bulk as Filling from bulk states.

By default the rows are ordered by category regardless of case, items without one last, then by article number, items without one after the others and by name regardless of case, then by container (Items).

GET parameters select the items listed: `q` those in whose article number, category or note, or in whose substance's key, name, German name or short name, the text is found regardless of case; `category`, `compartment` and `box` those with that value; `container` those of that size and unit, given as the size without trailing zeros and the unit's code, such as `2.5 mg` or `10 umol`; and `stock` those at that level, a value that names no level selecting every item. The page shows the value of each filter in force, offers each category, container, compartment and box in use, and offers each level with the number of items at it that the other filters admit, linking to the list with those filters and that level.

A user switches between the views; the browser remembers the view last chosen in the cookie `item-list-view`, `table` or `details`, and the list opens in that view, in the table view without it or with another value. The address does not name the view.

One item listed is selected: the one `selected=<id>` names among those listed; without it, or naming none of them, the first item listed, and none when the list is empty. The selected row is marked in both views. In either view, a click without a modifier key in a row, but not on its links or its check box, selects its item, and so do the arrow keys up and down; a link in a row leads where it links. Selecting an item loads its details in place; once they have arrived its row is marked and the address names it in `selected`, so that a reload selects the same item. The marked row and the address name the item whose details the list holds, also while another item's details are loading and when loading them fails. Filtering the list and changing its order keep the selected item while the list still holds it.

The details view shows, with the table, the details of the selected item: its article number, name and container; its quantity with its level, and its coverage; its compartment and box, each `nicht hinterlegt` (`not recorded`) when it is not set; each open vessel of its substance with its location, or `Kolben` for a flask without one, or `nicht hinterlegt`, its batch and its amount, linking to the vessel's page; its consumption: the current year's so far, the means per year and per quarter, `–` for a mean there is not, and the consumption of each quarter of the current year and of the two years before it, with each year's sum, the quarters to come left empty, and the years whose quarters hold an entered value above zero; its note; and a link to its page, and for a signed-in user the item page's links but `Stornieren` (Item page).

A signed-in user sees a link `Neuer Artikel` (`New item`), and, in the row of each item that has an article number, a check box `item` with the item's id, belonging to a form that requests `/lab/inventory/deliveries/new/` with the button `Lieferschein mit Auswahl` (`Delivery note from selection`). On paper the list prints every row of its table, without the details.

#### Scenario: Items without an article number last
- **WHEN** the database holds items `CH-0012`, `Neuverbindung 9` without an article number, `CH-0001` and `Brücke 3` without an article number, none with a category, and a test client requests the list
- **THEN** the rows show `CH-0001`, `CH-0012`, `Brücke 3` and `Neuverbindung 9`, and the names of the last two link to their items' pages

#### Scenario: By category first
- **WHEN** the database holds `A-2` in the category `Ester`, `A-1` in `Säuren`, `A-3` in `Ester` and `A-4` without a category, and a test client requests the list
- **THEN** the rows show `A-2`, `A-3`, `A-1` and `A-4`

#### Scenario: Sizes by amount
- **WHEN** the database holds `CH-0012` in 1 g, 100 mg and 500 mg, and a test client requests the list
- **THEN** the rows show 100 mg, 500 mg and 1 g in this order

#### Scenario: Numbers alone
- **WHEN** an item at the level low holds 3 containers and a test client requests the list
- **THEN** its stock cell carries `level-low` and the title `niedrig`, holds `niedrig` in a `span.visually-hidden`, and shows `3` and no other text

#### Scenario: Levels with their counts
- **WHEN** the database holds two items at the level ok and one at low in the category `A`, and one dormant item in `B`, and a test client requests the list with `category=A`
- **THEN** the list offers ok with 2 items, low with 1 and each other level with 0, and links low to the list with `category=A` and `stock=low`

#### Scenario: One level exactly
- **WHEN** the database holds items at the levels out, critical and low, and a test client requests the list with `stock=critical`
- **THEN** it lists the item at critical alone

#### Scenario: New items marked
- **WHEN** on 2026-11-04 one item has the `stocked_on` 2026-02-01, another 2025-12-31, and a third none
- **THEN** the list marks the first `neu` and neither other

#### Scenario: Locations
- **WHEN** one item is kept in compartment `2`, box `7`, another in compartment `10`, box `7`, and a test client requests the list, once with `compartment=2` and once with `box=7`
- **THEN** each row shows its compartment and box, the first request lists the first item alone and the second both

#### Scenario: Ticking rows
- **WHEN** a signed-in user requests the list holding items `CH-0012` and `CH-0010` and an item without an article number
- **THEN** the rows of `CH-0012` and `CH-0010` hold a check box `item` with their ids and the third none, and the form of the boxes requests `/lab/inventory/deliveries/new/` by GET

#### Scenario: Filters
- **WHEN** the database holds `CH-0012` `(E)-Zimtsäure` of 100 mg in `Säuren` with the note `Kühlschrank`, `CH-0010` `Aspirin` of 1 g in `Säuren` and `CH-0016` `Isopentylacetat` of 100 mg in `Ester`, and a test client requests the list with `q=ZIMT`, with `q=kühl`, with `category=Ester` and with `container=100 mg`
- **THEN** the lists show `CH-0012`; `CH-0012`; `CH-0016`; and `CH-0016` and `CH-0012`, in the order of their categories; and each filter shows the value requested

#### Scenario: The view from the cookie
- **WHEN** a test client requests the list without a cookie, with the cookie `item-list-view` set to `details`, then to `table`, and then to `other`
- **THEN** the second answer shows the details view and the others the table view, and no answer's links name a view

#### Scenario: Details of an item
- **WHEN** on 2026-11-04 an item `CH-0012` `(E)-Zimtsäure` of 100 mg holding 3 containers has no compartment or box, the entered values 4 for each quarter of 2024 and 6, 5 and 7 for the first three quarters of 2026, and a delivery of 2 dated 2026-10-15, an open vessel of the batch `B-7` holding `50` mg of its substance lies in `Kühlschrank 2`, and a test client requests the list with `selected` naming that item
- **THEN** the details show `CH-0012`, `(E)-Zimtsäure`, `100 mg` and 3 containers with their level, `nicht hinterlegt` for the compartment and the box, `Kühlschrank 2` and `B-7`, linking to the vessel's page, the consumption 4, 4, 4, 4 and 16 for 2024, 0, 0, 0, 0 and 0 for 2025, and 6, 5, 7, 2 and 20 for 2026, name 2024 and 2026 as holding entered values, and link to the item's page

#### Scenario: The first item selected
- **WHEN** the database holds `A-1` in the category `Säuren` and `A-2` in `Ester`, and a test client requests the list, then with `selected` naming no item, then with `category=Säuren` and `selected` naming `A-2`, and then with `category=Basen` and `selected` naming `A-2`
- **THEN** the first two lists mark the row of `A-2` and show its details, the third marks the row of `A-1` and show its details, and the fourth marks no row and shows none, in either view

#### Scenario: The selection kept
- **WHEN** the database holds `A-2` and `A-3` in `Ester` and `A-1` in `Säuren`, and a test client requests the list with `category=Ester` and `selected` naming `A-3`, then with `category=Ester` alone, then with `category=Ester` and `selected` naming `A-1`, and then with `category=Basen`
- **THEN** the filter form holds `selected` and the list's links to its stock levels, to its other orders and to its reset name it in `selected`: `A-3` in the first answer, `A-2` in the second and third, and in the fourth neither the form nor those links hold `selected`

#### Scenario: Links in the details
- **WHEN** a signed-in user requests the list with `selected` naming an item without an article number, and a visitor requests it
- **THEN** the user's details link `Artikelnr. eintragen`, `Abfüllen`, `Bestand korrigieren` and `Bearbeiten`, and neither `Abgabe buchen` nor `Verbrauch nachtragen`; the visitor's details hold none of these links

#### Scenario: Another item in place
- **WHEN** a test client requests the list with `category=Ester` holding `A-2` and `A-3`, then, as htmx does, the details the row of `A-3` loads in place, and then the same address without htmx
- **THEN** the second answer holds the details of `A-3` alone, as the list with `selected` naming `A-3` shows them; the third redirects to the list with `selected` naming `A-3`

### Requirement: Consumption
An item SHALL keep entered consumption per quarter, with a change history (web-app "Change history"), a whole number of containers of at least zero for a year and a quarter 1 to 4, not after the current quarter, at most one per quarter; entering a value replaces the quarter's earlier one, and entering none removes it. Entering a value for an item without an article number is refused, zero included. A quarter's consumption is its entered value, zero when there is none, plus the counts of the item's lines, in notes current or historical, dated in it, leaving out reversed movements and reversed historical notes. Quarters and years follow the calendar in `Europe/Berlin`.

The mean per year is the sum of the consumption of the complete calendar years before the current one, from the year of the item's first entered value, zero included, or delivery line that counts as consumption, divided by the number of those years; with none, there is no mean. The mean per quarter is a quarter of the mean per year. An item whose consumption above zero all lies in the current year has projected means instead: the mean per quarter is the current year's consumption times 91.3125 divided by the number of days from the first day of the quarter of its first consumption above zero to today, today included, or by 91.3125 when that is fewer; the mean per year is four times that. The current year's consumption is that of the current year so far, shown beside the mean for comparison. The coverage is the quantity divided by the mean per quarter, in quarters, and has no value without a mean above zero or for an item whose level is `dormant` or `undelivered`. Means and coverage show to one decimal place, rounded half up; levels compare the unrounded values.

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
- **THEN** its mean per quarter is 2,5, its mean per year 10,1 and its coverage 1,2 quarters, and its level is watch

#### Scenario: One early delivery
- **WHEN** on 2026-11-04 an item with 2 containers has a delivery of 3 dated 2026-10-15 and no other consumption
- **THEN** its projected mean per quarter is 3,0, its coverage 0,7 quarters and its level low

#### Scenario: No coverage for a dormant item
- **WHEN** on 2026-11-04 an item with 6 containers has the entered value 8 for each quarter of 2024 and nothing since
- **THEN** its mean per year is 16, it has no coverage, and its level is dormant

### Requirement: Vessel list
`/lab/inventory/vessels/` SHALL list the open vessels, of every substance, with the columns `Gefäß`, `Name`, `Artikelnr.`, `Art`, `Charge`, `Herkunft`, `Menge`, `Ort`, `Datum` and `Angebrochen` (`Vessel`, `Name`, `Article no.`, `Kind`, `Batch`, `Source`, `Amount`, `Location`, `Date`, `Opened`): `#<id>`, linking to the vessel's page; its substance's name, linking to the substance's page; the article number of the substance's article, empty when there is none; its kind; its batch, linking to the batch's page; the batch's source as the batch list shows it; its amount; its location; its batch's date; for a vessel of a bought batch its `opened_on` or `versiegelt` (`sealed`), and nothing for one of a made batch. The vessels are ordered by name regardless of case, then by their batch's date, oldest first and vessels without one last, then by id. `empty=1` adds the used-up vessels. `kind=<kind>`, one of `flask`, `end-product`, `intermediate` and `commercial`, lists the vessels of that kind; another value lists every kind. The page offers each kind and shows the one in force. A signed-in user sees a link `Neue Charge` (`New batch`).

#### Scenario: Used-up vessels
- **WHEN** the database holds an open vessel and a used-up vessel, and a test client requests the vessel list with and without `empty=1`
- **THEN** it lists both with it and only the open vessel without

#### Scenario: Vessels by kind
- **WHEN** the database holds an open flask of a made batch of `cinnamic-acid`, an open vessel of a made batch of `acetophenone`, which has no article, and one of a batch of `acetophenone` bought from `Sigma`, and a test client requests the vessel list, and then with `kind=commercial`
- **THEN** the first lists the three with the kinds `Kolben`, `Zwischenprodukt` and `Handelschemikalie`, the first with `CH-0012` and the others with an empty article number, the last with `gekauft · Sigma`; the second lists the bought vessel alone
