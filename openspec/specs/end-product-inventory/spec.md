# end-product-inventory Specification

## Purpose
Count the lab's end products in the lab application: articles, each one substance of the registry with its article number and category; items, an article in containers of one size, kept by batch and changed only by movements, delivery notes current and historical, consumption per quarter with its means and coverage, stock levels, batches of every substance and the vessels that hold them, filling from vessels, their lists, pages and forms, and the admin.
## Requirements
### Requirement: Items
The `inventory` package SHALL keep items, each a container size of an article (Articles), with a change history:

- `article`, fixed once the item is created;
- `size`, a decimal greater than zero with up to three places, and `unit`, one of `mg`, `umol` (shown `µmol`), `g` and `mmol`;
- `quantity`, the whole number of containers left, at least zero, changed only by movements, the sum of the item's shares (Stock by batch);
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
- **WHEN** on 2026-11-04 a signed-in user creates an item with an opening count of 0, fills 3 containers from a vessel of its substance dated 2026-10-20, and fills 2 more dated 2026-11-02
- **THEN** its `stocked_on` is 2026-10-20 and it is new

#### Scenario: Stock entry by the opening count
- **WHEN** on 2026-11-04 a signed-in user creates an item with an opening count of 5, and then gives it the `stocked_on` 2019-05-02 in its edit form
- **THEN** its `stocked_on` was 2026-11-04 and is 2019-05-02, its history records the change, and it is not new

### Requirement: Item movements
Every change of an item's quantity SHALL be a movement holding `kind`, `count`, `quantity_after`, `batch`, `date`, `booked_at`, `user`, `note`, and `delivery_note`, `vessel_movement` and `reverses` where they apply. `batch` is the batch whose share the movement changes, and none for the share of unknown batch (Stock by batch):

- `opening` (`Anfangsbestand`, `Opening count`): the first movement of every item, its `count` the quantity entered on creation, in the batch entered or of unknown batch;
- `delivery` (`Abgabe`, `Delivery`): `count` containers out of the share of the line's batch, more than zero and at most what that share holds after any assignment, booked by a line of the current delivery note `delivery_note` and dated as the note;
- `assignment` (`Zuordnung`, `Assignment`): `count` containers of unknown batch, more than zero, given the batch the movement names. It is booked by a line of the current delivery note `delivery_note`, before that line's delivery, and dated as the note. It leaves the quantity unchanged;
- `filling` (`Abfüllung`, `Filling`): `count` containers in, more than zero, taken from a vessel (Filling from bulk) into the share of the vessel's batch, `vessel_movement` the vessel's filling;
- `correction` (`Korrektur`, `Correction`): `count` the containers counted in the share the movement names, at least zero; the quantity changes by the difference, and a note is required;
- `reversal` (`Storno`, `Reversal`): undoes one delivery or filling, named by `reverses`, adding a delivery's count back to its batch's share or taking a filling's back from its batch's share, and returning a filling's amount to its vessel with a vessel reversal; a movement is reversed at most once, a reversal of a filling is refused when its batch's share holds fewer containers than it took in, and a note is required.

`date` is the day the movement took place, today by default and never after today; `booked_at` is the time it was booked. The quantity and the shares a movement changes are changed by atomic conditional updates in the transaction that stores the movement. Two bookings prepared from the same stock can therefore never take more than a share holds. `quantity_after` is the quantity after those updates. A refused movement changes nothing. Movements are never edited or deleted, in the views or the admin, except that deleting an item in the admin deletes its opening movement with it.

#### Scenario: Delivery
- **WHEN** user `KL` books a delivery note `LS-2026-117` to `Produktion` with one line of 2 containers of the batch `KL0412` of an item holding 5 of that batch
- **THEN** the item has 3, and its newest movement is a delivery of 2 with `quantity_after` 3, by `KL`, naming that note and `KL0412`

#### Scenario: Concurrent deliveries
- **WHEN** two deliveries of 4 of one batch are validated against an item holding 5 of that batch and none of unknown batch, and then stored one after the other
- **THEN** the first is stored, the second is refused, and the item has 1

#### Scenario: Correction needs a note
- **WHEN** a signed-in user posts a correction to 4 without a note
- **THEN** the form shows an error at the note and nothing changes

#### Scenario: Reversing a delivery
- **WHEN** a signed-in user reverses a delivery of 2 dated in the third quarter of 2026, with the note `falsch gebucht`
- **THEN** the item has 2 containers more, in the delivery's batch, the delivery no longer counts in that quarter's consumption, and a second reversal of it is refused

### Requirement: Delivery notes
The `inventory` package SHALL keep delivery notes (`Lieferscheine`), each with a change history: `number`, optional, at most 30 characters, unique among notes when given; `date`, never after today; `recipient`, optional, at most 100 characters; `note`; `historical`; `reversed` and `reversal_note`, the flag of a reversed historical note and the note it was reversed with; `created_by` and `created_at`; and one or more lines, each an item with an article number, a `batch` of the item's substance and a `count` above zero, no item and batch twice in one note. A line of an item without an article number, a line without a batch, and a line whose batch is of another substance are refused, current or historical. A note shows as its number, or as `#<id>` when it has none.

A current note, `historical` off, books for each line an assignment where the line's batch holds too few containers, then one `delivery` movement (Stock by batch), all dated as the note and in one transaction. When one line's count exceeds what its batch and the item's share of unknown batch hold together, the whole note is refused and nothing changes. A historical note, `historical` on, records deliveries made before they could be booked, such as those of old paper delivery notes: its lines change no quantity. A historical note is refused when one of its lines' items has an entered consumption value for the quarter of the note's date, and an entered value is refused for a quarter in which the item has lines of a historical note that is not reversed. A signed-in user may mark a historical note reversed, with a required note; a current note's lines are reversed one by one through their movements, and the note shows as reversed when all its lines are, and as partly reversed when some are. A note's date, kind and lines are fixed once it is created, its number, recipient and note may be edited, and no note is deleted, in the views or the admin.

#### Scenario: Note with several lines
- **WHEN** a signed-in user books a current note with 2 containers of the batch `KL0412` of one item holding 5 of it, and 3 of the batch `KL0420` of another item holding 3 of it
- **THEN** both items are reduced, to 3 and 0, and the note lists both lines with their batches

#### Scenario: One line too many refuses the note
- **WHEN** a signed-in user books a current note with 2 containers of a batch of an item holding 5 of it, and 4 of a batch of an item holding 3 of it and none of unknown batch
- **THEN** the form shows an error at the second line, no note exists, and both items keep their quantities

#### Scenario: Historical note
- **WHEN** a signed-in user enters a historical note dated 2025-03-12 with 4 containers of the batch `KL0412` of an item holding 5 that has no entered value for the first quarter of 2025
- **THEN** the item still has 5, and its consumption in the first quarter of 2025 is 4

#### Scenario: Historical note in a quarter with an entered value
- **WHEN** an item has the entered value 6 for the first quarter of 2025 and a signed-in user enters a historical note dated 2025-03-12 with a line of that item
- **THEN** the form shows an error at that line and nothing is saved

#### Scenario: First delivery needs the article number
- **WHEN** an item without an article number holds 5 containers and a signed-in user posts a current note with a line of 2 of it
- **THEN** the form shows an error at that line, no note exists and the item keeps 5

#### Scenario: Two batches of one item
- **WHEN** a signed-in user books a current note with 2 containers of `KL0412` and 1 of `KL0413` of one item, and then posts another note with two lines of 1 of `KL0412` of that item
- **THEN** the first note has both lines, and the second form shows an error at its second line and saves nothing

#### Scenario: One of two batch lines reversed
- **WHEN** a current note dated in the third quarter of 2026 delivers 2 containers of `KL0412` and 3 of `KL0413` of one item, and a signed-in user reverses the delivery of `KL0412`
- **THEN** the item's consumption in that quarter is 3, the note shows as partly reversed, and on its page only the line of `KL0412` shows `storniert`

#### Scenario: A batch of another substance
- **WHEN** a signed-in user posts a note with a line of an item of `cinnamic-acid` naming a batch of `acetophenone`, current or historical
- **THEN** the form shows an error at that line's batch and nothing is saved

### Requirement: Consumption
An item SHALL keep entered consumption per quarter, with a change history (web-app "Change history"), a whole number of containers of at least zero for a year and a quarter 1 to 4, not after the current quarter, at most one per quarter; entering a value replaces the quarter's earlier one, and entering none removes it. Entering a value for an item without an article number is refused, zero included. A quarter's consumption is its entered value, zero when there is none, plus the counts of the item's lines, in notes current or historical, dated in it, leaving out reversed movements and reversed historical notes. Quarters and years follow the calendar in `Europe/Berlin`.

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

### Requirement: Filling from bulk
Filling an item SHALL name an open vessel of its substance and the amount taken from it, in the vessel's unit; a filling without a vessel is refused. The proposed amount is the count times the item's size, converted into the vessel's base unit and rounded half up to six places, shown in the vessel's unit. The filling form has, besides its button to book, a button `Menge vorschlagen` (`Propose amount`), which books nothing and shows the form again with the values entered and the amount set to the proposal for the count and vessel entered. When the amount is left empty, the proposed amount is booked. Units of the same kind convert by their factors: 1 g is 1000 mg, and 1 mmol is 1000 µmol. Mass and amount of substance convert through the molar mass of the item's substance in g/mol. Without that molar mass across kinds, nothing is proposed, the amount is required, and `Menge vorschlagen` shows an error at the amount. The item's filling and the vessel's filling are stored in one transaction. An amount above the vessel's, or one that rounds to zero, refuses both.

