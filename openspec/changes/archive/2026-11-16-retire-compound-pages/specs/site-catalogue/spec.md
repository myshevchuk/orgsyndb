## MODIFIED Requirements

### Requirement: Catalogue rows
Each body row of a catalogue table SHALL carry these attributes, which are the catalogue's records:
- `data-id`: the procedure's `id`;
- `data-title`: its `title`;
- `data-status`: its `status`;
- `data-kind`: `general` for a general procedure and `specific` otherwise (general-procedures "Scope entries");
- `data-type`, `data-tag` and `data-author`: JSON arrays of the term keys of its reaction types, tags and authors, in front-matter order;
- `data-created` and `data-modified`: its `date` and `lastmod`, formatted `2006-01-02T15:04:05Z07:00`;
- for each procedure field declared with `facet = true` (procedure-fields "Procedure field declarations"), `data-<key>`: a JSON array of machine values: for a `boolean` field `"true"` or `"false"`, for a `choice` field each value the procedure sets and each ancestor of one, each once; an unset field gives `[]`.

A term key is the key of the term in Hugo's taxonomy (`site.Taxonomies.<plural>`), which is the term as written, lowercased: `hydrolysis`, `sample-data`, and for an author its user name, such as `a.example` (procedure-authors "Author data for the site"). A reaction type's key is its vocabulary slug. The facets' machine values are these keys, the status literals `draft`, `checked` and `retired`, the kind literals `specific` and `general`, and the values of the declared facets.

#### Scenario: Rows carry the records
- **WHEN** a test scans `public/procedures/index.html` of a theme build that adds the catalogue fixtures to the test collection
- **THEN** every row's attributes equal the values computed from its published content file, each term key is the term as written, lowercased, and the author `ae.mueller`, named `Ä. Müller`, has the key `ae.mueller`

#### Scenario: Rows carry the declared facets
- **WHEN** a test scans `public/procedures/index.html` after a theme build in locale `en`
- **THEN** every row's `data-project` and `data-inert_atmosphere` equal the values computed from its published content file and the field data of the test collection's `orgsyndb.toml`, and the row of a procedure that sets `project = "first-year-practical"` has the `data-project` `["first-year-practical", "teaching"]` in some order

