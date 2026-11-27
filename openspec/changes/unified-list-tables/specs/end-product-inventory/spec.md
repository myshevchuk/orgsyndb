## ADDED Requirements

### Requirement: Batch details
The batch list SHALL be a main list (web-app "Main lists") whose details of a batch, `/lab/inventory/batches/<id>/detail/`, show:

- the batch as heading, linking to its page;
- its substance, linking to its page, with the article number of the substance's article when there is one;
- its source as the batch list shows it;
- for a made batch, its journal entry, linking to its notebook's page, and its yield;
- its date;
- each field `–` when it has no value;
- its open vessels in a table with the columns `Gefäß`, `Art`, `Ort` and `Menge` (`Vessel`, `Kind`, `Location`, `Amount`), each vessel as `#<id>` linking to its page, ordered as the batch page orders them, or `Keine` (`None`) when it has none;
- a link `Chargenseite öffnen` (`Open batch page`) to the batch's page.

For a signed-in user the details also link `Bearbeiten` (`Edit`) and `Neues Gefäß` (`New vessel`), as the batch page does.

#### Scenario: Details of a batch
- **WHEN** a made batch `KL0412` of `cinnamic-acid` naming the journal entry `AE-1/9` has a stored vessel of `2` g in `Kühlschrank 2` and a used-up flask, and a test client requests the batch list with `selected` naming it
- **THEN** `#item-detail` is headed `KL0412` linking to `/lab/inventory/batches/<id>/`, names `CH-0012`, links `AE-1/9` to `/lab/journal/AE-1/`, lists the stored vessel with `Kühlschrank 2` and `2 g` and not the flask, and links `Chargenseite öffnen`

### Requirement: Vessel details
The vessel list SHALL be a main list (web-app "Main lists") whose details of a vessel, `/lab/inventory/vessels/<id>/detail/`, show:

- the vessel as heading, linking to its page;
- its batch, linking to its page;
- its substance, linking to its page, with the article number of the substance's article when there is one;
- its kind, amount, location and note;
- for a vessel of a bought batch, `Angebrochen am <date>` (`Opened on <date>`) or `versiegelt` (`sealed`);
- the mark `aufgebraucht` (`used up`) at zero;
- its five newest movements in booking order, newest first, with date, kind, amount and note, as the bulk list's details show them;
- a link `Gefäßseite öffnen` (`Open vessel page`) to the vessel's page.

For a signed-in user the details offer `Korrigieren` (`Correct`) and `Bearbeiten` (`Edit`), and, on an open vessel, `Entnahme` (`Withdraw`) and `Umfüllen` (`Transfer`). They open the vessel's forms in a dialog over the page (web-app "Form dialogs"), as the intermediate list's details do.

#### Scenario: Details of a vessel
- **WHEN** a bought vessel of `benzaldehyde` from `Sigma-Aldrich` holding `41` g in `Kühlschrank 1`, opened on 2026-03-05, had two withdrawals booked, and a signed-in user requests the vessel list with `selected` naming it
- **THEN** `#item-detail` is headed by the vessel linking to its page, shows `41 g`, `Kühlschrank 1` and `Angebrochen am 05.03.2026`, lists its opening and both withdrawals newest first, and offers `Entnahme`, `Umfüllen`, `Korrigieren` and `Bearbeiten` opening in a dialog

#### Scenario: A used-up vessel
- **WHEN** a signed-in user requests the vessel list with `empty=1` and `selected` naming a used-up vessel
- **THEN** its details carry `aufgebraucht` and offer `Korrigieren` and `Bearbeiten` but neither `Entnahme` nor `Umfüllen`

## MODIFIED Requirements

### Requirement: Live inventory lists
All seven inventory lists—`/lab/inventory/end-products/`, `/lab/inventory/intermediates/`, `/lab/inventory/chemicals/`, `/lab/inventory/end-products/bulk/`, `/lab/inventory/deliveries/`, `/lab/inventory/batches/`, and `/lab/inventory/vessels/`—SHALL implement live list updates (web-app "Live lists") as main lists (web-app "Main lists"):

- Each list's filter form updates `#item-rows` in place with `morph:outerHTML` and updates its count, `#item-detail` and `#filter-selected` out of band with disjoint `:morph` selectors. It uses triggers scoped exclusively to its own controls: `submit`; a single `change` clause, `change target:select` when only selects are inside `#filters`, or `change target:(select, input[type=checkbox])` when both selects and checkboxes are inside `#filters`; and `search from:#filter-q` / `input delay:200ms from:#filter-q` where present. It synchronizes with split-view row requests on `#main:replace`.
- Each list's column header links update `#item-rows` and its dependent regions in place via HTMX with `hx-sync="#main:replace"`, keeping their `href` fallbacks.
- On `/lab/inventory/end-products/`, `#filters` also triggers on `change from:#filter-container`, `change from:#filter-compartment`, and `change from:#filter-box`. The header links (`#item-head`), the stock-status menu links (`#stock-entries`) and the `Reset` link in `#list-summary` use disjoint OOB targets that morph `#filters:morph` and `#more-filters:morph`, without separately targeting their children `#filter-selected` or `#filter-hidden`, so visible filter controls stay synchronized with the applied response and URL. They keep their `href` / `method="get"` fallbacks.
- Each list's non-restore HTMX GET response sets `HX-Push-Url` to its canonical path and cleaned query. On every list the query names `sort` and `dir=desc` as web-app "Main lists" states, and the resolved `selected` (omitted when empty):
  - `/lab/inventory/end-products/`: nonempty `q`, `category`, `stock`, `container`, `compartment`, `box`, and `selected` naming an item ID;
  - `/lab/inventory/intermediates/`: nonempty `q`, `location`, `class`, `flask=1`, `old=1`, and `selected` naming a substance key;
  - `/lab/inventory/chemicals/`: nonempty `q`, `location`, `group`, `supplier`, `sealed=1`, and `selected` naming a substance key;
  - `/lab/inventory/end-products/bulk/`: trimmed `q`, trimmed `location`, valid `source`, `flask=1`, and `selected` naming a vessel ID;
  - `/lab/inventory/deliveries/`: trimmed `q`, numeric `item`, and `selected` naming a note ID;
  - `/lab/inventory/batches/`: trimmed `q`, and `selected` naming a batch ID;
  - `/lab/inventory/vessels/`: valid `kind`, `empty=1`, and `selected` naming a vessel ID.
