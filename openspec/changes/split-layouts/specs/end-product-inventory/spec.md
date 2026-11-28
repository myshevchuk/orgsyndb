## MODIFIED Requirements

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

The details view shows, with the table, the selected substance and its vessels, the same vessels its row describes: its name, linking to its page, and for a signed-in user `Neue Charge` to `/lab/inventory/batches/new/?substance=<key>` on the intermediate list and `Wareneingang` to `/lab/inventory/batches/new/?substance=<key>&source=bought` on the commercial chemical list; and its lot table, a table of its vessels, ordered by their batch's date, oldest first and vessels without one last, then by id, with the columns `Gefäß`, `Charge`, `Menge`, `Ort`, `Herkunft` and `Datum` (`Vessel`, `Batch`, `Amount`, `Location`, `Source`, `Date`), and on the commercial chemical list `Angebrochen am` (`Opened on`) after `Datum`: `#<id>`, linking to the vessel's page; the batch, linking to its page; the amount; the location, `nicht hinterlegt` without one, or `Kolben` (`Flask`) for a flask; for a made batch the task's number linking to its page and the step's label, or `ohne Auftrag` when no step made it, followed by the journal entry linking to its notebook's page where the batch names one, and for a bought batch the supplier and the supplier's article number; the batch's date; and the `opened_on` or `versiegelt`. Each row of the lot table carries `data-item` with the vessel's id.

One vessel of the lot table is selected, its lot: the one `lot=<id>` names among the vessels the table lists, else the first. Its row carries `aria-current="true"`, and a click without a modifier key in a row, not on its links, or the arrow keys up and down within the lot table, select another lot without changing the selected substance. With the lot table the details show the lot's details as the vessel list's details show a vessel (Vessel details): its note, its five newest movements and, for a signed-in user, `Entnahme` (`Withdraw`) on an open vessel, `Umfüllen` (`Transfer`), `Korrigieren` (`Correct`) and `Bearbeiten` (`Edit`), which open the vessel's forms in a dialog over the page (web-app "Form dialogs"). The lot's details come from `/lab/inventory/intermediates/<key>/lots/<id>/` and `/lab/inventory/chemicals/<key>/lots/<id>/`, which answer an htmx request with the lot's details alone and set `HX-Replace-Url` to the list's URL with the active filters, `selected` naming the substance and `lot` naming the vessel, and redirect any other request there; a key or an id that names no vessel of the substance in the list's category answers 404. The list's address names `lot` only when the lot is not the first of the lot table.

The list selects only among the substances it lists, so after a save that leaves the selected substance no vessel the filters admit, the first substance listed is selected, and none when the list is empty. Details requested directly for a substance that has open vessels of the category, none of which the filters admit, show `Keine Gefäße` (`No vessels`) in place of the table.

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
- **THEN** the lot table shows the three vessels of `acetophenone`, the flask with `Kolben` and `T-021`; the first is the selected lot, whose details offer `Entnahme`, `Umfüllen`, `Korrigieren` and `Bearbeiten` opening in a dialog; and the details link `Neue Charge` to `/lab/inventory/batches/new/?substance=acetophenone`

#### Scenario: Booking in a dialog
- **WHEN** a signed-in user selects a vessel holding `12` g as the lot, opens its `Entnahme` and books `2` g into a step of a running task
- **THEN** the dialog closes, the row shows the substance's amount `2` g lower, the lot table and the lot's details show the vessel with `10 g`, and the list's selection, lot and view are unchanged

#### Scenario: The last admitted bottle opened
- **WHEN** with `sealed=1` the commercial chemical list shows `benzaldehyde` and `toluene`, `benzaldehyde` selected with one sealed bottle, and a signed-in user books a withdrawal from that bottle in its dialog; and then, with `toluene` alone left and selected, books one from its only sealed bottle
- **THEN** after the first save the list shows `toluene` alone, selected, and the address names it; after the second the list shows no substance and the details none

#### Scenario: One bottle with its movements
- **WHEN** a substance has a single bought vessel, from which two withdrawals were booked, and a test client requests the commercial chemical list with `selected` naming it and the cookie `chemical-list-view` set to `details`
- **THEN** the lot table lists that vessel alone, selected, and the lot's details show its opening and two withdrawals, the newest first

#### Scenario: Ages
- **WHEN** on 2026-11-24 one substance has intermediates of batches dated 2026-11-20 and 2026-04-06, another has one of a batch dated 2025-05-01, and a third one of a batch dated 2025-11-24
- **THEN** the first row's age shows `4 Tage – 7 Mon.` with no `span.age-old`, the second row's `1 J 6 Mon.` and the third row's `1 J`, both in a `span.age-old`, and `old=1` lists the second and third substances alone