An item's bulk is the amount in the open vessels of its substance, flasks among them. Wherever an item shows its bulk, it shows that amount by unit and the number of its containers the vessels would still fill. That number is, for each open vessel that converts into the item's unit, its amount converted and divided by the size and rounded down, summed over the vessels. A vessel that does not convert is left out of that number and counted as not convertible.

#### Scenario: Filling with conversion
- **WHEN** an item `CH-0012` of 10 µmol, whose substance has the molar mass 148.16, has a vessel of `50` mg, and a signed-in user fills 5 containers from it
- **THEN** `Menge vorschlagen` shows the form with the amount `7,408` and books nothing; booking it gives the item 5 more containers, the vessel holds `42,592` mg, and the item's movement names the vessel's movement

#### Scenario: Small filling from a vessel in grams
- **WHEN** an item `CH-0012` of 10 µmol, whose substance has the molar mass 148.16, has a vessel of `1` g, and a signed-in user fills 1 container from it, leaving the amount empty
- **THEN** the vessel holds 998,5184 mg, shown as `0,999` g

#### Scenario: No filling without a vessel
- **WHEN** a signed-in user posts the filling form of an item with the count 3 and no vessel
- **THEN** the form shows an error at the vessel and the item keeps its quantity

#### Scenario: Containers from bulk
- **WHEN** an item `CH-0012` of 10 µmol, whose substance has the molar mass 148.16, has one open vessel of `50` mg
- **THEN** it shows `50 mg` and 33 containers

#### Scenario: Vessels are not pooled
- **WHEN** an item of 10 mg has two open vessels of `6` mg
- **THEN** it shows 0 containers from bulk

### Requirement: Item list
`/lab/inventory/end-products/` SHALL list the items under the heading `Endprodukte` (`End products`), followed by the number of all items; `/lab/inventory/` redirects to it. It shows them in one of two views, `Tabelle` (`Table`) and `Details` (`Details`). Its table has the base columns, which both views show, first, in this order, and which no user can hide:

- the article number, linking to the item's page;
- the name, linking to the substance's page (lab-registry "Registry pages") when the item has an article number and to the item's page when it has none, followed by the mark `neu` (`new`), a `sup.mark-new`, for a new item;
- the category;
- the container;
- the quantity, its cell carrying its level as Stock levels states.

After them come the table view's own columns, which the table view alone shows and of which a user may hide each:

- the mean per year and the current year's consumption, each cell carrying its heat as Consumption heat states;
- the coverage;
- the compartment, the box, the bulk as Filling from bulk states, and the note.

A base column is as wide in one view as in the other. Means and a coverage projected from the current year are marked in their cells as Consumption states. By default the rows are ordered by category regardless of case, items without one last, then by article number, items without one after the others and by name regardless of case, then by container (Items).

GET parameters select the items listed: `q` those in whose article number, category or note, or in whose substance's key, name, German name or short name, the text is found regardless of case; `category`, `compartment` and `box` those with that value; `container` those of that size and unit, given as the size without trailing zeros and the unit's code, such as `2.5 mg` or `10 umol`; and `stock` those at that level, a value that names no level selecting every item. The page shows the value of each filter in force, offers each category, container, compartment and box in use, and offers each level with the number of items at it that the other filters admit, linking to the list with those filters and that level.

A user switches between the views; the browser remembers the view last chosen in the cookie `item-list-view`, `table` or `details`, and the list opens in that view, in the table view without it or with another value. The address does not name the view.

One item listed is selected: the one `selected=<id>` names among those listed; without it, or naming none of them, the first item listed, and none when the list is empty. The selected row is marked in both views. In either view, a click without a modifier key in a row, but not on its links or its check box, selects its item, and so do the arrow keys up and down; a link in a row leads where it links. Selecting an item loads its details in place; once they have arrived its row is marked and the address names it in `selected`, so that a reload selects the same item. The marked row and the address name the item whose details the list holds, also while another item's details are loading and when loading them fails. Filtering the list and changing its order keep the selected item while the list still holds it.

The details view shows, beside the base columns, the details of the selected item: its article number, name and container; its quantity with its level, and its coverage; its compartment and box, each `nicht hinterlegt` (`not recorded`) when it is not set; each open vessel of its substance with its location, or `Kolben` for a flask without one, or `nicht hinterlegt`, its batch and its amount, linking to the vessel's page; its consumption: the current year's so far, the means per year and per quarter, `–` for a mean there is not, and the consumption of each quarter of the current year and of the two years before it, with each year's sum, the quarters to come left empty, and the years whose quarters hold an entered value above zero; its note; and a link to its page, and for a signed-in user the item page's links but `Stornieren` (Item page).

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

#### Scenario: Base columns first
- **WHEN** a test client requests the list
- **THEN** each row's cells hold, in this order, the article number, the name, the category, the container and the quantity, then the table view's own columns, and every cell of those is marked as the table view's

#### Scenario: Columns a user may hide
- **WHEN** a test client requests the list
- **THEN** the list offers to hide the mean per year, the current year's consumption, the coverage, the compartment, the box, the bulk and the note, and none of the base columns

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

### Requirement: Delivery list
`/lab/inventory/deliveries/` SHALL list the delivery notes, under the heading `Endprodukte` (End product layers), newest date first, then newest booking first, each with its number linking to its page, date, recipient, the mark `nachgetragen` (`entered later`) on a historical note and `storniert` (`reversed`) on a reversed one, and its lines with article number, name, size, batch and count; a current note shows `storniert` when all its lines are reversed and `teilweise storniert` (`partly reversed`) when some are. GET parameters filter it and keep their values: `q`, text found regardless of case in the number or recipient, and `item`, an item's id. The list shows its notes in the views `Tabelle` and `Details`, remembered in the cookie `delivery-list-view`, with one note selected by `selected=<id>`, as the item list does with its items: the table view shows each note with its lines; the details view shows beside a table of each note's number, date, recipient, number of lines and a short summary of them the selected note as its page shows it, with its marks, lines and a link to its page. `/lab/inventory/deliveries/<id>/` shows one note with its lines, each with the article number, name, size, batch, linking to its page, compartment, box and count, their movements and the change history, and an unknown id answers 404. A signed-in user sees a link `Neuer Lieferschein` (`New delivery note`).

#### Scenario: Deliveries of one item
- **WHEN** two notes have lines of an item and a third does not, and a test client requests the list with that item's id
- **THEN** it lists the two notes, the newer first

#### Scenario: A pick list
- **WHEN** a note has a line of an item kept in compartment `2`, box `7`, and a test client requests the note's page
- **THEN** the line shows `2` and `7` in the columns `Fach` and `Box`

#### Scenario: Lines name their batch
- **WHEN** a note has a line of 2 containers of the batch `KL0412`, and a test client requests the note's page and the delivery list
- **THEN** both show `KL0412` in that line, linking on the note's page to the batch's page

#### Scenario: A note in the details view
- **WHEN** a note `LS-2026-156` has lines of `CH-0013` and `CH-0016`, and a test client with the cookie `delivery-list-view` set to `details` requests the delivery list with `selected` naming it
- **THEN** the details show `LS-2026-156`, both lines with their batches and counts, and a link to the note's page

### Requirement: Item page
`/lab/inventory/items/<id>/` SHALL show the article number and name as heading, or the name alone for an item without an article number, followed by the mark `neu` for a new item; the substance, linking to its page; the category, size and note; the `status` when it is not `active`; the `stocked_on`, `–` when there is none; the compartment and the box, `–` for each that is not set; the quantity with its level; its containers by batch (Stock by batch): each batch holding containers of the item, linking to its page, with their count, then `unbekannt` (`unknown`) with the containers of unknown batch when there are any; the means and coverage; the current year's consumption; a chart of the consumption of each quarter of the two complete years before the current one and of the current year, an inline `svg` with one bar per quarter titled with the quarter and its value and, when the item has a mean, a line at the mean per quarter, followed by a table of each quarter's entered value, deliveries and total, in which a signed-in user sees beside each quarter's entered value a link to the consumption form for that quarter (Inventory forms), `Ändern` (`Change`) where the quarter has an entered value and `Nachtragen` (`Enter`) where it has none, except on the page of an item without an article number, beside a quarter that has not begun, and beside a quarter that holds lines of a historical note that is not reversed (Consumption), and each such link opens its form in a dialog over the page (web-app "Form dialogs"); the movements in booking order, newest first, with date, booking time, kind, count, quantity after, batch, linking to its page or `unbekannt` for the share of unknown batch, the user's initials, the delivery note with its number and recipient, the note, and the mark `storniert` (`reversed`) on a reversed movement; its bulk (Filling from bulk): the open vessels of its substance, each with its batch and amount and linking to its page, and the number of containers they would fill; under `Prognose` (`Forecast`), the item's forecast, as `production-planning` states under Item forecast; and the change history, which includes that of the item's entered consumption: each entry, change and removal of a quarter's value, headed `Verbrauch Q<quarter> <year>` (`Consumption Q<quarter> <year>`), with the old and new count, `–` standing for none; the entries of item and entered consumption are shown together, newest first, and of entries made at the same moment those of the entered consumption first. A signed-in user sees the links `Abgabe buchen` (`Book delivery`), to the new delivery note with the item in its first line, `Abfüllen` (`Fill`), `Bestand korrigieren` (`Correct count`), `Verbrauch nachtragen` (`Enter consumption`), `Bearbeiten` (`Edit`), and `Stornieren` (`Reverse`) beside each delivery and filling not yet reversed; for an item without an article number, `Artikelnr. eintragen` (`Enter article number`), to its edit form, takes the place of `Abgabe buchen`, and `Verbrauch nachtragen` is left out. An unknown id answers 404.