### Requirement: Catalogue controls
Each catalogue SHALL carry its controls in the published HTML. Its search form is the site header's; the others lie inside elements that carry `data-catalogue-controls` and `hidden`:
- **Search.** The header's `form.site-search` (site-theme "Page shell") carries `data-catalogue-search`, and its `action` resolves to the page's own URL. Its `input` carries `id="catalogue-q"`. On `/procedures/` the input's `aria-label` is `Search procedures` and its placeholder `Product, CAS or SMILES`. On a term page the `aria-label` names the scope, `Search procedures of the reaction type <label>`, `Search procedures with the tag <tag>` or `Search procedures by <author>`, and the placeholder is `Search these procedures`, short enough to show whole whatever the term. On `/general-procedures/` the `aria-label` is `Search general procedures` with the same placeholder. The form is shown without JavaScript; submitting it then reloads the page with `q`, which the static list does not apply.
- **Facets.** `div.catalogue-facets`, with `id="catalogue-facets"`, `data-catalogue-controls` and `hidden`, holds an `h2` `Filters`, then one `details.facet` per facet in the order `type`, `kind`, `status`, then each procedure field declared with `facet = true` (procedure-fields "Procedure field declarations"), in declared order, then `tag` and `author`, each carrying `data-facet` with the facet's name, which for a declared field is its key. A facet's `summary` carries an `id` and the text `Reaction type`, `Kind`, `Status`, the declared field's shown label, `Tag` or `Author`, and is followed by a `div` with `role="group"` and `aria-labelledby` naming that `id`, which holds one `label.facet-value` per value. Each holds an `input` with `type="checkbox"`, `name` the facet's name and `value` the machine value, then `span.facet-label` with the value's display label, then an empty `span.facet-count`. The `type`, `kind` and `status` facets and the declared facets carry `open`. After the group, the `type`, `tag` and `author` facets each link their directory: `All reaction types` to `/reaction_types/`, `All tags` to `/tags/` and `All authors` to `/authors/`.
- **Facet values.** The `status` facet lists `draft`, `checked` and `retired`, in that order, and the `kind` facet `specific` and `general`, in that order, with the display labels `Specific procedure` and `General procedure`. The other facets, apart from a term page's fixed facet, list each value that some published procedure carries, on every catalogue page, ordered by display label. The display label is the vocabulary label for a reaction type, the tag itself, the author's name as written, and the status and kind in the site's language. A declared facet lists, on every catalogue page, the values some published procedure carries: for a `boolean` field `true` and `false`, in that order, each only when some published procedure sets it, with the display labels compound-fields "Field display" writes for them; for a `choice` field, in the field data's `order`, each value that some published procedure sets or that is an ancestor of such a value, with its shown label as the display label, its `label.facet-value` carrying `style="--depth: <n>"`, where `n` is the number of the value's ancestors. The screen stylesheet indents a `label.facet-value` by its `--depth`.
- **Toolbar.** `div.catalogue-toolbar`, with `data-catalogue-controls` and `hidden`, holds, in order: `button.facets-toggle` with `type="button"`, `aria-controls="catalogue-facets"`, `aria-expanded="false"` and the text `Filters`; an empty `ul.catalogue-active`; `button.clear-all` with `type="button"` and the text `Clear all`; a `label` `Sort by` for `select#catalogue-sort`, whose options have the values and texts `relevance` `Relevance`, `id` `ID`, `title` `Title (A–Z)`, `created` `Created (newest first)` and `modified` `Modified (newest first)`; and a `label` `View` for `select#catalogue-view`, whose options are `table` `Table` and `details` `Details`.
- **Message.** `p.catalogue-message` carries `data-catalogue-message`, `role="status"` and `hidden`, and is empty.
- **Texts for the script.** `div.catalogue` carries the texts the script shows: `data-text-searching` `Searching…`, `data-text-unavailable` `Search unavailable`, `data-text-error` `The search index could not be loaded, so the search was not applied.`, `data-text-error-action` `Show the list without the search`, `data-text-empty` `No procedures match the search and filters.`, `data-text-ignored` `Ignored in the address: {list}` and `data-text-remove` `Remove {facet}: {value}`.

#### Scenario: Controls in the HTML
- **WHEN** a test scans `public/procedures/index.html` after a theme build in locale `en`
- **THEN** its header has the search form with the stated attributes and texts, and `div.catalogue` holds no form and has the facets, the toolbar and the message with the stated elements, attributes and texts, each container carrying `hidden`
- **AND** the header search of `public/tags/cinnamate/index.html` has the `action` `/tags/cinnamate/`, the `aria-label` `Search procedures with the tag cinnamate` and the placeholder `Search these procedures`
- **AND** the `type`, `tag` and `author` facets list exactly the term keys in use in the collection, ordered by label, the `status` facet lists the three literals in order, and the `kind` facet `specific` and `general`

#### Scenario: Declared facets in the HTML
- **WHEN** a test scans `public/procedures/index.html`, `public/general-procedures/index.html` and `public/tags/cinnamate/index.html` after a theme build in locale `en`
- **THEN** each has the facets `type`, `kind`, `status`, `project`, `inert_atmosphere`, `tag` and `author`, in this order, `project` labelled `Project` and `inert_atmosphere` `Inert atmosphere`, both carrying `open` and neither a directory link
- **AND** on each page the values, labels, order and depths of `project` and `inert_atmosphere` are those computed from the published procedures of the whole collection and the field data, `project` listing `teaching` with the depth 0 and `first-year-practical` with the depth 1

#### Scenario: Filtering procedures by a declared field
- **WHEN** the orchestrator opens `/procedures/` of the German demo build from `tools/orgsyndb serve`, ticks `Forschung` under `Projekt`, then `Ja` under `Schutzgas`, reloads, and goes Back twice (manual verification, tasks.md section 3)
- **THEN** the rows narrow to the procedures filed under a research project, then to those of them that need an inert atmosphere, with the count, the facet counts and the chips following each step; the reload keeps the address `/procedures/?project=research&inert_atmosphere=true`, and Back restores each earlier address with its rows

