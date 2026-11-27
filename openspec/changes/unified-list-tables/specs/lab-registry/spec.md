## ADDED Requirements

### Requirement: Substance details
The substance list SHALL be a main list (web-app "Main lists") whose details of a substance, `/lab/registry/substances/<key>/detail/`, need no sign-in and show:

- its name as heading, linking to its page;
- when it has a structure image (Structure images), the `figure.structure` of its page;
- its key, short name, inventory group, chemical classes, formula, molar mass, CAS number and article number, each `–` when it has none;
- its article's items in a table with the columns `Gebinde` and `Bestand` (`Container`, `Stock`), each with its article number and container size, linking to its page, and its number of containers;
- its batches, newest first as the batch list orders them, in a table with the columns `Charge`, `Datum` and `Bestand` (`Batch`, `Date`, `Stock`), each linking to its page, with its date and the amount in its open vessels by unit;
- its tasks in a table with the columns `Nr.` and `Status` (`No.`, `State`), each linking to its page, with its state;
- for each of the three tables that would have no row, `Keine` (`None`) in its place;
- a link `Substanzseite öffnen` (`Open substance page`) to the substance's page.

For a signed-in user the details also link `Bearbeiten` (`Edit`) to the substance's edit form.

#### Scenario: Details of a substance
- **WHEN** the demo data set is written and a test client requests `/lab/registry/?selected=cinnamic-acid`
- **THEN** `#item-detail` is headed `(E)-Zimtsäure` linking to `/lab/registry/substances/cinnamic-acid/`, shows the article number `CH-0012`, lists the article's items and the substance's batches, each linking to its page, and links `Substanzseite öffnen`

#### Scenario: Details of a bare substance
- **WHEN** a test client requests the substance list with `selected` naming a substance without article, batch or task
- **THEN** its details read `Keine` in place of each of the three tables

## MODIFIED Requirements

### Requirement: Live substance list
`/lab/registry/` SHALL implement live list updates (web-app "Live lists") as a main list (web-app "Main lists"):

- Its filter form (`#filters`) updates `#item-rows` in place with `morph:outerHTML`, each row carrying the stable `id="substance-row-<pk>"`. It updates `#substance-count`, `#item-detail` and `#filter-selected` out of band with `#substance-count:morph,#item-detail:morph,#filter-selected:morph`. It uses `hx-get="/lab/registry/"`, `hx-push-url="true"`, `hx-sync="#main:replace"`, and scoped triggers (`submit`, `search from:#filter-q`, `input delay:200ms from:#filter-q`, `change target:select`). It keeps its `method="get"`, `action="/lab/registry/"`, and submit button for no-script use.
- Its column header links update `#item-rows` and the same regions in place with `hx-sync="#main:replace"`, keeping their `href` fallbacks.
- When `group` or `class` holds a non-empty key that names no vocabulary term, the corresponding `<select>` SHALL keep that key as a selected `<option>`, so later live edits to `q` keep the unknown filter until the user explicitly selects `All`.
- Its view returns the complete page for plain GET requests and HTMX history restores (`HX-Request: true` with `HX-History-Restore-Request: true`), and varies on `HX-Request` and `HX-History-Restore-Request`. On non-restore HTMX GET responses it sets `HX-Push-Url` to `/lab/registry/` with:
  - trimmed non-empty `q`, `group`, and `class` parameters;
  - `sort` and `dir=desc` as web-app "Main lists" states;
  - the resolved `selected` substance key, omitted when the list is empty.
- `/lab/registry/substances/<key>/detail/` sets `HX-Replace-Url` on HTMX responses to the list URL with the active filters and `selected` naming the substance.

#### Scenario: Live filtering and canonical URL on the substance list
- **WHEN** a test client requests `/lab/registry/?q=+zimt+&group=+final-products+&class=`, `/lab/registry/?group=nope`, `/lab/registry/?group=nope&q=zimt`, `/lab/registry/?group=&q=zimt&sort=formula&dir=desc`, and `/lab/registry/?q=+` with `HX-Request: true`
- **AND** it requests `/lab/registry/?q=zimt` once with both `HX-Request: true` and `HX-History-Restore-Request: true`, and once without HTMX headers
- **THEN** all responses return complete page markup (`html`, `#main`, table, filter form) and vary on `HX-Request` and `HX-History-Restore-Request`
- **AND** `#filters` carries `hx-get="/lab/registry/"`, `hx-push-url="true"`, `hx-sync="#main:replace"`, scoped triggers (`submit`, `search from:#filter-q`, `input delay:200ms from:#filter-q`, `change target:select`), `hx-target="#item-rows"`, `hx-select="#item-rows"`, `hx-swap="morph:outerHTML"`, and disjoint `hx-select-oob="#substance-count:morph,#item-detail:morph,#filter-selected:morph"`
- **AND** populated `#item-rows` rows carry `id="substance-row-<pk>"` and `data-item` with the substance's key
- **AND** `/lab/registry/?group=nope` and `/lab/registry/?group=nope&q=zimt` render an empty `#item-rows` and a `#substance-count` of `0`, and keep `nope` as the selected `<option>` in `select[name="group"]`, whereas `/lab/registry/?group=&q=zimt&sort=formula&dir=desc` lists matching substances
- **AND** the five ordinary HTMX responses set `HX-Push-Url` to `/lab/registry/?q=zimt&group=final-products&selected=<resolved>`, `/lab/registry/?group=nope`, `/lab/registry/?q=zimt&group=nope`, `/lab/registry/?q=zimt&sort=formula&dir=desc&selected=<resolved>`, and `/lab/registry/?selected=<resolved>`, while the history-restore and plain GET responses omit `HX-Push-Url`