#### Scenario: Chart and ledger
- **WHEN** on 2026-11-04 a test client requests the page of an item with entered values for three quarters of 2025 and two deliveries in 2026
- **THEN** the `svg` has twelve bars, the table lists the same values, and the movements list the deliveries before the opening count

#### Scenario: Page of a position without an article number
- **WHEN** a signed-in user requests the page of an item of 10 mg of the substance `new-compound-9`, named `Neuverbindung 9`, without an article number
- **THEN** its heading is `Neuverbindung 9`, its substance links to `/lab/registry/substances/new-compound-9/`, and it links `Artikelnr. eintragen` to its edit form and has neither `Abgabe buchen` nor `Verbrauch nachtragen`

#### Scenario: A discontinued size
- **WHEN** a test client requests the page of an item with the `status` `discontinued`, 4 containers and the `stocked_on` 2024-03-01
- **THEN** it shows `auslaufend`, `01.03.2024`, and 4 with the class `level-dormant` and the text `ruhend`

#### Scenario: Changing a quarter's entered value
- **WHEN** on 2026-11-04 a signed-in user requests the page of an item with an article number that has the entered value 40 for the third quarter of 2026, the entered value 0 for the second quarter of 2025, no value for the second quarter of 2026, and a historical note with a line of the item dated in the first quarter of 2026
- **THEN** the row of the third quarter of 2026 links `Ändern` to `/lab/inventory/items/<id>/consumption/?year=2026&quarter=3`, the second quarter of 2025 links `Ändern` to the form for it, the second quarter of 2026 links `Nachtragen` to the form for it, the first quarter of 2026 has no such link, and each link opens in a dialog

#### Scenario: History of entered consumption
- **WHEN** user `KL` enters 400 for the third quarter of 2026 of an item, then changes the item's note, then enters 40 for the same quarter, then removes it, and a test client requests the item's page
- **THEN** its history holds, newest first, an entry headed `Verbrauch Q3 2026` changing the count from 40 to `–`, one changing it from 400 to 40, the item's change of its note, and one headed `Verbrauch Q3 2026` changing the count from `–` to 400, each naming `KL`

#### Scenario: Containers by batch
- **WHEN** an item holds 3 containers of `KL0412`, none of `KL0413` and 2 of unknown batch, and a test client requests its page
- **THEN** its containers by batch are `KL0412` with 3, linking to the batch's page, and `unbekannt` with 2, and `KL0413` is not among them

### Requirement: Inventory forms
For a signed-in user, the application SHALL offer:

- `/lab/inventory/end-products/new/`: a new item with its opening count and the batch it is of, optional, chosen among the batches of every substance, grouped under their substance's name as on a delivery note's row, none standing for unknown batch; its substance by key; the article number, optional, and the category with a `datalist` of the categories in use, the `stocked_on`, optional, left empty for the opening count to set, and the compartment and the box, each with a `datalist` of the values in use;
- `/lab/inventory/items/<id>/edit/`: the item's note, `status`, `stocked_on`, compartment and box, the last two each with a `datalist` of the values in use, and its article's category and, while the article has none, its article number, both saved on the article for every size of it, as the form says beside them;
- `/lab/inventory/deliveries/new/`: a delivery note with ten rows for lines, each offering the items with an article number, each shown as its article number, container and name and, where they are set, `Fach <compartment>` and `Box <box>` (`Compartment <compartment>`, `Box <box>`), joined by ` · ` and the locations by ` / `, and the batches of the substances of the items it offers, grouped under their substance's name, each shown as the batch shows; a row with only some of item, batch and count is refused at the field missing, and rows left empty are ignored; and a check box `nachgetragen – Bestand bleibt unverändert` (`entered later – stock unchanged`) for a historical note; `?item=<id>`, given once or several times, puts those items in the first rows in the order given, up to ten, leaving out ids of items it does not offer and ids given twice;
- `/lab/inventory/deliveries/<id>/reverse/`: marking a historical note reversed, with its note;
- `/lab/inventory/items/<id>/fill/`: a filling, its vessel chosen among the open vessels of the item's substance, or given as `?vessel=<id>`, which chooses that vessel when the form offers it, each offered as the vessel, its kind, its location where it has one, and its amount, joined by ` · `; and `/lab/inventory/items/<id>/correct/`: a correction of one share, chosen among the batches of the item's substance, each with the item's containers of it, and `unbekannt` (`unknown`) with its containers of unknown batch, the default;
- `/lab/inventory/items/<id>/movements/<movement id>/reverse/`: the reversal of a delivery or filling, with its note;
- `/lab/inventory/items/<id>/consumption/`: the entered value of a year and quarter, replacing an earlier one of that quarter, or removing it when left empty; `?year=<year>&quarter=<quarter>`, naming a quarter that has begun, fixes the form to that quarter, which it names in place of the fields for the year and the quarter, and fills in its entered value, zero included, naming it as the value a save replaces, or leaves the count empty where the quarter has none; other values of the two parameters are ignored, and the form opens as without them; beside its fields the form shows the item's consumption as the item page does, its chart and its table of quarters with their links, a link choosing its quarter in the form;
- `/lab/inventory/deliveries/<id>/edit/`: a note's number, recipient and note;
- `/lab/inventory/batches/new/`: a new batch with its substance by key; its source, `hergestellt` when none is chosen; for a made batch its number and its journal entry, given as `<code>/<number>` as a task step names one (task-tracker "Task page"); for a bought batch its supplier, the supplier's article number and the supplier's batch; its date, today by default; its note; and an amount, its unit and a location, with a `datalist` of the locations in use, that open the batch's first vessel, a stored one, when the amount is given. `?substance=<key>` fills in the substance, and `?source=bought` chooses `gekauft`. `?step=<id>` records a batch made by that task step: the source is `hergestellt`, the substance is filled in with the first product of the step's entry, or the task's substance for a step without one, and a substance the step does not make is refused; the journal entry is the step's, shown and not editable, when the step names one; and the amount is required and is the batch's yield, opening a flask when no location is given and a stored vessel at the location given. A step whose task is neither planned nor running, a number another made batch has regardless of case, a number on a bought batch, an amount without its unit, and a journal entry whose code is no notebook's are refused;
- `/lab/inventory/batches/<id>/edit/`: the number, journal entry and yield of a made batch, the supplier, supplier's article number and supplier's batch of a bought one, and the date and note;
- `/lab/inventory/batches/<id>/vessels/new/`: a new stored vessel of the batch with its opening amount, its unit, its location, with the `datalist` of the locations in use, and its note;
- `/lab/inventory/vessels/<id>/withdraw/`: a withdrawal from an open vessel into a step of a task that is planned or running, chosen among those tasks' steps or given as `?step=<id>`, with the amount in the vessel's unit and the date; an amount above the vessel's is refused;
- `/lab/inventory/vessels/<id>/transfer/`: a transfer from an open vessel, with the amount in the source vessel's unit, the date and a note, into a stored vessel of the same batch, chosen among them, or into a new vessel at the location given; an amount above the vessel's, and a target whose unit converts from the source's only through a molar mass the substance lacks, are refused, the latter with an error at the target;
- `/lab/inventory/vessels/movements/<id>/reverse/`, a POST: reverses a withdrawal not yet reversed;
- `/lab/inventory/vessels/<id>/edit/`, for the location and note and, for a vessel of a bought batch, its `opened_on`, which may be emptied to mark it sealed, and `/lab/inventory/vessels/<id>/correct/`.

The withdrawal, transfer, correction and edit forms of a vessel open in a dialog over the page where a list offers them so (Lists by substance); the vessel's page links them as pages, as before.

A batch of another substance than the item's is refused at the batch, on the new-item form and in a delivery note's row. With the page's script, a delivery note's row offers only the batches of the substance of the item chosen in it, and the new-item form only those of the substance entered, and a batch chosen that is no longer offered is cleared; without the script, every batch stays offered. A substance is named by its key, offered through a `datalist` of every substance's key labelled with its name; an unknown key is an error at the field. On the new-item form, the article number and the category make the substance's article when it has none, an empty number giving it none. When the substance has an article, a field left empty leaves the article's value as it is; a category entered replaces the article's; an article number entered gives the article that number when it has none, as the edit form does, and must otherwise be its number, or the form shows an error at it. On the edit form, the category field holds the article's category and saves what it holds, empty included, and the article number, offered only while the article has none, gives it one when entered and leaves it without one when empty. Invalid input shows the form again with the errors beside their fields and saves nothing. A saved form leads, with a message naming the record, to the page of the delivery note for the forms of notes, to the page of the batch for the new-batch form, and to the page of the item, batch or vessel for every other; a form saved in a dialog leaves the page it was opened from in place instead. On an item's page and in the item list's details, the links to the item's edit form, its filling, its count correction and its consumption, and on its page each link `Stornieren` beside a movement, open those forms in a dialog over the page (web-app "Form dialogs"); `Abgabe buchen` leads to the new delivery note's form page.

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

#### Scenario: A batch from a step
- **WHEN** on 2026-11-04 a signed-in user requests `/lab/inventory/batches/new/?step=<id>` for the last step of a running task of `cinnamic-acid`, a step that names the journal entry `AE-1/9`
- **THEN** the form holds the substance `cinnamic-acid`, the source `hergestellt`, the date 2026-11-04 and the journal entry `AE-1/9`, not editable, and posting it without an amount shows an error at the amount