### Requirement: Catalogue core functions
`site/assets/js/catalogue-core.js` SHALL be a classic script, with no `import`, `export` or use of `document`, `window` or `location`, that defines `globalThis.OrgSynCatalogue`. It needs `globalThis.OrgSynSearch` from `search-terms.js`, loaded before it. A catalogue names its own facets: the procedure catalogues `type`, `kind`, `status`, the procedure fields declared with `facet = true` (requirement "Catalogue controls"), `tag` and `author`. A state is an object holding `q`, a string; `sort`, `null` or one of `relevance`, `id`, `title`, `created` and `modified`; `view`, `table` or `details`; and one key per facet of its catalogue, an array of machine values. The facets of a state are its keys other than `q`, `sort` and `view`, in the state's key order. A record is an object holding `id`; `title`; `created` and `modified`, RFC 3339 strings, on a procedure catalogue; and, for each facet, an array of machine values or a single one, a missing key holding no value. The functions are:
- `parse(search, known, fixed, offered)`: the state and the ignored parameters of an address, as the requirement "Catalogue address" states. Returns `{state, ignored}`.
- `serialize(state)`: the canonical query string of a state.
- `active(state)`: whether `OrgSynSearch.normaliseTerm(state.q)` is non-empty.
- `sortOf(state)`: the sort in effect.
- `withQuery(state, q)`: a copy of `state` with the query `q`.
- `clear(state)`: the state that Clear all leaves.
- `select(records, state, matched, language)`: the displayed IDs and the facet counts. Returns `{ids, counts}`.
- `searcher(pagefind)`: the procedure catalogue's text search, as the site-search spec states.

No function changes its arguments.

#### Scenario: A classic script without the DOM
- **WHEN** a Node test reads `site/assets/js/catalogue-core.js` and loads it with `search-terms.js` into a fresh context that defines no `document`, `window` or `location`
- **THEN** the file has no `import` or `export` statement, and `OrgSynCatalogue` has the eight functions

### Requirement: Catalogue address
`OrgSynCatalogue.parse(search, known, fixed, offered)` SHALL read the query string `search`, with or without its leading `?`, as `URLSearchParams` does. `known` maps each facet of the page's catalogue to the machine values the page knows, in the order the page lists them; its keys, in their order, are the catalogue's facets. `fixed` is the term page's facet or `null`. `offered` is `{sorts, views}`, the sorts and the views the page offers; when it is omitted the page offers every sort and both views. It returns the state, holding `q`, then the catalogue's facets in `known` order, then `sort` and `view`, and `ignored`, the list of `[name, value]` pairs it did not apply, in their order in `search`:
- **`q`.** The first `q` value, without leading or trailing whitespace, is the query; absent, it is `""`. Every later `q` is ignored.
- **Facets.** A value of a parameter named like a facet of the catalogue is selected when it is one of `known` for that facet and the facet is not `fixed`; a value given twice is selected once and not reported. Every other value of these names, including an empty one and every value of the fixed facet, is ignored. Each facet's selected values are listed in `known` order.
- **`sort`.** The first `sort` value is the sort when the page offers it and it is `id`, `title`, `created` or `modified`, or `relevance` while the query is active; otherwise it is ignored and the sort is `null`. Every later `sort` is ignored.
- **`view`.** The first `view` value is the view when the page offers it and it is `table` or `details`; otherwise it is ignored. Every later `view` is ignored. Without one the view is `table`.
- **Other names.** Every parameter with another name is ignored.

`serialize(state)` returns `""` for the default state, and otherwise `?` followed by, in order: `q`, without leading or trailing whitespace, when that is non-empty; one parameter per selected value of each of the state's facets, the facets and their values in the state's order; `sort` when it is not `null`; and `view=details` when the view is `details`. Values are encoded as `URLSearchParams` encodes them. For every state `s` whose facets are those of `known`, in `known` order, whose selections are known and listed in `known` order, and whose sort and view `parse` would keep, `serialize(parse(serialize(s), known, null, offered).state)` equals `serialize(s)`.