#### Scenario: Month ends
- **WHEN** on 2026-02-28 a batch is dated 2026-01-31, and on 2026-02-27 another is dated 2026-01-31
- **THEN** the first shows `1 Mon.` and the second `27 Tage`

#### Scenario: Classes below a class
- **WHEN** `acetophenone` has the chemical class `aryl-ketones`, filed under `ketones`, and a test client requests the intermediate list with `class=ketones`, and with `class=nothing`
- **THEN** the first lists `acetophenone` and the second lists no substance

#### Scenario: Selecting a lot
- **WHEN** `acetophenone` has three intermediate vessels, and a test client requests the intermediate list with `selected=acetophenone` and `lot` naming the second, then with `lot` naming a vessel of another substance, and then requests the second vessel's lot details with `HX-Request: true` and a same-host `HX-Current-URL` of `/lab/inventory/intermediates/?location=Regal+1&selected=acetophenone`, and once without htmx
- **THEN** the first page marks the second vessel's row and shows its details; the second marks the first vessel's row; the htmx answer holds the lot's details alone and sets `HX-Replace-Url` to `/lab/inventory/intermediates/?location=Regal+1&selected=acetophenone&lot=<id>`; and the other answer redirects to the list with `selected=acetophenone` and `lot=<id>`

#### Scenario: A lot of another substance
- **WHEN** a test client requests `/lab/inventory/intermediates/acetophenone/lots/<id>/` with `<id>` naming a vessel of another substance, and `/lab/inventory/chemicals/acetophenone/lots/<id>/` with `<id>` naming an intermediate vessel of `acetophenone`
- **THEN** both answer 404

### Requirement: Live inventory lists
All seven inventory lists—`/lab/inventory/end-products/`, `/lab/inventory/intermediates/`, `/lab/inventory/chemicals/`, `/lab/inventory/end-products/bulk/`, `/lab/inventory/deliveries/`, `/lab/inventory/batches/`, and `/lab/inventory/vessels/`—SHALL implement live list updates (web-app "Live lists") as main lists (web-app "Main lists"):

- Each list's filter form updates `#item-rows` in place with `morph:outerHTML` and updates its count, `#item-head`, `#item-detail` and `#filter-selected` out of band with disjoint `:morph` selectors. It uses triggers scoped exclusively to its own controls: `submit`; a single `change` clause, `change target:select` when only selects are inside `#filters`, or `change target:(select, input[type=checkbox])` when both selects and checkboxes are inside `#filters`; and `search from:#filter-q` / `input delay:200ms from:#filter-q` where present. It synchronizes with split-view row requests on `#main:replace`.
- Each list's column header links update `#item-rows` in place via HTMX with `hx-sync="#main:replace"`, and its count, `#item-head`, `#item-detail` and `#filters` out of band, keeping their `href` fallbacks.
- On `/lab/inventory/end-products/`, `#filters` also triggers on `change from:#filter-container`, `change from:#filter-compartment`, and `change from:#filter-box`. The header links (`#item-head`), the stock-status menu links (`#stock-entries`) and the `Reset` link in `#list-summary` use disjoint OOB targets that morph `#filters:morph` and `#more-filters:morph`, without separately targeting their children `#filter-selected` or `#filter-hidden`, so visible filter controls stay synchronized with the applied response and URL. They keep their `href` / `method="get"` fallbacks.
- Each list's non-restore HTMX GET response sets `HX-Push-Url` to its canonical path and cleaned query. On every list the query names `sort` and `dir=desc` as web-app "Main lists" states, and the resolved `selected` (omitted when empty):
  - `/lab/inventory/end-products/`: nonempty `q`, `category`, `stock`, `container`, `compartment`, `box`, and `selected` naming an item ID;
  - `/lab/inventory/intermediates/`: nonempty `q`, `location`, `class`, `flask=1`, `old=1`, `selected` naming a substance key, and `lot` naming a vessel as end-product-inventory "Lists by substance" states;
  - `/lab/inventory/chemicals/`: nonempty `q`, `location`, `group`, `supplier`, `sealed=1`, `selected` naming a substance key, and `lot` naming a vessel as "Lists by substance" states;
  - `/lab/inventory/end-products/bulk/`: trimmed `q`, trimmed `location`, valid `source`, `flask=1`, and `selected` naming a vessel ID;
  - `/lab/inventory/deliveries/`: trimmed `q`, numeric `item`, and `selected` naming a note ID;
  - `/lab/inventory/batches/`: trimmed `q`, and `selected` naming a batch ID;
  - `/lab/inventory/vessels/`: valid `kind`, `empty=1`, and `selected` naming a vessel ID.