#### Scenario: Vessels offered for a filling
- **WHEN** an item of `CH-0012` has an open flask of the batch `KL0412` holding `2` g and a used-up vessel of another batch, and a signed-in user requests the item's filling form
- **THEN** it offers the flask alone, as `KL0412 #<id> · Kolben · 2 g`

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

#### Scenario: Item forms as dialogs
- **WHEN** a signed-in user requests the item list with an item's details and that item's page
- **THEN** in the details and on the page, the links `Abfüllen`, `Bestand korrigieren`, `Verbrauch nachtragen` and `Bearbeiten`, and on the page each `Stornieren`, open their forms in a dialog, and `Abgabe buchen` does not

#### Scenario: The form for a quarter
- **WHEN** an item has the entered value 400 for the third quarter of 2026, and a signed-in user requests its consumption form with `?year=2026&quarter=3`
- **THEN** the form names the quarter `Q3 2026` and has no field for the year or the quarter, holds the count 400, names 400 as the value a save replaces, and shows the item's chart and its table of quarters, the third quarter's row linking `Ändern` to the form for that quarter; the same request with `?year=2026&quarter=9` opens the form with fields for the year and the quarter and no value named

#### Scenario: Opening count of a batch
- **WHEN** a signed-in user posts an item of the substance `cinnamic-acid` with an opening count of 4 and the batch `KL0412` of `cinnamic-acid`, and then another of another size naming a batch of `acetophenone`
- **THEN** the first item holds 4 containers of `KL0412`, and the second form shows an error at the batch and saves nothing

#### Scenario: Batches narrowed to the item
- **WHEN** a signed-in user's browser runs the page's script on the new delivery note form, and the user chooses in a row an item of `cinnamic-acid` after choosing a batch of `acetophenone`
- **THEN** the row's batch choice offers the batches of `cinnamic-acid` alone, and no batch is chosen

#### Scenario: A row needs its batch
- **WHEN** a signed-in user posts a delivery note with a row holding an item and a count and no batch
- **THEN** the form shows an error at that row's batch and nothing is saved

#### Scenario: Shares offered for a correction
- **WHEN** an item holds 3 containers of `KL0412` and 2 of unknown batch, its substance has the batch `KL0413` too, and a signed-in user requests its correction form
- **THEN** it offers `unbekannt` with 2, chosen, `KL0412` with 3 and `KL0413` with 0

#### Scenario: Opening date entered and cleared
- **WHEN** on 2026-11-24 a signed-in user posts the edit form of a sealed vessel of a bought batch with the `opened_on` 2026-11-10, then with 2026-11-25, then with the field empty
- **THEN** the vessel has the `opened_on` 2026-11-10 after the first, the form shows an error at the field and the vessel keeps 2026-11-10 after the second, and the vessel is sealed after the third

#### Scenario: Goods receipt
- **WHEN** a signed-in user requests `/lab/inventory/batches/new/?substance=benzaldehyde&source=bought`
- **THEN** the form has the substance `benzaldehyde` and the source `gekauft` filled in

### Requirement: Inventory in the admin
The admin SHALL list articles, items, batches, vessels, delivery notes and the movements for staff, with search by article number and by the substance's key and names, and the change history of each record. It shows movements, delivery notes' dates, kinds and lines, an item's shares (Stock by batch), and the fixed fields read-only, an article's number among them once it has one; an article number entered there is given as the edit form gives it, only while the article has none. It deletes no movement or delivery note, deletes an article only while it has no items, deletes an item or vessel only while its one movement is the opening and, for an item, no delivery note has a line of it, and deletes a batch only while no vessel, share, delivery line or movement names it and no task step made it.

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
The heat of an item's mean per year, and that of its current year's consumption, SHALL be, for a value above zero, `heat-<n>` with `n` being `1 + ⌊5B/N⌋`, where `N` is the number of items whose value of the same kind is above zero and `B` the number of those whose value is smaller. A value of zero, or none, has no heat. The heats run from a pale pink, `heat-1`, through red to a blackish red, `heat-5`; each cell carrying one shows its text with a contrast of at least 4.5:1 to the heat's background in both colour schemes.

#### Scenario: Fifths of the consuming items
- **WHEN** six items' consumption in the current year is 0, 1, 2, 2, 5 and 9 containers, and a test client requests the list, then with `q=` naming the item of 9 alone
- **THEN** their cells of the current year's consumption carry no heat, `heat-1`, `heat-2`, `heat-2`, `heat-4` and `heat-5`, and the cell of the item of 9 carries `heat-5` in the second list too

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

### Requirement: Batches
The `inventory` package SHALL keep batches (`Chargen`), each a quantity of one substance with one origin, with a change history:

- `substance`, a substance of the registry;
- `source` (`Herkunft`, `Source`), `made` (`hergestellt`, `made`) or `bought` (`gekauft`, `bought`);
- for a made batch: `number` (`Charge`, `Batch`), required, at most 30 characters, unique among made batches regardless of case and of their substance; `journal_entry` (`Laborjournal`, `Lab notebook`), the journal entry it is written down in (lab-journal "Notebooks and entries"), or none; `task_step`, the task step that made it, or none: a step whose entry has the batch's substance among its products, or, for a step without an entry, whose task makes the batch's substance; and `yield` (`Ausbeute`, `Yield`), an amount above zero in one of the units `mg`, `g`, `umol` and `mmol`, or none;
- for a bought batch: `supplier` (`Lieferant`, `Supplier`), at most 100 characters, and `supplier_article_number` (`Artikelnr. des Lieferanten`, `Supplier's article no.`) and `supplier_batch` (`Charge des Lieferanten`, `Supplier's batch`), at most 50 characters each, each optional; a bought batch has no number, journal entry, step or yield;
- `date` (`Datum`, `Date`), the day it was made or received, or none, never after today;
- `note`.

The substance, source and `task_step` are fixed once the batch exists. A batch may be of any substance, intermediates and commercial chemicals among them, and one substance may have made and bought batches side by side; a journal entry may be named by no batch, one or several. A batch shows as its number, a bought batch as its supplier's batch number, and either, when it has none, as `#<id>`. A batch is recorded from a task step only while the step's task is planned or running, and then names the step's journal entry when the step names one. Its yield shows in its unit to three decimal places, rounded half up. A batch that has vessels, or that a task step made, cannot be deleted, except by `demo_data --replace` (lab-demo "Demo data command").

#### Scenario: Made and bought batches
- **WHEN** a signed-in user records a batch of `cinnamic-acid` made in the lab with the number `KL0412FA`, and another bought from `Sigma` with the supplier's article number `C80857` and the supplier's batch `MKCK1234`
- **THEN** both batches exist with their sources, the first showing as `KL0412FA` and the second as `MKCK1234` with its supplier and article number

#### Scenario: Numbers unique regardless of case
- **WHEN** a made batch `KL0412FA` of `cinnamic-acid` exists and a signed-in user records a made batch of `acetophenone` with the number `kl0412fa`
- **THEN** the form shows an error at the number and no batch is created

#### Scenario: Fractions of one entry
- **WHEN** the first step of a running task following `SEQ-0002` names the journal entry `CE-3/2`, and a signed-in user records from that step two batches of `4-acetylbiphenyl`, `CE3002FA` and `CE3002FB`, and then one of `cinnamic-acid`
- **THEN** the first two exist, each made by that step and naming `CE-3/2`, and the third is refused with an error at the substance

#### Scenario: Not from an ended task
- **WHEN** a signed-in user posts the new-batch form for a step of an ended task
- **THEN** the form shows an error and no batch is created

### Requirement: Vessels
The `inventory` package SHALL keep vessels (`Gefäße`), each a weighed amount of one batch in one place, with a change history: `batch`; `unit`, one of `mg`, `g`, `umol` and `mmol`, in which the vessel is entered and shown; `amount`, at least zero, kept in the vessel's base unit, `mg` for `mg` and `g` and `µmol` for `µmol` and `mmol`, with six decimal places; `flask` (`Kolben`, `Flask`), whether it is its batch's reaction flask; `location` (`Ort`, `Location`), optional, at most 100 characters; `opened_on` (`Angebrochen am`, `Opened on`), for a vessel of a bought batch, the day it was first opened, or none while it is sealed (`versiegelt`, `sealed`), never after today, and none for a vessel of a made batch; and `note`. The batch, unit and `flask` are fixed once the vessel exists. A vessel's substance is its batch's, and a vessel belongs to every item of its substance's article, when the substance has one. Its amount shows in its unit to three decimal places, rounded half up. A vessel at zero is used up, and one above zero is open. A vessel of a bought batch opens sealed, unless a transfer makes it: a vessel a transfer makes is opened on the transfer's date. The first filling, withdrawal or transfer out of a sealed vessel sets its `opened_on` to that movement's date in the transaction that books it; a correction, and the reversal of the movement, leave it as it is. A vessel shows as its batch followed by `#<id>`.

A flask is made only by recording a batch from a task step with its yield and without a location (Inventory forms), and a batch has at most one; every other vessel is stored. A vessel's kind (`Art`, `Kind`) is `Kolben` (`Flask`) for a flask; for a stored vessel it is `Endprodukt` (`End product`) when its substance has an article, else `Zwischenprodukt` (`Intermediate`) when its batch is made and `Handelschemikalie` (`Commercial chemical`) when it is bought.

Its amount changes only by its movements, each holding `kind`, `amount`, `amount_after`, `date`, `booked_at`, `user`, `note`, and `task_step`, `transfer` and `reverses` where they apply, by one atomic conditional update in the transaction that stores the movement, as for items:

- `opening` (`Anfangsmenge`, `Opening amount`), the amount the vessel opens with: its batch's yield, or an amount entered;
- `filling` (`Abfüllung`, `Filling`), the amount taken into an item's containers, more than zero and at most the vessel's amount;
- `withdrawal` (`Entnahme`, `Withdrawal`), the amount taken into a task step, named by `task_step`, more than zero and at most the vessel's amount;
- `transfer_out` (`Umfüllung (Abgang)`, `Transfer out`) and `transfer_in` (`Umfüllung (Zugang)`, `Transfer in`), an amount passed from one vessel to another of the same batch, more than zero and at most the source's amount, booked together, the `transfer_in` naming the `transfer_out` as `transfer`; the target is a stored vessel, or a new stored vessel in the source's unit, whose first movement the `transfer_in` is; the `transfer_out` holds the amount in the source's base unit and the `transfer_in` that amount converted into the target's, rounded half up to six places, a transfer whose converted amount rounds to zero being refused whole, units converting as for a filling (Filling from bulk), and a transfer between a mass and an amount of substance is refused when the substance has no molar mass;
- `correction` (`Korrektur`, `Correction`), the amount weighed, with a required note;
- `remainder` (`Restausbuchung`, `Remainder written off`), a flask's whole amount, booked when the task of its batch's step ends, fails or is cancelled (task-tracker "Task record");
- `reversal` (`Storno`, `Reversal`), the amount a reversed filling or withdrawal returns, the withdrawal named by `reverses`, each withdrawal reversed at most once.

A flask whose task is ended, failed or cancelled stays at zero: a correction of it, and the reversal of a filling or withdrawal from it, are refused. Recording a batch from a step and every booking on a flask check the task's state in the transaction that books, so that one prepared while the task was open and stored after it closed is refused and changes nothing; on PostgreSQL this holds for bookings and closures that overlap. Vessel movements are never edited or deleted, except that deleting a vessel in the admin deletes its opening movement with it, and `demo_data --replace` deletes every vessel with its movements.

#### Scenario: Yield into the flask
- **WHEN** a signed-in user records from the last step of a running task of `cinnamic-acid` a batch `KL0412` with the amount `2` g and no location
- **THEN** the batch's yield is `2` g, and its one vessel is a flask holding `2` g whose only movement is the opening

#### Scenario: Yield stored at once
- **WHEN** a signed-in user records the same batch with the location `Kühlschrank 2`
- **THEN** its one vessel is stored in `Kühlschrank 2`, of the kind `Endprodukt`, holding `2` g, and the batch has no flask

#### Scenario: Transfer into a new vessel
- **WHEN** the flask of `KL0412` holds `2` g and a signed-in user transfers `1,5` g from it into a new vessel in `Kühlschrank 2`
- **THEN** the flask holds `0,5` g and the new vessel `1,5` g, whose only movement is a `transfer_in` naming the flask's `transfer_out`

#### Scenario: Transfer across units
- **WHEN** a batch of `cinnamic-acid`, whose molar mass is 148.16, has a flask in `mg` holding `1000` mg and a stored vessel in `µmol` holding `100` µmol, and a signed-in user transfers `148,16`, in the flask's unit, from the flask into that vessel
- **THEN** the flask holds `851,84` mg and the vessel `1100` µmol

#### Scenario: Transfer without a molar mass
- **WHEN** a batch of a substance without a molar mass has a flask in `mg` and a stored vessel in `µmol`, and a signed-in user posts a transfer from the flask into that vessel
- **THEN** the form shows an error at the target and neither vessel changes

#### Scenario: A closed task's flask stays empty
- **WHEN** 5 containers of an item were filled from the flask of a batch whose task has since ended, and a signed-in user reverses that filling, and then corrects the flask to `1` g with a note
- **THEN** both are refused with an error, the item keeps its containers and the flask holds nothing

#### Scenario: Correction of a vessel
- **WHEN** a signed-in user corrects a vessel of `50` mg to `47,5` mg with the note `nachgewogen`
- **THEN** the vessel holds `47,5` mg and its newest movement is that correction

#### Scenario: Withdrawal and its reversal
- **WHEN** a signed-in user withdraws `500` mg of a vessel holding `2` g into a step of a running task, and then reverses the withdrawal
- **THEN** the vessel holds `1,5` g after the withdrawal and `2` g after the reversal, the withdrawal names the step, the reversal names the withdrawal, and reversing it again is refused

#### Scenario: Kinds of vessels
- **WHEN** the database holds the flask of a made batch of `cinnamic-acid`, a stored vessel of the same batch, a stored vessel of a made batch of `acetophenone`, which has no article, and one of a bought batch of `acetophenone`
- **THEN** their kinds are `Kolben`, `Endprodukt`, `Zwischenprodukt` and `Handelschemikalie`

#### Scenario: A bought bottle is opened by its first withdrawal
- **WHEN** a signed-in user records a batch of `acetophenone` bought from `Sigma` with `100` g in `Chemikalienschrank 1`, then on 2026-11-20 withdraws `5` g of its vessel into a step of a running task, and on 2026-11-22 another `5` g
- **THEN** the vessel was sealed after the receipt and has the `opened_on` 2026-11-20 after both withdrawals

#### Scenario: A made vessel is never sealed
- **WHEN** a signed-in user posts the edit form of a stored vessel of a made batch with the `opened_on` 2026-11-20
- **THEN** the vessel keeps no `opened_on`

### Requirement: Batch list
`/lab/inventory/batches/` SHALL list the batches, of every substance, with the columns `Charge`, `Name`, `Artikelnr.`, `Herkunft`, `Laborjournal`, `Datum`, `Ausbeute` and `Bestand` (`Batch`, `Name`, `Article no.`, `Source`, `Lab notebook`, `Date`, `Yield`, `Stock`): the batch as it shows, linking to its page; its substance's name, linking to the substance's page; the article number of the substance's article, empty when there is none; the source, `hergestellt` followed for a batch made by a step by its task's number linking to the task's page, or `gekauft` followed by the supplier when there is one; the journal entry, linking to its notebook's page; the date; the yield; and the amount in its open vessels by unit, `–` when it has none. The batches are ordered by date, newest first and batches without one last, then newest first. The GET parameter `q` lists the batches in whose number, supplier's batch number or supplier, or in whose substance's key, name or German name, the text is found regardless of case; the form keeps its value. The item list, the bulk list, the delivery list, the intermediate list, the commercial chemical list, the batch list and the vessel list carry section tabs `Endprodukte`, `Zwischenprodukte`, `Handelschemikalien`, `Chargen` and `Alle Gefäße` (`End products`, `Intermediates`, `Commercial chemicals`, `Batches`, `All vessels`), linking to `/lab/inventory/end-products/`, `/lab/inventory/intermediates/`, `/lab/inventory/chemicals/`, `/lab/inventory/batches/` and `/lab/inventory/vessels/`, in the site's `nav.section-tabs` markup. A signed-in user sees a link `Neue Charge` (`New batch`).

#### Scenario: Batches of either source
- **WHEN** the database holds a made batch `KL0412` of `cinnamic-acid` dated 2026-10-30, made by a step of task `T-007` and naming the journal entry `AE-1/9`, with an open vessel of `2` g, and a batch of `acetophenone` bought from `Sigma` dated 2026-11-02 without vessels, and a test client requests the batch list
- **THEN** it lists the bought batch first, with an empty article number, `gekauft · Sigma` and `–`, and then `KL0412` with `CH-0012`, `hergestellt · T-007` linking to the task's page, `AE-1/9` linking to `/lab/journal/AE-1/` and `2 g`

#### Scenario: Searching batches
- **WHEN** the same database is listed with `q=kl04` and with `q=sigma`
- **THEN** the first lists `KL0412` alone and the second the bought batch alone

### Requirement: Batch page
`/lab/inventory/batches/<id>/` SHALL show the batch as heading; its substance, linking to its page, and the article number of the substance's article when there is one; its source; for a made batch, its journal entry linking to its notebook's page, the step that made it as its task's number and `Stufe <n>` (`Step <n>`) linking to the task's page, and its yield; for a bought batch, its supplier, the supplier's article number and the supplier's batch; its date and note; each field `–` when it has no value; its vessels, the open ones first, then by id, each as `#<id>` linking to its page, with its kind, location, amount and, at zero, the mark `aufgebraucht` (`used up`); the fillings from its vessels, newest first, each with its date, the item filled linking to its page, the count and the vessel, and the mark `storniert` (`reversed`) on a reversed one; the items holding containers of it, each linking to its page, with their count; the delivery lines naming it, current and historical, newest first, each with its date, the delivery note linking to its page, the recipient, the item and the count, the mark `nachgetragen` (`entered later`) on a line of a historical note, and the mark `storniert` on a reversed delivery and on a line of a reversed historical note; and its change history. A signed-in user sees the links `Bearbeiten` (`Edit`) and `Neues Gefäß` (`New vessel`). An unknown id answers 404.

#### Scenario: Where a batch went
- **WHEN** 5 containers of an item of `CH-0012` were filled from the flask of `KL0412`, its rest was transferred into a new vessel, a note `LS-2026-117` delivered 2 of those containers, a historical note has a line of `KL0412`, and a test client requests the batch's page
- **THEN** it lists the stored vessel and then the flask, marked `aufgebraucht`; the filling of 5 linking to the item's page; the item with 3; and the line of 2 of `LS-2026-117`, linking to its page; a line of `KL0412` on a historical note shows `nachgetragen`