- The details endpoints set `HX-Replace-Url` to their list URL with the active filters and `selected` naming the requested record. They are `/lab/inventory/items/<id>/detail/`, `/lab/inventory/intermediates/<key>/`, `/lab/inventory/chemicals/<key>/`, `/lab/inventory/end-products/bulk/<id>/`, `/lab/inventory/deliveries/<id>/detail/`, `/lab/inventory/batches/<id>/detail/`, and `/lab/inventory/vessels/<id>/detail/`.

#### Scenario: Live filtering on category lists
- **WHEN** a test client requests `/lab/inventory/intermediates/?location=Regal+1&sealed=1&selected=missing`, `/lab/inventory/intermediates/?location=nowhere`, and `/lab/inventory/chemicals/?sealed=1&flask=1` with `HX-Request: true`
- **THEN** each page's filter form carries `hx-get`, `hx-push-url="true"`, `hx-sync="#main:replace"`, scoped triggers, `hx-target="#item-rows"`, `hx-select="#item-rows"`, `hx-swap="morph:outerHTML"`, and `hx-select-oob` naming `#category-count:morph`, `#item-detail:morph`, and `#filter-selected:morph`
- **AND** the first sets `HX-Push-Url` to `/lab/inventory/intermediates/?location=Regal+1&selected=<resolved>`, dropping `sealed`; the second to `/lab/inventory/intermediates/?location=nowhere` with no `selected`; and the third to `/lab/inventory/chemicals/?sealed=1&selected=<resolved>`, dropping `flask`

#### Scenario: Live filtering, sorting, stock status, and reset on the item list
- **WHEN** a test client requests `/lab/inventory/end-products/?category=Ester&stock=bogus&sort=stock&dir=desc&q=` with `HX-Request: true`
- **THEN** `#filters`, the `#item-head` sort links, the `#stock-entries` links, and the `#list-summary` reset link carry HTMX live attributes targeting `#item-rows` with `morph:outerHTML` and `hx-sync="#main:replace"`, and `#filters` triggers on `#filter-container`, `#filter-compartment`, and `#filter-box`
- **AND** the sort, stock, and Reset links' `hx-select-oob` morph `#filters:morph` and `#more-filters:morph` without overlapping `#filter-selected` or `#filter-hidden`, and `HX-Push-Url` equals `/lab/inventory/end-products/?category=Ester&sort=stock&dir=desc&selected=<resolved>`

#### Scenario: Live filtering on bulk, delivery, batch, and vessel lists
- **WHEN** a test client requests `/lab/inventory/end-products/bulk/?flask=1&source=bogus&q=+CH+`, `/lab/inventory/deliveries/?q=+LS+&item=abc`, `/lab/inventory/batches/?q=+B-1+&sort=bogus`, and `/lab/inventory/vessels/?kind=bogus&empty=1&sort=amount` with `HX-Request: true`
- **THEN** each list's filter form carries scoped HTMX live attributes targeting `#item-rows` with `morph:outerHTML`, `hx-sync="#main:replace"`, and `:morph` OOB targets for its count, `#item-detail` and `#filter-selected`
- **AND** their `HX-Push-Url` headers drop invalid values, trim `q`, resolve `selected`, drop the batch list's unknown `sort`, and keep the vessel list's `sort=amount`

#### Scenario: Inventory details endpoints replace the list URL
- **WHEN** a test client requests these with `HX-Request: true`:
  - `/lab/inventory/items/<id>/detail/` with `HX-Current-URL: http://testserver/lab/inventory/end-products/?category=Ester&selected=999`;
  - `/lab/inventory/intermediates/<key>/?location=Regal+1`;
  - `/lab/inventory/items/<id>/detail/` with a foreign-host `HX-Current-URL`;
  - `/lab/inventory/batches/<id>/detail/` with `HX-Current-URL: http://testserver/lab/inventory/batches/?q=KL&sort=yield`
- **THEN** the first sets `HX-Replace-Url` to `/lab/inventory/end-products/?category=Ester&selected=<id>`, the second to `/lab/inventory/intermediates/?location=Regal+1&selected=<key>`, the third to `/lab/inventory/end-products/?selected=<id>`, and the fourth to `/lab/inventory/batches/?q=KL&sort=yield&selected=<id>`
- **AND** all four return only `#item-detail`