#### Scenario: Reading an address
- **WHEN** a Node test calls `parse` with `known` holding `type` `hydrolysis` and `acylation`, `kind` `specific` and `general`, `status` the three literals, `tag` `sample-data` and `cinnamate`, `author` `a. example` and `ä. müller`, and `fixed` `null`, on `?q=+acid+&type=acylation&type=hydrolysis&type=acylation&kind=general&tag=nope&tag=&sort=title&view=details&page=2&q=x`
- **THEN** the state is `q` `acid`, `type` `["hydrolysis", "acylation"]`, `kind` `["general"]`, no other selection, `sort` `title` and `view` `details`, and `ignored` is `[["tag", "nope"], ["tag", ""], ["page", "2"], ["q", "x"]]`

#### Scenario: Sorts and views that do not apply
- **WHEN** the same test parses `?sort=relevance`, `?q=acid&sort=relevance`, `?q=---&sort=relevance`, `?sort=newest`, `?sort=id&sort=title`, `?view=grid` and `?view=table`
- **THEN** the sorts are `null`, `relevance`, `null`, `null`, `id`, `null` and `null`, every view is `table`, and `ignored` names `sort=relevance`, nothing, `sort=relevance`, `sort=newest`, `sort=title`, `view=grid` and nothing respectively

#### Scenario: The fixed facet is not read from the address
- **WHEN** the test parses `?tag=cinnamate&status=draft` with `fixed` `tag`
- **THEN** the state selects `status` `draft` and no tag, and `ignored` is `[["tag", "cinnamate"]]`

#### Scenario: Canonical addresses
- **WHEN** the test serializes the default state; a state with query ` acetic acid `, `status` `draft` and `checked`, `author` `ä. müller`, `sort` `modified` and view `details`; and parses each result again
- **THEN** the first is `""`, the second is `?q=acetic+acid&status=draft&status=checked&author=%C3%A4.+m%C3%BCller&sort=modified&view=details`, and serializing each parsed state gives the same string

#### Scenario: Facets and offers the caller names
- **WHEN** a Node test calls `parse` with `known` holding `chemical_class` `carbonyl-compounds`, `esters` and `phenols`, then `in_house` `true` and `false`, `fixed` `null` and `offered` `{sorts: [], views: ["table"]}`, on `?in_house=true&q=ester&chemical_class=esters&type=hydrolysis&sort=title&view=details`, and serializes the state
- **THEN** the state's keys are `q`, `chemical_class`, `in_house`, `sort` and `view`, in this order, with `q` `ester`, `chemical_class` `["esters"]`, `in_house` `["true"]`, `sort` `null` and `view` `table`; `ignored` is `[["type", "hydrolysis"], ["sort", "title"], ["view", "details"]]`; and the serialized state is `?q=ester&chemical_class=esters&in_house=true`

### Requirement: Sort orders
`OrgSynCatalogue.sortOf(state)` SHALL return the state's `sort` when it is not `null` and either is not `relevance` or the query is active; otherwise `relevance` while the query is active, and `id` when it is not. `withQuery(state, q)` returns the state with the query `q`, and with the sort `null` when the sort was `relevance` and the new query is not active. `clear(state)` returns the state with the query `""` and no selections, keeping the sort, unless it was `relevance`, and the view. `select` orders the displayed records by the sort in effect, except that while the state's `sort` is `null` and the query is not active it keeps them in the order of `records`, which is by ID:
- `relevance`: the order of `matched`;
- `id`: `id` ascending, by code point;
- `title`: `title` ascending by `Intl.Collator(language, {numeric: true})`, then `id` ascending;
- `created`: `created` as an instant, newest first, then `id` ascending;
- `modified`: `modified` as an instant, newest first, then `id` ascending.

#### Scenario: Every order
- **WHEN** a Node test calls `select` with each sort and `language` `en` on records with distinct and equal titles and timestamps, among them two whose `modified` values are the same instant written with the offsets `+02:00` and `Z`, and titles that differ only in case and in a number (`4-` and `10-`)
- **THEN** each order is as stated, the two equal instants are ordered by ID, and every order lists the same IDs