### Requirement: Vessel list
`/lab/inventory/vessels/` SHALL list the open vessels, of every substance, with the columns `Gefäß`, `Name`, `Artikelnr.`, `Art`, `Charge`, `Herkunft`, `Menge`, `Ort`, `Datum`, `Angebrochen` and `Bemerkung` (`Vessel`, `Name`, `Article no.`, `Kind`, `Batch`, `Source`, `Amount`, `Location`, `Date`, `Opened`, `Note`): `#<id>`, linking to the vessel's page; its substance's name, linking to the substance's page; the article number of the substance's article, empty when there is none; its kind; its batch, linking to the batch's page; the batch's source as the batch list shows it; its amount; its location; its batch's date; for a vessel of a bought batch its `opened_on` or `versiegelt` (`sealed`), and nothing for one of a made batch; and its note. The vessels are ordered by name regardless of case, then by their batch's date, oldest first and vessels without one last, then by id. `empty=1` adds the used-up vessels. `kind=<kind>`, one of `flask`, `end-product`, `intermediate` and `commercial`, lists the vessels of that kind; another value lists every kind. The page offers each kind and shows the one in force. A signed-in user sees a link `Neue Charge` (`New batch`).

#### Scenario: Used-up vessels
- **WHEN** the database holds an open vessel and a used-up vessel, and a test client requests the vessel list with and without `empty=1`
- **THEN** it lists both with it and only the open vessel without

#### Scenario: Vessels by kind
- **WHEN** the database holds an open flask of a made batch of `cinnamic-acid`, an open vessel of a made batch of `acetophenone`, which has no article, and one of a batch of `acetophenone` bought from `Sigma`, and a test client requests the vessel list, and then with `kind=commercial`
- **THEN** the first lists the three with the kinds `Kolben`, `Zwischenprodukt` and `Handelschemikalie`, the first with `CH-0012` and the others with an empty article number, the last with `gekauft · Sigma`; the second lists the bought vessel alone

### Requirement: Vessel page
`/lab/inventory/vessels/<id>/` SHALL show the vessel as heading; its batch, linking to its page; its substance, linking to its page, and the article number of the substance's article when there is one; its kind, amount, location and note, for a vessel of a bought batch `Angebrochen am <date>` (`Opened on <date>`) or `versiegelt` (`sealed`), and the mark `aufgebraucht` (`used up`) at zero; its movements in booking order, newest first, with date, booking time, kind, amount, amount after, the user's initials, note and, for a filling, the item filled, for a withdrawal, the task and step it went into, linking to the task, for a transfer, the other vessel, linking to its page, and for a reversal the movement it reverses; and its change history. A signed-in user sees the links `Korrigieren` (`Correct`), `Bearbeiten` (`Edit`) and, on an open vessel, `Entnahme` (`Withdraw`) and `Umfüllen` (`Transfer`), and beside each withdrawal not yet reversed a button `Stornieren` (`Reverse`). An unknown id answers 404.

#### Scenario: Vessel page after a filling
- **WHEN** a test client requests the page of a vessel from which 5 containers of an item were filled
- **THEN** its newest movement is that filling, linking to the item

#### Scenario: Vessel page after a transfer
- **WHEN** a test client requests the page of a flask from which an amount was transferred into a new vessel
- **THEN** its newest movement is the `transfer_out`, linking to the new vessel's page

### Requirement: Stock by batch
The `inventory` package SHALL keep an item's containers by batch: one share for each batch of the item's substance that has held containers of the item, and one share of unknown batch (`unbekannt`, `unknown`), each a whole number of containers at least zero. The item's quantity is the sum of its shares. Each movement changes one share, the one its `batch` names, or the share of unknown batch when it names none (Item movements). An assignment is the exception: it moves containers from the share of unknown batch into the batch it names.

- An opening count goes into the batch the new-item form names, or into the share of unknown batch when the form names none.
- A filling goes into its vessel's batch.
- A delivery takes from its line's batch. When a line of a current delivery note asks for more containers than that batch's share holds, the shortfall is first assigned from the share of unknown batch, by an `assignment` movement before the delivery. The line is refused when the two shares together hold fewer.
- A correction sets the share it names.
- Reversing a delivery returns its containers to its batch's share. Reversing a filling takes its containers from its batch's share, and is refused when that share holds fewer.

Shares change by atomic conditional updates, in the transaction of their movement and together with the quantity. Two bookings prepared from the same shares therefore never take more than a share holds.

#### Scenario: Fillings into their batches
- **WHEN** a signed-in user creates an item with an opening count of 0, fills 3 containers from a vessel of the batch `KL0412`, and fills 2 from a vessel of the batch `KL0413`
- **THEN** the item has 5 containers: 3 of `KL0412`, 2 of `KL0413` and none of unknown batch

#### Scenario: Opening count of unknown batch
- **WHEN** a signed-in user creates an item with an opening count of 4 and names no batch
- **THEN** it has 4 containers of unknown batch

#### Scenario: Delivery from containers of unknown batch
- **WHEN** an item holds 1 container of the batch `KL0412` and 5 of unknown batch, and a signed-in user books a current note with a line of 3 of `KL0412`
- **THEN** the item has 3 containers, all of unknown batch, and its newest movements, newest first, are a delivery of 3 of `KL0412` with `quantity_after` 3 and an assignment of 2 to `KL0412` with `quantity_after` 6, both naming the note

#### Scenario: Too few even with unknown batch
- **WHEN** an item holds 1 container of the batch `KL0412` and 1 of unknown batch, and a signed-in user books a current note with a line of 3 of `KL0412`
- **THEN** the form shows an error at that line's count, no note exists, and both shares are unchanged

#### Scenario: A reversed delivery returns to its batch
- **WHEN** the delivery of 3 of `KL0412` from that scenario is reversed
- **THEN** the item holds 3 containers of `KL0412` and 3 of unknown batch

#### Scenario: A filling's batch emptied
- **WHEN** an item holds 3 containers of unknown batch, 2 are filled from a vessel of `KL0412`, a current note delivers 2 of `KL0412`, and a signed-in user reverses the filling
- **THEN** the reversal is refused, and the item keeps 3 containers of unknown batch

#### Scenario: Concurrent deliveries of one batch
- **WHEN** an item holds 5 containers of `KL0412` and none of unknown batch, and two deliveries of 4 of `KL0412` are validated against it and then stored one after the other
- **THEN** the first is stored, the second is refused, and the item holds 1 container of `KL0412`

#### Scenario: Correction of one share
- **WHEN** an item holds 3 containers of `KL0412` and 2 of unknown batch, and a signed-in user corrects the share of unknown batch to 0 with a note
- **THEN** the item has 3 containers, all of `KL0412`, and the correction names no batch, with `count` 0 and `quantity_after` 3

### Requirement: End product layers
The item list, the bulk list and the delivery list SHALL be the three layers of the end products, `Gebinde` (`Containers`), `Bulk` (`Bulk`) and `Lieferungen` (`Deliveries`), in this order: each has the heading `Endprodukte` (`End products`) and offers the three layers as links, to `/lab/inventory/end-products/`, `/lab/inventory/end-products/bulk/` and `/lab/inventory/deliveries/`, each with its count, the number of all items, of the vessels the bulk list lists without filters and of all delivery notes, and marks its own as current. In the section tabs, `Endprodukte` is current on all three.

#### Scenario: Three layers
- **WHEN** the database holds 2 items, one open vessel of their substance and 3 delivery notes, and a test client requests the bulk list
- **THEN** its heading is `Endprodukte`, it offers `Gebinde` with 2, `Bulk` with 1 and `Lieferungen` with 3, marks `Bulk` as current, and the section tab `Endprodukte` is current

### Requirement: Bulk list
`/lab/inventory/end-products/bulk/` SHALL list the open vessels of every substance that has an article, flasks and vessels of bought batches among them, with the columns `Artikel`, `Gefäß`, `Charge`, `Herkunft`, `Menge`, `Ort`, `Datum` and `Reicht für` (`Article`, `Vessel`, `Batch`, `Source`, `Amount`, `Location`, `Date`, `Fills`): the article number, `ohne Nr.` (`no number`) for an article without one, and the substance's name, linking to the substance's page; `#<id>`, linking to the vessel's page; the batch, linking to its page; the batch's source as the batch list shows it; the amount; the location, or `Kolben` (`Flask`) for a flask; the batch's date; and, for each item of the article, by size, the number of its containers the vessel would fill as Filling from bulk counts it, shown as `<number> × <size>` and joined by `oder` (`or`), or `Molmasse fehlt` (`Molar mass missing`) for an item the vessel does not convert into. For a signed-in user each such alternative links to that item's filling form with the vessel chosen. The vessels are ordered by article number, articles without one last and by name regardless of case, then by their batch's date, oldest first and vessels without one last, then by id.

GET parameters select the vessels listed and keep their values: `q` those in whose article number, or in whose substance's key, name or German name, or batch number or supplier's batch, the text is found regardless of case; `location` those at that location; `source`, `made` or `bought`, those of batches of that source; and `flask=1` the flasks alone. The page offers each location in use. The list shows its vessels in the views `Tabelle` and `Details`, remembered in the cookie `bulk-list-view`, with one vessel selected by `selected=<id>`, as the item list does with its items. The details view shows beside the table the selected vessel: its batch, source, amount, location, the containers it would fill, and its five newest movements as the vessel page shows them, with a link to the vessel's page. A signed-in user sees a link `Neue Charge` (`New batch`).