- The details endpoints set `HX-Replace-Url` to their list URL with the active filters and `selected` naming the requested record. They are `/lab/inventory/items/<id>/detail/`, `/lab/inventory/intermediates/<key>/`, `/lab/inventory/chemicals/<key>/`, `/lab/inventory/end-products/bulk/<id>/`, `/lab/inventory/deliveries/<id>/detail/`, `/lab/inventory/batches/<id>/detail/`, and `/lab/inventory/vessels/<id>/detail/`.

#### Scenario: Live filtering on category lists
- **WHEN** a test client requests `/lab/inventory/intermediates/?location=Regal+1&sealed=1&selected=missing`, `/lab/inventory/intermediates/?location=nowhere`, and `/lab/inventory/chemicals/?sealed=1&flask=1` with `HX-Request: true`
- **THEN** each page's filter form carries `hx-get`, `hx-push-url="true"`, `hx-sync="#main:replace"`, scoped triggers, `hx-target="#item-rows"`, `hx-select="#item-rows"`, `hx-swap="morph:outerHTML"`, and `hx-select-oob` naming `#category-count:morph`, `#item-head:morph`, `#item-detail:morph`, and `#filter-selected:morph`
- **AND** the first sets `HX-Push-Url` to `/lab/inventory/intermediates/?location=Regal+1&selected=<resolved>`, dropping `sealed`; the second to `/lab/inventory/intermediates/?location=nowhere` with no `selected`; and the third to `/lab/inventory/chemicals/?sealed=1&selected=<resolved>`, dropping `flask`

#### Scenario: Live filtering, sorting, stock status, and reset on the item list
- **WHEN** a test client requests `/lab/inventory/end-products/?category=Ester&stock=bogus&sort=stock&dir=desc&q=` with `HX-Request: true`
- **THEN** `#filters`, the `#item-head` sort links, the `#stock-entries` links, and the `#list-summary` reset link carry HTMX live attributes targeting `#item-rows` with `morph:outerHTML` and `hx-sync="#main:replace"`, and `#filters` triggers on `#filter-container`, `#filter-compartment`, and `#filter-box`
- **AND** the sort, stock, and Reset links' `hx-select-oob` morph `#filters:morph` and `#more-filters:morph` without overlapping `#filter-selected` or `#filter-hidden`, and `HX-Push-Url` equals `/lab/inventory/end-products/?category=Ester&sort=stock&dir=desc&selected=<resolved>`

#### Scenario: Live filtering on bulk, delivery, batch, and vessel lists
- **WHEN** a test client requests `/lab/inventory/end-products/bulk/?flask=1&source=bogus&q=+CH+`, `/lab/inventory/deliveries/?q=+LS+&item=abc`, `/lab/inventory/batches/?q=+B-1+&sort=bogus`, and `/lab/inventory/vessels/?kind=bogus&empty=1&sort=amount` with `HX-Request: true`
- **THEN** each list's filter form carries scoped HTMX live attributes targeting `#item-rows` with `morph:outerHTML`, `hx-sync="#main:replace"`, and `:morph` OOB targets for its count, `#item-head`, `#item-detail` and `#filter-selected`
- **AND** their `HX-Push-Url` headers drop invalid values, trim `q`, resolve `selected`, drop the batch list's unknown `sort`, and keep the vessel list's `sort=amount`

#### Scenario: Inventory details endpoints replace the list URL
- **WHEN** a test client requests these with `HX-Request: true`:
  - `/lab/inventory/items/<id>/detail/` with `HX-Current-URL: http://testserver/lab/inventory/end-products/?category=Ester&selected=999`;
  - `/lab/inventory/intermediates/<key>/?location=Regal+1`;
  - `/lab/inventory/items/<id>/detail/` with a foreign-host `HX-Current-URL`;
  - `/lab/inventory/batches/<id>/detail/` with `HX-Current-URL: http://testserver/lab/inventory/batches/?q=KL&sort=yield`
- **THEN** the first sets `HX-Replace-Url` to `/lab/inventory/end-products/?category=Ester&selected=<id>`, the second to `/lab/inventory/intermediates/?location=Regal+1&selected=<key>`, the third to `/lab/inventory/end-products/?selected=<id>`, and the fourth to `/lab/inventory/batches/?q=KL&sort=yield&selected=<id>`
- **AND** all four return only `#item-detail`