#### Scenario: Relevance comes and goes with the query
- **WHEN** the test takes the default state, applies `withQuery` with `aspirin`, then with `""`; then chooses `modified`, applies `withQuery` with `aspirin` and then `clear`; then chooses `relevance` with the query `aspirin` and applies `clear`
- **THEN** `sortOf` gives `id`, `relevance`, `id`; then `modified`, `modified`, `modified`; then `relevance` and, after `clear`, `id` with the sort `null` and the view kept

#### Scenario: Page facets through every change
- **WHEN** a Node test takes a state with the keys `q` `ester`, `chemical_class` `["esters"]`, `in_house` `["true"]`, `sort` `null` and `view` `table`, in this order, and applies `withQuery` with `ketone` and `clear`; and does the same with a state that holds only `q`, `sort` and `view`
- **THEN** `withQuery` keeps both selections and `clear` empties both, each result has the input's keys in the input's order, the input is unchanged, and the state without facets keeps exactly its three keys

#### Scenario: The order of the records
- **WHEN** a Node test calls `select` on three records given in the order `b`, `c`, `a` of their IDs, with the default state, then with the sort `id`
- **THEN** the first lists `b`, `c`, `a` and the second `a`, `b`, `c`

### Requirement: Catalogue script
The catalogue, the term pages and `/general-procedures/` SHALL load one script, `/js/catalogue.<hash>.js`, with `defer`. It is built with Hugo Pipes by concatenating `site/assets/js/search-terms.js`, `catalogue-core.js` and `catalogue.js`, minified and fingerprinted. No other page loads it, and no page loads `pagefind-ui.js` or `pagefind-ui.css`. The script imports the Pagefind bundle only while the query is active, from `pagefind/pagefind.js` beside the directory of its own script URL (the URL `../pagefind/pagefind.js` resolved against it), so that the bundle loads under any path prefix.

#### Scenario: Script wiring
- **WHEN** a test scans every HTML page after a theme build
- **THEN** exactly the catalogue, the term pages and `/general-procedures/` load `/js/catalogue.<hash>.js`, which contains `OrgSynSearch`, `OrgSynCatalogue` and `pagefind/pagefind.js`, and no page references `pagefind-ui`

### Requirement: Catalogue in a browser
With JavaScript, the catalogue script SHALL make each procedure catalogue interactive as follows:
- **Start.** It removes `hidden` from every element with `data-catalogue-controls`. Its facets are the `data-facet` values of the catalogue's `details.facet` elements, in page order. Its records are the table rows: a row's `data-id`, `data-title`, `data-created` and `data-modified` give the record's keys of those names, and for each facet its `data-<facet>` attribute gives the record's values, read as a JSON array when it holds one and as a single value otherwise. Its known values are the values of the facet checkboxes outside the fixed facet; its fixed facet is the catalogue's `data-fixed`. It offers the values of the options of `#catalogue-sort` and of `#catalogue-view`, no sort and only `table` where the page has no such select. It reads the state with `parse` from the page's address. When values were ignored, it shows the `data-text-ignored` text in `p.catalogue-message`, `{list}` replaced by the ignored pairs written `name=value` and joined by `, `. When the canonical address `serialize` gives differs from the page's, it replaces the history entry with it.
- **Controls follow the state.** The search field is set to the query when the state comes from the address, from `Clear all` or from the error button, and typing never rewrites it; each checkbox outside the fixed facet is checked when its value is selected, and the fixed facet's checkbox stays checked, disabled and shown; where the page has them, the sort select shows `sortOf` and offers `Relevance` only while the query is active, and the view select shows the view; the catalogue carries `data-view` with the view. `ul.catalogue-active` holds one `li` per selected value, in facet order and then the state's order, holding a `button` whose text is `<facet name>: <display label>` and whose `aria-label` is the `data-text-remove` text with `{facet}` and `{value}` replaced. `Clear all` is shown only while the query is non-empty or a value is selected. A facet that the page does not render `open`, such as the procedure catalogues' `tag` and `author`, opens while a value of it is selected.
- **Results.** Without an active query the records are selected with `matched` `null`. With one, the matching IDs come from the searcher, one search per distinct normalised query in a page view; while a search is pending, `div.catalogue-results` carries `aria-busy="true"` and the count reads the `data-text-searching` text. Each change of state starts a new render, and a search result is used only by the latest render. The displayed rows are shown in order and every other row is hidden. Each `span.facet-count` holds its value's count; outside the fixed facet, an unselected value whose count is 0 is hidden, and a selected one is shown whatever its count. The fixed facet's count is the number of displayed rows.
- **Count and messages.** While the query is non-empty or a value is selected, `p.catalogue-count` reads its `data-filtered` text with `{shown}` and `{total}` replaced by the number of displayed rows and of all rows; otherwise it reads its original text. Numbers are written with `Intl.NumberFormat` of the page's language. When no row is displayed, `p.catalogue-message` shows the `data-text-empty` text.
- **Index errors.** On a procedure catalogue, when the bundle cannot be imported or a search fails while the query is active, no row is shown, the facet counts are hidden, the count reads the `data-text-unavailable` text, and `p.catalogue-message` shows the `data-text-error` text followed by a `button` with the `data-text-error-action` text, which removes the query.
- **Changes and history.** Typing in the search field changes the query 250 ms after the last keystroke, through `withQuery`. The first such change of a run of edits pushes a history entry and later ones replace it; the run ends when the field loses focus, when the form is submitted, or with any other change. Submitting the form applies the field at once and loads no page. Each checkbox change, chip, `Clear all` (through `clear`), sort change, view change and the error button pushes one history entry. A change that leaves the address unchanged adds no entry. Back and Forward restore the state of the address they reach, with its controls, results, counts and order.
- **Focus.** Removing a selection with its chip moves focus to the next chip, else the previous one, else the search field. `Clear all` and the error button move focus to the search field. No other change moves focus.
- **Narrow windows.** On a catalogue with facets, below 55rem the facets are hidden until `button.facets-toggle` opens them; the button's `aria-expanded` follows. At 55rem and wider the facets are always shown and the button is not.