#### Scenario: Vessels of end products
- **WHEN** the database holds an item `CH-0012` of 100 mg and one of 1 g of `cinnamic-acid`, whose substance has the molar mass 148.16, a stored vessel of a made batch of it holding `2,5` g, its task's flask holding `4` g, a vessel of a bought batch of it holding `50` g, and a vessel of a made batch of `acetophenone`, which has no article, and a test client requests the bulk list
- **THEN** it lists the three vessels of `cinnamic-acid` and not the vessel of `acetophenone`, the flask with `Kolben`, the bought vessel with `gekauft`, and the stored vessel with `25 × 100 mg oder 2 × 1 g`

#### Scenario: A vessel that does not convert
- **WHEN** an item of 10 µmol of a substance without a molar mass has an open vessel of `600` mg
- **THEN** the bulk list shows `Molmasse fehlt` for that item in the vessel's row

#### Scenario: Filling from the bulk list
- **WHEN** a signed-in user requests the bulk list holding a vessel of `cinnamic-acid` and follows the alternative of its item of 100 mg
- **THEN** the filling form of that item opens with that vessel chosen

#### Scenario: Flasks alone
- **WHEN** the bulk list holds a flask and a stored vessel, and a test client requests it with `flask=1`
- **THEN** it lists the flask alone

### Requirement: Stock categories
Every open vessel SHALL belong to one stock category, from two facts alone, whether its substance has an article and whether its batch is made or bought: `Endprodukte` (`End products`) when its substance has an article; else `Zwischenprodukte` (`Intermediates`) when its batch is made; else `Handelschemikalien` (`Commercial chemicals`). A flask belongs to the category of its batch like any other vessel. A substance can have vessels in more than one category; giving it an article moves all its vessels to `Endprodukte`.

#### Scenario: Categories of vessels
- **WHEN** the database holds a stored vessel and the flask of made batches of `cinnamic-acid`, which has an article, the flask of a made batch of `acetophenone`, which has none, a stored vessel of another made batch of `acetophenone` and a vessel of a bought batch of `acetophenone`
- **THEN** the two vessels of `cinnamic-acid` are `Endprodukte`, the flask and the stored made vessel of `acetophenone` `Zwischenprodukte`, and the bought one `Handelschemikalien`

### Requirement: Lists by substance
`/lab/inventory/intermediates/` and `/lab/inventory/chemicals/` SHALL list the substances that have an open vessel of the category `Zwischenprodukte` and of `Handelschemikalien` respectively (Stock categories), one row per substance, under the headings `Zwischenprodukte` (`Intermediates`) and `Handelschemikalien` (`Commercial chemicals`), each followed by the number of substances and of vessels listed, and ordered by the substance's name regardless of case. A signed-in user sees a link `Neue Charge` (`New batch`) to `/lab/inventory/batches/new/` on the intermediate list and `Wareneingang` (`Goods receipt`) to `/lab/inventory/batches/new/?source=bought` on the commercial chemical list.

A row's cells describe the substance's open vessels of the list's category that the filters admit, its vessels for short. Locations are ordered as the item list orders compartments, numbers in them by value; other texts regardless of case.

- `Substanz` (`Substance`): the substance's name, linking to its page, followed on the intermediate list by its chemical classes, by label, and on the commercial chemical list by its short name and CAS number where it has them; and the mark `+gekauft` (`+bought`) on the intermediate list, `+hergestellt` (`+made`) on the commercial chemical list, when the substance has an open vessel of the other of the two categories, whatever the filters;
- `Menge` (`Amount`): the amount in its vessels summed per unit, the units in the order `mg`, `g`, `µmol`, `mmol`;
- `Gefäße` (`Vessels`): their number, followed on the intermediate list by `<n> Kolben` (`<n> in flask`) when flasks are among them, and on the commercial chemical list by `(<n> versiegelt)` (`(<n> sealed)`) when sealed vessels are among them;
- `Ort` (`Location`): from the stored vessels, the location they all share, else the first followed by `+<n>`, the number of other locations, a stored vessel without a location counting as the location `nicht hinterlegt` (`not recorded`), placed last; then, on the intermediate list, `im Kolben` (`in flask`) when flasks are among them, alone when all are flasks; a flask's own location is not shown;
- on the intermediate list, `Herkunft` (`Source`): the numbers of the tasks whose steps made the batches, linking to the tasks' pages, in the order of the tasks' numbers by value, at most two followed by `+<n>`, then `ohne Auftrag` (`no task`) when a batch was made by no step, alone when none was; and `Alter` (`Age`): the age of the newest and of the oldest batch date among its vessels, joined by ` – `, or one when the two read alike, `–` when no batch has a date, and marked as old, in a `span.age-old`, when the oldest age is a year or more;
- on the commercial chemical list, `Gruppe` (`Group`): the substance's inventory group; `Lieferanten` (`Suppliers`): the suppliers of the batches, `unbekannt` (`unknown`) for a batch without one, the first followed by `+<n>`, the number of the others; and `Angebrochen` (`Opened`): the earliest `opened_on` among its vessels, or `versiegelt` (`sealed`) when all are sealed.

An age runs from a batch's date to today in whole calendar months, a month being complete on the same day of the month, or on a shorter month's last day: `heute` (`today`) for today, `1 Tag` (`1 day`) and `<n> Tage` (`<n> days`) below one month, `<n> Mon.` (`<n> mo.`) below twelve months, and `<y> J` (`<y> y`) or `<y> J <m> Mon.` (`<y> y <m> mo.`) from twelve months.

GET parameters filter the list and keep their values; a filter on vessels admits vessels, and a row is listed while it has at least one vessel the filters admit:

- on both lists, `q`: vessels in whose substance's key, name, German name, short name or CAS number, or in whose batch's number, supplier's batch or supplier, the text is found regardless of case, and on the intermediate list also in the number of the task that made the batch; and `location`: stored vessels at that location, flasks never;
- on the intermediate list, `class`: substances filed under the chemical class of that key or under a class filed below it, at any depth; `flask=1`: flasks; and `old=1`: vessels whose batch's age is a year or more;
- on the commercial chemical list, `group`: substances filed under the inventory group of that key or under a group filed below it, at any depth; `supplier`: vessels of batches bought from that supplier; and `sealed=1`: sealed vessels.

A `class` or `group` key that names no term lists none. The page offers each location of the category's open stored vessels and each supplier of its bought batches, and each term of the chemical classes or inventory groups in the order of the vocabulary's page; the value in force is offered even when no vessel has it any more. The list shows its substances in the views `Tabelle` and `Details`, remembered in the cookies `intermediate-list-view` and `chemical-list-view`, with one substance selected by `selected=<key>`, as the item list does with its items.

The details view shows, with the table, the selected substance and its vessels, the same vessels its row describes: its name, linking to its page, and for a signed-in user `Neue Charge` to `/lab/inventory/batches/new/?substance=<key>` on the intermediate list and `Wareneingang` to `/lab/inventory/batches/new/?substance=<key>&source=bought` on the commercial chemical list; and a table of its vessels, ordered by their batch's date, oldest first and vessels without one last, then by id, with the columns `Gefäß`, `Charge`, `Menge`, `Ort`, `Herkunft`, `Datum` and `Bemerkung` (`Vessel`, `Batch`, `Amount`, `Location`, `Source`, `Date`, `Note`), and on the commercial chemical list `Angebrochen am` (`Opened on`) before `Bemerkung`: `#<id>`, linking to the vessel's page; the batch, linking to its page; the amount; the location, `nicht hinterlegt` without one, or `Kolben` (`Flask`) for a flask; for a made batch the task's number linking to its page and the step's label, or `ohne Auftrag` when no step made it, followed by the journal entry linking to its notebook's page where the batch names one, and for a bought batch the supplier and the supplier's article number; the batch's date; the `opened_on` or `versiegelt`; and the vessel's note. For a signed-in user each vessel offers `Entnahme` (`Withdraw`), on an open vessel, `Umfüllen` (`Transfer`), `Korrigieren` (`Correct`) and `Bearbeiten` (`Edit`), which open the vessel's withdrawal, transfer, correction and edit forms in a dialog over the page (web-app "Form dialogs"). When the substance has a single vessel there, the details also show that vessel's five newest movements in booking order, newest first, as its page orders them, with date, kind, amount, amount after, the user's initials and note, and a link to the vessel's page. The list selects only among the substances it lists, so after a save that leaves the selected substance no vessel the filters admit, the first substance listed is selected, and none when the list is empty. Details requested directly for a substance that has open vessels of the category, none of which the filters admit, show `Keine Gefäße` (`No vessels`) in place of the table.

#### Scenario: Intermediates by substance
- **WHEN** `acetophenone`, which has no article, has a flask of a batch made by a step of task `T-021` holding `1` g, a stored vessel of the same batch holding `1,5` g in `Chemikalienschrank 3` and one of a batch made by a step of `T-008` holding `12` g there, and a bought vessel, and a test client requests the intermediate list
- **THEN** it shows one row of `acetophenone` with `14,5 g`, `3` and `1 Kolben`, `Chemikalienschrank 3` and `im Kolben`, `T-008` and `T-021`, and the mark `+gekauft`

#### Scenario: Commercial chemicals by substance
- **WHEN** `benzaldehyde`, which has no article, has a bottle bought from `Sigma-Aldrich` holding `41` g in `Kühlschrank 1`, opened on 2026-03-05, and one bought from `TCI` holding `100` g in `Kühlschrank 2`, sealed, and a test client requests the commercial chemical list
- **THEN** it shows one row of `benzaldehyde` with `141 g`, `2 (1 versiegelt)`, `Kühlschrank 1 +1`, `Sigma-Aldrich +1` and `05.03.2026`

