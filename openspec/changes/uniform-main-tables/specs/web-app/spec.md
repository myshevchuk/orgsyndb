## MODIFIED Requirements

### Requirement: Main lists
The lists of this table SHALL be the lab's main lists:

| List | Path | Columns by key | Default order | Details of a record | View cookie |
|---|---|---|---|---|---|
| item list | `/lab/inventory/end-products/` | `number`, `name`, `category`, `container`, `stock`, `mean_year`, `this_year`, `coverage`, `compartment`, `box`, `bulk` | `category` ascending | `/lab/inventory/items/<id>/detail/` | `item-list-view` |
| bulk list | `/lab/inventory/end-products/bulk/` | `article`, `vessel`, `batch`, `source`, `amount`, `location`, `date`, (`fills`) | `article` ascending | `/lab/inventory/end-products/bulk/<id>/` | `bulk-list-view` |
| delivery list | `/lab/inventory/deliveries/` | `number`, `date`, `recipient`, `lines`, (`contents`) | `date` descending | `/lab/inventory/deliveries/<id>/detail/` | `delivery-list-view` |
| intermediate list | `/lab/inventory/intermediates/` | `substance`, `amount`, `vessels`, `location`, `source`, `age` | `substance` ascending | `/lab/inventory/intermediates/<key>/` | `intermediate-list-view` |
| commercial chemical list | `/lab/inventory/chemicals/` | `substance`, `group`, `amount`, `vessels`, `location`, `suppliers`, `opened` | `substance` ascending | `/lab/inventory/chemicals/<key>/` | `chemical-list-view` |
| batch list | `/lab/inventory/batches/` | `batch`, `name`, `article`, `source`, `notebook`, `date`, `yield`, `stock` | `date` descending | `/lab/inventory/batches/<id>/detail/` | `batch-list-view` |
| vessel list | `/lab/inventory/vessels/` | `vessel`, `name`, `article`, `kind`, `batch`, `source`, `amount`, `location`, `date`, `opened` | `name` ascending | `/lab/inventory/vessels/<id>/detail/` | `vessel-list-view` |
| planning list | `/lab/planning/` | `article`, `runway`, `synthesis`, `start`, `priority`, `tasks`, (`actions`) | `start` ascending | `/lab/planning/<article number>/detail/` | `planning-list-view` |
| task list | `/lab/tasks/` | `number`, `product`, `priority`, `assignee`, `started`, `ended`, `progress`, `batch`, `report`, `qc`, `state` | `priority` ascending | `/lab/tasks/<number>/detail/` | `task-list-view` |
| substance list | `/lab/registry/` | `name`, `key`, `short_name`, `group`, `classes`, `formula`, `molar_mass`, `article` | `name` ascending | `/lab/registry/substances/<key>/detail/` | `substance-list-view` |

The keys name a list's columns in the order its spec states them. A key in parentheses names a column that does not sort.

**The main table.** Each main list shows its records in one table, its main table, a `table.main-table`. Its header row is in `#item-head` and its body is `#item-rows`. Each row of the body holds one record and carries `data-item` with the record's key: the id of an item, vessel, delivery note or batch, the key of a substance, the number of a task, or the article number of an article. The table sits in a split layout beside the details pane `#item-detail`, which carries `data-item` with the key of the record whose details it holds. The list marks its count, `#item-rows` and `#item-detail` as refreshed parts (Form dialogs).

**Sorting.** `sort=<key>`, naming a column that sorts, puts the list in that column's order, ascending, and with `dir=desc` descending. Without `sort`, or with a key naming no column that sorts, the list is in its default order. That order is the one its spec states, and it runs in the default column's order in the stated direction. The header of each column that sorts holds a link to the list in that column's order: descending when that column is in force ascending, and ascending otherwise. The link keeps the filters in force and the `selected` record. The header of the column in force carries `aria-sort`, `ascending` or `descending`, and no other header does. The filter form keeps the order in force in hidden fields `sort` and `dir`, present only while the order is not the default, so filtering keeps it.