#### Scenario: Searching and filtering together
- **WHEN** the orchestrator opens `/procedures/` from `tools/orgsyndb serve`, types `cinnamate`, then ticks the status `draft` and a tag (manual verification, tasks.md section 3)
- **THEN** the rows narrow to the matches of the query and the filters, the count reads `<shown> of <total> procedures`, every facet count follows the stated rule, the chips list the selections, and the sort select offers and shows `Relevance`
- **AND** the page text contains no part of a SMILES index

#### Scenario: The address restores the catalogue
- **WHEN** the orchestrator opens `/procedures/?q=acid&type=hydrolysis&sort=title&view=details` directly, reloads it, changes the sort and a facet, types a word letter by letter into the cleared search field with pauses longer than 250 ms, moves focus away, then goes Back three times and Forward once (manual verification, tasks.md section 3)
- **THEN** each page shown has the controls, rows, counts and order of its address, and the typed word added exactly one history entry
- **AND** opening `/procedures/?type=nope&tag=` shows the ignored-parameters notice, lists every procedure, and leaves the address `/procedures/`

#### Scenario: A slow search does not overwrite a newer state
- **WHEN** a browser check delays the first Pagefind search and changes the query before it resolves (manual verification, tasks.md section 3)
- **THEN** the rows and counts shown are those of the later query

#### Scenario: Keyboard use
- **WHEN** the orchestrator uses only the keyboard on `/procedures/` (manual verification, tasks.md section 3)
- **THEN** Tab reaches the search field, the facets' summaries and checkboxes, the chips, Clear all, both selects and the table links, each shows a focus outline, Space toggles a checkbox and opens a summary, and focus moves only as the requirement states

#### Scenario: Index error
- **WHEN** the orchestrator removes `pagefind/pagefind.js` from a served copy of the build and searches (manual verification, tasks.md section 3)
- **THEN** the catalogue shows no rows, the error text and its button, and the button returns to the full list with the filters kept

## REMOVED Requirements

### Requirement: Compound catalogue
**Reason**: The lab's substance list (lab-registry "Registry pages") lists, searches and filters the substances; the site keeps no compound pages.

### Requirement: Compound text search
**Reason**: Only the compound catalogue searched its own rows; every remaining catalogue searches with Pagefind.

### Requirement: Compound tabs
**Reason**: The compound catalogue and its tab pages are gone; the lab's list filters by inventory group.