#### Scenario: Filters narrow the sums
- **WHEN** the same database is listed with `supplier=TCI`, and then with `sealed=1`
- **THEN** both show the row of `benzaldehyde` with `100 g`, one vessel, `Kühlschrank 2`, `TCI` and `versiegelt`, and its details list that bottle alone

#### Scenario: Locations not recorded
- **WHEN** a substance has two bought bottles, one in `Regal 10` and one without a location, and another substance a flask alone on the intermediate list
- **THEN** the first row shows `Regal 10 +1`, its details `nicht hinterlegt` for the second bottle, and the second row `im Kolben`

#### Scenario: Containers of the selected substance
- **WHEN** a signed-in user with the cookie `intermediate-list-view` set to `details` requests the intermediate list with `selected=acetophenone`
- **THEN** the details show the three vessels of `acetophenone`, the flask with `Kolben` and `T-021`, each with `Entnahme`, `Umfüllen`, `Korrigieren` and `Bearbeiten` opening in a dialog, and a link `Neue Charge` to `/lab/inventory/batches/new/?substance=acetophenone`

#### Scenario: Booking in a dialog
- **WHEN** a signed-in user opens `Entnahme` of a vessel holding `12` g in the details and books `2` g into a step of a running task
- **THEN** the dialog closes, the row shows the substance's amount `2` g lower and the details show the vessel with `10 g`, the list's selection and view unchanged

#### Scenario: The last admitted bottle opened
- **WHEN** with `sealed=1` the commercial chemical list shows `benzaldehyde` and `toluene`, `benzaldehyde` selected with one sealed bottle, and a signed-in user books a withdrawal from that bottle in its dialog; and then, with `toluene` alone left and selected, books one from its only sealed bottle
- **THEN** after the first save the list shows `toluene` alone, selected, and the address names it; after the second the list shows no substance and the details none

#### Scenario: One bottle with its movements
- **WHEN** a substance has a single bought vessel, from which two withdrawals were booked, and a test client requests the commercial chemical list with `selected` naming it and the cookie `chemical-list-view` set to `details`
- **THEN** the details show that vessel and its opening and two withdrawals, the newest first, with their amounts after

#### Scenario: Ages
- **WHEN** on 2026-11-24 one substance has intermediates of batches dated 2026-11-20 and 2026-04-06, another has one of a batch dated 2025-05-01, and a third one of a batch dated 2025-11-24
- **THEN** the first row's age shows `4 Tage – 7 Mon.` with no `span.age-old`, the second row's `1 J 6 Mon.` and the third row's `1 J`, both in a `span.age-old`, and `old=1` lists the second and third substances alone

#### Scenario: Month ends
- **WHEN** on 2026-02-28 a batch is dated 2026-01-31, and on 2026-02-27 another is dated 2026-01-31
- **THEN** the first shows `1 Mon.` and the second `27 Tage`

#### Scenario: Classes below a class
- **WHEN** `acetophenone` has the chemical class `aryl-ketones`, filed under `ketones`, and a test client requests the intermediate list with `class=ketones`, and with `class=nothing`
- **THEN** the first lists `acetophenone` and the second lists no substance

### Requirement: Live inventory lists
All six inventory lists—`/lab/inventory/end-products/`, `/lab/inventory/intermediates/`, `/lab/inventory/chemicals/`, `/lab/inventory/end-products/bulk/`, `/lab/inventory/deliveries/`, `/lab/inventory/batches/`, and `/lab/inventory/vessels/`—SHALL implement live list updates (web-app "Live lists"):

- Each list's filter form updates its table body in place with `morph:outerHTML` and updates its count (and, on split-view lists, `#item-detail` and `#filter-selected`) out of band with disjoint `:morph` selectors, using triggers scoped exclusively to its own controls (`submit`, a single `change` clause — `change target:select` when only selects are inside `#filters`, or `change target:(select, input[type=checkbox])` when both selects and checkboxes are inside `#filters` — and `search from:#filter-q` / `input delay:200ms from:#filter-q` where present) and synchronizing with split-view row requests on `#main:replace`.
- On `/lab/inventory/end-products/`, `#filters` also triggers on `change from:#filter-container`, `change from:#filter-compartment`, and `change from:#filter-box`; the sortable column header links (`#item-head`), stock-status menu links (`#stock-entries`), and `Reset` link in `#list-summary` ALSO update `#item-rows` and dependent regions in place via HTMX with `hx-sync="#main:replace"`, using disjoint OOB targets that morph `#filters:morph` and `#more-filters:morph` (without separately targeting their children `#filter-selected` or `#filter-hidden`) so visible filter controls stay synchronized with the applied response and URL, while keeping their `href` / `method="get"` fallbacks.
- Each list's non-restore HTMX GET response sets `HX-Push-Url` to its canonical path and cleaned query:
  - `/lab/inventory/end-products/`: nonempty `q`, `category`, `stock`, `container`, `compartment`, `box`, effective `sort` (default `category`), `dir=desc` only when descending, and resolved `selected` (omitted when empty);
  - `/lab/inventory/intermediates/`: nonempty `q`, `location`, `class`, `flask=1`, `old=1`, and resolved `selected` substance key (omitted when empty);
  - `/lab/inventory/chemicals/`: nonempty `q`, `location`, `group`, `supplier`, `sealed=1`, and resolved `selected` substance key (omitted when empty);
  - `/lab/inventory/end-products/bulk/`: trimmed `q`, trimmed `location`, valid `source`, `flask=1`, and resolved `selected` vessel ID (omitted when empty);
  - `/lab/inventory/deliveries/`: trimmed `q`, numeric `item`, and resolved `selected` note ID (omitted when empty);
  - `/lab/inventory/batches/`: trimmed `q`;
  - `/lab/inventory/vessels/`: valid `kind` and `empty=1`.
- The split-view detail endpoints (`/lab/inventory/items/<id>/detail/`, `/lab/inventory/intermediates/<key>/`, `/lab/inventory/chemicals/<key>/`, `/lab/inventory/end-products/bulk/<id>/`, and `/lab/inventory/deliveries/<id>/detail/`) set `HX-Replace-Url` to their list URL with the active filters and `selected` naming the requested record.

#### Scenario: Live filtering on category lists
- **WHEN** a test client requests `/lab/inventory/intermediates/?location=Regal+1&sealed=1&selected=missing`, `/lab/inventory/intermediates/?location=nowhere`, and `/lab/inventory/chemicals/?sealed=1&flask=1` with `HX-Request: true`
- **THEN** each page's filter form carries `hx-get`, `hx-push-url="true"`, `hx-sync="#main:replace"`, scoped triggers, `hx-target="#item-rows"`, `hx-select="#item-rows"`, `hx-swap="morph:outerHTML"`, and `hx-select-oob` naming `#category-count:morph`, `#item-detail:morph`, and `#filter-selected:morph`; the first sets `HX-Push-Url` to `/lab/inventory/intermediates/?location=Regal+1&selected=<resolved>` dropping `sealed`; the second sets `/lab/inventory/intermediates/?location=nowhere` with no `selected`; and the third sets `/lab/inventory/chemicals/?sealed=1&selected=<resolved>` dropping `flask`

#### Scenario: Live filtering, sorting, stock status, and reset on the item list
- **WHEN** a test client requests `/lab/inventory/end-products/?category=Ester&stock=bogus&sort=stock&dir=desc&q=` with `HX-Request: true`
- **THEN** `#filters`, `#item-head` sort links, `#stock-entries` links, and the `#list-summary` reset link carry HTMX live attributes targeting `#item-rows` with `morph:outerHTML` and `hx-sync="#main:replace"`, `#filters` triggers on `#filter-container`, `#filter-compartment`, and `#filter-box`, the sort, stock, and Reset links' `hx-select-oob` morph `#filters:morph` and `#more-filters:morph` without overlapping `#filter-selected` or `#filter-hidden`, and `HX-Push-Url` equals `/lab/inventory/end-products/?category=Ester&sort=stock&dir=desc&selected=<resolved>`

#### Scenario: Live filtering on bulk, delivery, batch, and vessel lists
- **WHEN** a test client requests `/lab/inventory/end-products/bulk/?flask=1&source=bogus&q=+CH+`, `/lab/inventory/deliveries/?q=+LS+&item=abc`, `/lab/inventory/batches/?q=+B-1+`, and `/lab/inventory/vessels/?kind=bogus&empty=1` with `HX-Request: true`
- **THEN** each list's filter form carries scoped HTMX live attributes targeting its table body with `morph:outerHTML`, `hx-sync="#main:replace"`, and `:morph` OOB targets for its count (plus `#item-detail:morph,#filter-selected:morph` on bulk and deliveries), and their `HX-Push-Url` headers drop invalid values, trim `q`, and resolve `selected` on split lists

#### Scenario: Inventory detail endpoints replace the list URL
- **WHEN** a test client requests `/lab/inventory/items/<id>/detail/` with `HX-Request: true` and `HX-Current-URL: http://testserver/lab/inventory/end-products/?category=Ester&selected=999`, `/lab/inventory/intermediates/<key>/?location=Regal+1` with `HX-Request: true`, and `/lab/inventory/items/<id>/detail/` with a foreign-host `HX-Current-URL`
- **THEN** the first sets `HX-Replace-Url` to `/lab/inventory/end-products/?category=Ester&selected=<id>`, the second to `/lab/inventory/intermediates/?location=Regal+1&selected=<key>`, and the third to `/lab/inventory/end-products/?selected=<id>`, and all three return only `#item-detail`

