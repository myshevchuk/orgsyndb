## MODIFIED Requirements

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

No two items of one article share size and unit. The size and unit are fixed once the item is created, in the views and the admin alike. An item's substance, name, article number and category are its article's, so every size of an article has the same substance and molar mass. An item without an article number, one whose article has none, cannot be delivered and cannot have consumption entered. An item shows as its article number, container and name, or as its container and name when it has no article number. Containers compare by amount: units of mass before units of amount of substance, then by size in mg or µmol.

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

### Requirement: Item list
`/lab/inventory/end-products/` SHALL list the items under the heading `Endprodukte` (`End products`), followed by the number of all items; `/lab/inventory/` redirects to it. Its table has a column for each of the following, which a user may hide, all but the article number, the name and the quantity:

- the article number, linking to the item's page;
- the name, linking to the substance's page (lab-registry "Registry pages") when the item has an article number and to the item's page when it has none, followed by the mark `neu` (`new`), a `sup.mark-new`, for a new item;
- the category and the container;
- the quantity, its cell carrying its level as Stock levels states;
- the mean per year and the current year's consumption, each cell carrying its heat as Consumption heat states;
- the coverage;
- the compartment, the box, the bulk as Filling from bulk states, and the note.

Means and a coverage projected from the current year are marked in their cells as Consumption states. By default the rows are ordered by category regardless of case, items without one last, then by article number, items without one after the others and by name regardless of case, then by container (Items).

GET parameters select the items listed: `q` those in whose article number, category or note, or in whose substance's key, name, German name or short name, the text is found regardless of case; `category`, `compartment` and `box` those with that value; `container` those of that size and unit, given as the size without trailing zeros and the unit's code, such as `2.5 mg` or `10 umol`; and `stock` those at that level, a value that names no level selecting every item. The page shows the value of each filter in force, offers each category, container, compartment and box in use, and offers each level with the number of items at it that the other filters admit, linking to the list with those filters and that level.

A user may show, with the list, the details of one item: its article number, name and container; its quantity with its level, and its coverage; its compartment and box, each `nicht hinterlegt` (`not recorded`) when it is not set; each open lot of its substance with its location, or `nicht hinterlegt`, its batch and its amount, linking to the lot's page; its consumption: the current year's so far, the means per year and per quarter, `–` for a mean there is not, and the consumption of each quarter of the current year and of the two years before it, with each year's sum, the quarters to come left empty, and the years whose quarters hold an entered value above zero; its note; and a link to its page, and for a signed-in user the item page's links but `Stornieren` (Item page). `detail=<id>` names the item among those listed; without it, or naming none of them, the details are those of the first item listed, and none when the list is empty. While the details show, a click anywhere in a row without a modifier key, on its links too but not on its check box, chooses its item instead of following a link, and so do the arrow keys up and down; the chosen item's details then show in place of the others, and the address names it in `detail`, so that a reload shows the same item. The row marked as chosen and the address name the item whose details show, also while another item's details are loading and when loading them fails.

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

#### Scenario: Details of an item
- **WHEN** on 2026-11-04 an item `CH-0012` `(E)-Zimtsäure` of 100 mg holding 3 containers has no compartment or box, the entered values 4 for each quarter of 2024 and 6, 5 and 7 for the first three quarters of 2026, and a delivery of 2 dated 2026-10-15, an open lot `B-7` of `50` mg of its substance lies in `Kühlschrank 2`, and a test client requests the list with `detail` naming that item
- **THEN** the details show `CH-0012`, `(E)-Zimtsäure`, `100 mg` and 3 containers with their level, `nicht hinterlegt` for the compartment and the box, `Kühlschrank 2` and `B-7`, linking to the lot's page, the consumption 4, 4, 4, 4 and 16 for 2024, 0, 0, 0, 0 and 0 for 2025, and 6, 5, 7, 2 and 20 for 2026, name 2024 and 2026 as holding entered values, and link to the item's page

#### Scenario: Details of the first item
- **WHEN** the database holds `A-1` in the category `Säuren` and `A-2` in `Ester`, and a test client requests the list, then with `detail` naming no item, then with `category=Säuren` and `detail` naming `A-2`, and then with `category=Basen` and `detail` naming `A-2`
- **THEN** the first two lists show the details of `A-2`, the third those of `A-1`, and the fourth none

#### Scenario: Links in the details
- **WHEN** a signed-in user requests the list with `detail` naming an item without an article number, and a visitor requests it
- **THEN** the user's details link `Artikelnr. eintragen`, `Abfüllen`, `Bestand korrigieren` and `Bearbeiten`, and neither `Abgabe buchen` nor `Verbrauch nachtragen`; the visitor's details hold none of these links

#### Scenario: Another item in place
- **WHEN** a test client requests the list with `category=Ester` holding `A-2` and `A-3`, then, as htmx does, the details the row of `A-3` loads in place, and then the same address without htmx
- **THEN** the second answer holds the details of `A-3` alone, as the list with `detail` naming `A-3` shows them; the third redirects to the list with `detail` naming `A-3`

### Requirement: Consumption heat
The heat of an item's mean per year, and that of its current year's consumption, SHALL be, for a value above zero, `heat-<n>` with `n` being `1 + ⌊5B/N⌋`, where `N` is the number of items whose value of the same kind is above zero and `B` the number of those whose value is smaller. A value of zero, or none, has no heat. The heats run from a pale pink, `heat-1`, through red to a blackish red, `heat-5`; each cell carrying one shows its text with a contrast of at least 4.5:1 to the heat's background in both colour schemes.

#### Scenario: Fifths of the consuming items
- **WHEN** six items' consumption in the current year is 0, 1, 2, 2, 5 and 9 containers, and a test client requests the list, then with `q=` naming the item of 9 alone
- **THEN** their cells of the current year's consumption carry no heat, `heat-1`, `heat-2`, `heat-2`, `heat-4` and `heat-5`, and the cell of the item of 9 carries `heat-5` in the second list too

#### Scenario: Readable in both schemes
- **WHEN** a test reads the heat colours of `lab.css` for the light and the dark scheme
- **THEN** each heat's text and background have a contrast of at least 4.5:1