With the script, the filter form and the header links update the list in place (Live lists). The filter form updates `#item-rows`, and out of band the list's count, `#item-head`, `#item-detail` and `#filter-selected`. The header links update `#item-rows`, and out of band the list's count, `#item-head`, `#item-detail` and `#filters`, which holds `#filter-selected` and the order. Without the script, the links load the page.

A column orders its rows by the value its cells show:

- numbers by value;
- amounts and container sizes by their value in the smallest unit of their kind, mg for masses and µmol for amounts of substance, masses before amounts of substance;
- a cell of amounts in several units, summed per unit, by its masses summed in mg; cells without a mass come after those with one, by their amounts of substance summed in µmol;
- dates and times by their order;
- a priority by its rank, high, medium, low;
- a task's state by the task list's order of states;
- a progress by the share of steps done, a task without steps having none;
- an age by the oldest age it shows;
- any other cell of several values by its first;
- any other text, links and badges among it, by its text regardless of case, with a run of digits within it ordered by its value, so that `#2` comes before `#10`, `AE-1/2` before `AE-1/10`, and `Fach 2` before `Fach 10`.

These columns have orders of their own:

- the item list's `stock` orders by level, most urgent first, in the order end-product-inventory "Stock levels" lists the levels, then by coverage, items without one after the others at their level;
- its `bulk` orders by the number of containers its bulk would fill;
- its `container` orders by size as end-product-inventory "Items" orders sizes;
- the bulk list's `article` orders by article number, articles without one last, then by name regardless of case;
- the planning list's `article` orders by the article's name.

Ascending, numbers and amounts come first, then dates, then text; descending reverses that whole order. Empty cells and cells reading `–` come last in either direction. Rows of equal value keep the list's default order; on the item list, they keep the order by article number, then by container, that its order summary states.

**The address.** A main list's canonical address, which its live responses push (Live lists), names `sort`, and `dir=desc` when descending, unless the order in force is its default order. It names the resolved `selected` unless the list is empty.

**Selection.** One record listed is selected, as the item list selects its items (end-product-inventory "Item list"). It is the one `selected=<key>` names among those listed; without it, or naming none of them, it is the first record listed; and there is none when the list is empty. The selected row carries `aria-current="true"`. A click without a modifier key in a row selects its record, unless it lands on a link, button, label or form control. So do the arrow keys up and down. Selecting loads the record's details from the list's details endpoint into `#item-detail` in place. Once they have arrived, the record's row is marked and the address names it in `selected`. Sorting and filtering keep the selected record while the list still holds it.

A details endpoint answers an HTMX request with the `#item-detail` fragment alone and redirects any other request to the list with `selected` naming the record (Live lists). An unknown key answers 404. With no record selected, `#item-detail` holds a short note that none is chosen.

**Views.** Each main list shows its records in the views `Tabelle` and `Details` (`Table`, `Details`). The browser remembers the view last chosen in the list's cookie, `table` or `details`. The table view shows the table alone. The details view shows the table beside the details of the selected record. The list opens in its cookie's view. Without the cookie, or with another value, it opens in the table view, except the planning list, which opens in the details view. The address does not name the view. On paper a main list prints every row of its table, without the details.

**Table styles.** Every table of the pages under `/lab/` but the admin's SHALL be a main table or an auxiliary table. The main tables of the main lists carry the class `main-table`. Every other table carries `aux-table`: in widgets, in details panes, on record pages, on lists that are not main lists, in forms, and key–value tables. No table carries both classes or neither. The main tables share one look and the auxiliary tables another.

#### Scenario: Sorting by a column
- **WHEN** the database holds batches dated 2026-01-02 and 2026-03-04 and one without a date, and a test client requests the batch list without `sort`, with `sort=date`, and with `sort=date&dir=desc`
- **THEN** the first and third answers list the batch of 2026-03-04, then that of 2026-01-02, then the undated batch, and the `Datum` header carries `aria-sort="descending"` and links to the list with `sort=date` and no `dir`
- **AND** the second answer lists 2026-01-02, then 2026-03-04, then the undated batch, its `Datum` header carries `aria-sort="ascending"` and links to the list with `sort=date&dir=desc`, and no other header carries `aria-sort`

#### Scenario: An unknown sort key
- **WHEN** a test client requests the substance list with `sort=nothing`, and the planning list with `sort=actions`
- **THEN** both lists are in their default order, the substance list's `Name` header and the planning list's `Spätester Start` header carry `aria-sort="ascending"`, and the planning list's `Maßnahmen` header holds no link

#### Scenario: Header links keep filters and selection
- **WHEN** the demo data set is written and a test client requests `/lab/tasks/?state=all&person=KL&selected=<a task of KL>`
- **THEN** every header link of the task list names `state=all`, `person=KL` and `selected` naming that task, and the filter form holds the order in force

#### Scenario: Amounts across units and text after values
- **WHEN** the database holds open vessels of `1` g, `500` mg and `20` µmol, a vessel of a bought batch opened on 2026-05-01, one sealed, and one of a made batch, and a test client requests the vessel list with `sort=amount`, and then with `sort=opened`
- **THEN** the first lists `500 mg`, `1 g` and then `20 µmol`; the second lists the opened vessel, then the sealed vessel, then the vessel of the made batch, which shows nothing

#### Scenario: The canonical address omits the default order
- **WHEN** a test client requests, with `HX-Request: true`, the batch list with `sort=date&dir=desc`, then with `sort=yield`, and the item list with `sort=category`
- **THEN** the first pushes `/lab/inventory/batches/?selected=<first batch>`, the second `/lab/inventory/batches/?sort=yield&selected=<first batch>`, and the third the item list's address with neither `sort` nor `dir`

#### Scenario: Selecting a record of a new split list
- **WHEN** the demo data set is written and a test client requests the task list, the substance list, the batch list and the vessel list, each with `selected` naming its second record
- **THEN** each list's `#item-rows` rows carry `data-item`, `hx-get` naming the list's details endpoint and `hx-trigger="item-select"`, the second row carries `aria-current="true"` and no other row does, and `#item-detail` holds that record's details

#### Scenario: Details requested without htmx
- **WHEN** a test client requests `/lab/tasks/<number>/detail/`, `/lab/registry/substances/<key>/detail/`, `/lab/inventory/batches/<id>/detail/`, `/lab/inventory/vessels/<id>/detail/` and `/lab/planning/<article number>/detail/` without HTMX headers, and each with an unknown key
- **THEN** the first five redirect to their lists with `selected` naming the record, and the others answer 404

#### Scenario: Views from the cookie
- **WHEN** a test client requests the task list without a cookie and with `task-list-view` set to `details`, and the planning list without a cookie and with `planning-list-view` set to `table`
- **THEN** the task list opens in the table view and then in the details view, and the planning list in the details view and then in the table view

#### Scenario: Two table classes
- **WHEN** the demo data set is written, the signed-in user has an access token, and the user requests these pages:
  - each main list, and each main list's details of a record that renders every table its details can hold;
  - the overview;
  - the pages of an item, a batch that has vessels, fillings and delivery lines, a vessel, a delivery note, a task, and a substance that has procedures and sequences;
  - the consumption form of an item;
  - the new delivery note form;
  - the lab notebooks and a notebook's page;
  - the imports, a vocabulary and the access tokens
- **THEN** every `table` of every answer carries exactly one of `main-table` and `aux-table`, and the tables carrying `main-table` are the main lists' tables alone, one per list

#### Scenario: Sorting text with numbers in it
- **WHEN** the database holds open vessels `#2` and `#10` of one substance, and a test client requests the vessel list with `sort=vessel`
- **THEN** it lists `#2` before `#10`

#### Scenario: Descending puts text first
- **WHEN** the vessel list of the scenario "Amounts across units and text after values" is requested with `sort=opened&dir=desc`
- **THEN** it lists the sealed vessel, then the opened vessel, then the vessel of the made batch
