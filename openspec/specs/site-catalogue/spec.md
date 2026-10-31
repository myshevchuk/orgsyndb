# site-catalogue Specification

## Purpose
Define the procedure catalogue at `/procedures/` and on the term pages: its pages and row records, its controls, the state it keeps in the address, facet matching and counts, sort orders, the Details view, the fixed scope of a term page, its behaviour in a browser and the functions of its core script.
## Requirements
### Requirement: Catalogue pages
The site SHALL publish the catalogue at `/procedures/`, from `site/layouts/section.html`, on every reaction-type, tag and author term page, from `site/layouts/term.html`, and at `/general-procedures/` (general-procedures "General procedures view"). On each of these pages `main` holds one `div.catalogue` carrying `data-catalogue`, and on a term page and on `/general-procedures/` also `data-fixed` naming the page's facet (`type`, `tag`, `author` or `kind`). It holds, in this order:
1. `div.list-head`, holding the `h1` and `p.catalogue-count`. The `h1` is `Procedures` on `/procedures/`, `General procedures` on `/general-procedures/` and the term's display title on a term page. `p.catalogue-count` carries `role="status"`, `data-catalogue-count` and `data-filtered="{shown} of {total} procedures"`, and its text is `<n> procedures`, or `1 procedure`, where `n` is the number of table rows.
2. On a term page and on `/general-procedures/` only, `p.catalogue-scope`, as the requirement "Fixed scope on term pages" states.
3. A `noscript` element holding `p.catalogue-noscript`, whose text is `Search, filters and sorting need JavaScript. Without it, this page lists its procedures by ID. Browse them by reaction type, tag or author.`, where `reaction type`, `tag` and `author` link to `/reaction_types/`, `/tags/` and `/authors/`.
4. `div.catalogue-layout`, holding `div.catalogue-facets` and then `div.catalogue-results`. The results hold `div.catalogue-toolbar`, then `p.catalogue-message`, then the procedure table.

The procedure table is rendered by `site/layouts/_partials/procedure-table.html`: a `table.procedure-list`, the only child of a `div.table-scroll` with `tabindex="0"`, `role="region"` and `aria-label="Procedures"`. Its column headers are `ID`, `Procedure`, `Reaction type`, `Status` and `Modified`, each a `th` with `scope="col"`. It has one body row per procedure in scope, by `id` ascending: on `/procedures/` every published procedure, on a term page exactly the published procedures that carry the term, and on `/general-procedures/` exactly the published general procedures. In each row:
- the `ID` cell links the procedure page with the ID as text;
- the `Procedure` cell links it with the title as text;
- the `Reaction type` cell holds the vocabulary labels of its reaction types, joined by `, `;
- the `Status` cell holds `span.badge.badge--<status>` with the status;
- the `Modified` cell holds `<time datetime="<RFC 3339 lastmod>">YYYY-MM-DD</time>`.

Each of these pages loads the catalogue script. Its one `input` with `name="q"` is the catalogue's search field, in the site header (requirement "Catalogue controls").

#### Scenario: The catalogue lists every procedure once
- **WHEN** a test scans `public/procedures/index.html` after a theme build in locale `en`
- **THEN** its `h1` is `Procedures`, `p.catalogue-count` reads `9 procedures` with the stated attributes, and the table has the five column headers and one row per published ID, each ID once, in ascending order
- **AND** each row's cells link the procedure page and show its label, status and `lastmod` date as stated
- **AND** the page has the `noscript` note with its three links, no `form` inside `div.catalogue`, exactly one `input[name=q]`, in the site header, and loads `/js/catalogue.<hash>.js`

#### Scenario: Term pages are catalogue pages
- **WHEN** a test scans every term page under `public/reaction_types/`, `public/tags/` and `public/authors/` after a theme build in locale `en`
- **THEN** each has `div.catalogue` with `data-fixed` equal to `type`, `tag` or `author`, the term's display title as `h1`, a count of its rows, and a table whose rows are exactly the IDs carrying the term, ascending

### Requirement: Catalogue rows
Each body row of a catalogue table SHALL carry these attributes, which are the catalogue's records:
- `data-id`: the procedure's `id`;
- `data-title`: its `title`;
- `data-status`: its `status`;
- `data-kind`: `general` for a general procedure and `specific` otherwise (general-procedures "Scope entries");
- `data-type`, `data-tag` and `data-author`: JSON arrays of the term keys of its reaction types, tags and authors, in front-matter order;
- `data-created` and `data-modified`: its `date` and `lastmod`, formatted `2006-01-02T15:04:05Z07:00`.

A term key is the key of the term in Hugo's taxonomy (`site.Taxonomies.<plural>`), which is the term as written, lowercased: `hydrolysis`, `sample-data`, `a. example` for the author `A. Example`, and `ä. müller` for `Ä. Müller`. A reaction type's key is its vocabulary slug. The facets' machine values are these keys, the status literals `draft`, `checked` and `retired`, and the kind literals `specific` and `general`.

#### Scenario: Rows carry the records
- **WHEN** a test scans `public/procedures/index.html` of a theme build that adds the catalogue fixtures to the test collection
- **THEN** every row's attributes equal the values computed from its published content file, each term key is the term as written, lowercased, and the author `Ä. Müller` has the key `ä. müller`

### Requirement: Catalogue controls
Each catalogue SHALL carry its controls in the published HTML. Its search form is the site header's; the others lie inside elements that carry `data-catalogue-controls` and `hidden`:
- **Search.** The header's `form.site-search` (site-theme "Page shell") carries `data-catalogue-search`, and its `action` resolves to the page's own URL. Its `input` carries `id="catalogue-q"`. On `/procedures/` the input's `aria-label` is `Search procedures` and its placeholder `Product, CAS, SMILES or keyword`. On a term page the `aria-label` names the scope, `Search procedures of the reaction type <label>`, `Search procedures with the tag <tag>` or `Search procedures by <author>`, and the placeholder is `Search these procedures`, short enough to show whole whatever the term. On `/general-procedures/` the `aria-label` is `Search general procedures` with the same placeholder. The form is shown without JavaScript; submitting it then reloads the page with `q`, which the static list does not apply.
- **Facets.** `div.catalogue-facets`, with `id="catalogue-facets"`, `data-catalogue-controls` and `hidden`, holds an `h2` `Filters`, then one `details.facet` per facet in the order `type`, `kind`, `status`, `tag`, `author`, each carrying `data-facet` with the facet's name. A facet's `summary` carries an `id` and the text `Reaction type`, `Kind`, `Status`, `Tag` or `Author`, and is followed by a `div` with `role="group"` and `aria-labelledby` naming that `id`, which holds one `label.facet-value` per value. Each holds an `input` with `type="checkbox"`, `name` the facet's name and `value` the machine value, then `span.facet-label` with the value's display label, then an empty `span.facet-count`. The `type`, `kind` and `status` facets carry `open`. After the group, the `type`, `tag` and `author` facets each link their directory: `All reaction types` to `/reaction_types/`, `All tags` to `/tags/` and `All authors` to `/authors/`.
- **Facet values.** The `status` facet lists `draft`, `checked` and `retired`, in that order, and the `kind` facet `specific` and `general`, in that order, with the display labels `Specific procedure` and `General procedure`. The other facets, apart from a term page's fixed facet, list each value that some published procedure carries, on every catalogue page, ordered by display label. The display label is the vocabulary label for a reaction type, the tag itself, the author's name as written, and the status and kind in the site's language.
- **Toolbar.** `div.catalogue-toolbar`, with `data-catalogue-controls` and `hidden`, holds, in order: `button.facets-toggle` with `type="button"`, `aria-controls="catalogue-facets"`, `aria-expanded="false"` and the text `Filters`; an empty `ul.catalogue-active`; `button.clear-all` with `type="button"` and the text `Clear all`; a `label` `Sort by` for `select#catalogue-sort`, whose options have the values and texts `relevance` `Relevance`, `id` `ID`, `title` `Title (A–Z)`, `created` `Created (newest first)` and `modified` `Modified (newest first)`; and a `label` `View` for `select#catalogue-view`, whose options are `table` `Table` and `details` `Details`.
- **Message.** `p.catalogue-message` carries `data-catalogue-message`, `role="status"` and `hidden`, and is empty.
- **Texts for the script.** `div.catalogue` carries the texts the script shows: `data-text-searching` `Searching…`, `data-text-unavailable` `Search unavailable`, `data-text-error` `The search index could not be loaded, so the search was not applied.`, `data-text-error-action` `Show the list without the search`, `data-text-empty` `No procedures match the search and filters.`, `data-text-ignored` `Ignored in the address: {list}` and `data-text-remove` `Remove {facet}: {value}`.

#### Scenario: Controls in the HTML
- **WHEN** a test scans `public/procedures/index.html` after a theme build in locale `en`
- **THEN** its header has the search form with the stated attributes and texts, and `div.catalogue` holds no form and has the facets, the toolbar and the message with the stated elements, attributes and texts, each container carrying `hidden`
- **AND** the header search of `public/tags/cinnamate/index.html` has the `action` `/tags/cinnamate/`, the `aria-label` `Search procedures with the tag cinnamate` and the placeholder `Search these procedures`
- **AND** the `type`, `tag` and `author` facets list exactly the term keys in use in the collection, ordered by label, the `status` facet lists the three literals in order, and the `kind` facet `specific` and `general`

### Requirement: Catalogue core functions
`site/assets/js/catalogue-core.js` SHALL be a classic script, with no `import`, `export` or use of `document`, `window` or `location`, that defines `globalThis.OrgSynCatalogue`. It needs `globalThis.OrgSynSearch` from `search-terms.js`, loaded before it. A catalogue names its own facets: the procedure catalogues `type`, `kind`, `status`, `tag` and `author`, and the compound catalogue its facet fields (requirement "Compound catalogue"). A state is an object holding `q`, a string; `sort`, `null` or one of `relevance`, `id`, `title`, `created` and `modified`; `view`, `table` or `details`; and one key per facet of its catalogue, an array of machine values. The facets of a state are its keys other than `q`, `sort` and `view`, in the state's key order. A record is an object holding `id`; `title`; `created` and `modified`, RFC 3339 strings, on a procedure catalogue; `text`, the text the compound catalogue searches; and, for each facet, an array of machine values or a single one, a missing key holding no value. The functions are:
- `parse(search, known, fixed, offered)`: the state and the ignored parameters of an address, as the requirement "Catalogue address" states. Returns `{state, ignored}`.
- `serialize(state)`: the canonical query string of a state.
- `active(state)`: whether `OrgSynSearch.normaliseTerm(state.q)` is non-empty.
- `sortOf(state)`: the sort in effect.
- `withQuery(state, q)`: a copy of `state` with the query `q`.
- `clear(state)`: the state that Clear all leaves.
- `select(records, state, matched, language)`: the displayed IDs and the facet counts. Returns `{ids, counts}`.
- `searcher(pagefind)`: the procedure catalogue's text search, as the site-search spec states.
- `match(records, q)`: the compound catalogue's text search, as the requirement "Compound text search" states.

No function changes its arguments.

#### Scenario: A classic script without the DOM
- **WHEN** a Node test reads `site/assets/js/catalogue-core.js` and loads it with `search-terms.js` into a fresh context that defines no `document`, `window` or `location`
- **THEN** the file has no `import` or `export` statement, and `OrgSynCatalogue` has the nine functions

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

#### Scenario: The facets and offers of a compound catalogue
- **WHEN** a Node test calls `parse` with `known` holding `chemical_class` `carbonyl-compounds`, `esters` and `phenols`, then `in_house` `true` and `false`, `fixed` `null` and `offered` `{sorts: [], views: ["table"]}`, on `?in_house=true&q=ester&chemical_class=esters&type=hydrolysis&sort=title&view=details`, and serializes the state
- **THEN** the state's keys are `q`, `chemical_class`, `in_house`, `sort` and `view`, in this order, with `q` `ester`, `chemical_class` `["esters"]`, `in_house` `["true"]`, `sort` `null` and `view` `table`; `ignored` is `[["type", "hydrolysis"], ["sort", "title"], ["view", "details"]]`; and the serialized state is `?q=ester&chemical_class=esters&in_house=true`

### Requirement: Facet matching and counts
`OrgSynCatalogue.select(records, state, matched, language)` SHALL compute the displayed IDs and the facet counts over the state's facets. Records after the first with the same `id` are left out. `matched` is `null` when the query is not active, and otherwise the list of IDs that match the query, in relevance order. A record:
- matches the query when `matched` is `null` or holds its `id`;
- matches a facet when the state selects no value of that facet, or when the record carries at least one selected value of it;
- is displayed when it matches the query and every facet.

`ids` lists each displayed record's `id` once, in the order of the requirement "Sort orders". `counts` maps each facet of the state to an object that holds every value some record carries or the state selects, and gives for a value `v` of facet `f` the number of records that match the query, carry `v` in `f`, and match every facet other than `f`.

#### Scenario: OR within a facet, AND across facets
- **WHEN** a Node test calls `select` on six records with `matched` `null`, selecting `type` `hydrolysis` and `acylation`; then also `status` `draft`; then only `status` `retired`
- **THEN** the first lists every record of either type, the second only those that are also `draft`, and the third exactly the retired ones

#### Scenario: Counts leave out the facet's own selections
- **WHEN** the same test selects `type` `hydrolysis` and `tag` `cinnamate`, with `matched` naming four of the records
- **THEN** each `type` count is the number of matched records with that type and the tag `cinnamate`, each `tag` count the number of matched records of type `hydrolysis` with that tag, each `status` and `author` count the number of displayed records with that value, and a selected value that no remaining record carries has the count 0

#### Scenario: Facets that a page names
- **WHEN** a Node test calls `select` with `matched` `null` on four records with the facets `chemical_class` and `in_house`, whose `chemical_class` arrays hold `["esters", "acid-derivatives", "carbonyl-compounds"]`, `["ketones", "carbonyl-compounds"]`, `["alcohols"]` and `[]`, and whose `in_house` values are `"true"`, `"false"`, `"true"` and none, with a state of these two facets selecting `chemical_class` `carbonyl-compounds`; then also `in_house` `true`
- **THEN** the first lists the first two records, with the count 2 for `carbonyl-compounds`, 1 for `esters` and 1 for `alcohols`; and the second lists the first record only, with the `in_house` counts 1 for `true` and 1 for `false`, and the `chemical_class` counts 1 for `carbonyl-compounds` and 1 for `alcohols`

#### Scenario: A value and its ancestor on one record
- **WHEN** a Node test calls `select` with `matched` `null` on two records whose `chemical_class` arrays hold `["ketones", "carbonyl-compounds", "carbonyl-compounds"]` and `["esters", "carbonyl-compounds"]`, selecting no value
- **THEN** both are listed, and the counts are 2 for `carbonyl-compounds`, 1 for `ketones` and 1 for `esters`

#### Scenario: Filters without a query and an empty result
- **WHEN** the test selects `author` `ä. müller` with `matched` `null`, and then sets `matched` to `[]`
- **THEN** the first lists exactly that author's records, and the second lists none and gives every count as 0

#### Scenario: Each procedure once
- **WHEN** the test passes a record list that repeats one `id` and a `matched` list that names it twice
- **THEN** `ids` holds that `id` once and every count counts it once

### Requirement: Sort orders
`OrgSynCatalogue.sortOf(state)` SHALL return the state's `sort` when it is not `null` and either is not `relevance` or the query is active; otherwise `relevance` while the query is active, and `id` when it is not. `withQuery(state, q)` returns the state with the query `q`, and with the sort `null` when the sort was `relevance` and the new query is not active. `clear(state)` returns the state with the query `""` and no selections, keeping the sort, unless it was `relevance`, and the view. `select` orders the displayed records by the sort in effect, except that while the state's `sort` is `null` and the query is not active it keeps them in the order of `records`, which on a procedure catalogue is by ID and on the compound catalogue by shown name:
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
The catalogue, the term pages, `/general-procedures/` and `/compounds/` SHALL load one script, `/js/catalogue.<hash>.js`, with `defer`. It is built with Hugo Pipes by concatenating `site/assets/js/search-terms.js`, `catalogue-core.js` and `catalogue.js`, minified and fingerprinted. No other page loads it, and no page loads `pagefind-ui.js` or `pagefind-ui.css`. On a catalogue without `data-search="text"`, the script imports the Pagefind bundle only while the query is active, from `pagefind/pagefind.js` beside the directory of its own script URL (the URL `../pagefind/pagefind.js` resolved against it), so that the bundle loads under any path prefix. On the compound catalogue it never imports it.

#### Scenario: Script wiring
- **WHEN** a test scans every HTML page after a theme build
- **THEN** exactly the catalogue, the term pages, `/general-procedures/` and `/compounds/` load `/js/catalogue.<hash>.js`, which contains `OrgSynSearch`, `OrgSynCatalogue` and `pagefind/pagefind.js`, and no page references `pagefind-ui`

### Requirement: Catalogue in a browser
With JavaScript, the catalogue script SHALL make each catalogue interactive, the procedure catalogues and the compound catalogue alike, as follows:
- **Start.** It removes `hidden` from every element with `data-catalogue-controls`. Its facets are the `data-facet` values of the catalogue's `details.facet` elements, in page order. Its records are the table rows: a row's `data-id`, `data-title`, `data-created`, `data-modified` and `data-text` give the record's keys of those names, and for each facet its `data-<facet>` attribute gives the record's values, read as a JSON array when it holds one and as a single value otherwise. Its known values are the values of the facet checkboxes outside the fixed facet; its fixed facet is the catalogue's `data-fixed`. It offers the values of the options of `#catalogue-sort` and of `#catalogue-view`, no sort and only `table` where the page has no such select. It reads the state with `parse` from the page's address. When values were ignored, it shows the `data-text-ignored` text in `p.catalogue-message`, `{list}` replaced by the ignored pairs written `name=value` and joined by `, `. When the canonical address `serialize` gives differs from the page's, it replaces the history entry with it.
- **Controls follow the state.** The search field is set to the query when the state comes from the address, from `Clear all` or from the error button, and typing never rewrites it; each checkbox outside the fixed facet is checked when its value is selected, and the fixed facet's checkbox stays checked, disabled and shown; where the page has them, the sort select shows `sortOf` and offers `Relevance` only while the query is active, and the view select shows the view; the catalogue carries `data-view` with the view. `ul.catalogue-active` holds one `li` per selected value, in facet order and then the state's order, holding a `button` whose text is `<facet name>: <display label>` and whose `aria-label` is the `data-text-remove` text with `{facet}` and `{value}` replaced. `Clear all` is shown only while the query is non-empty or a value is selected. A facet that the page does not render `open`, such as the procedure catalogues' `tag` and `author`, opens while a value of it is selected.
- **Results.** Without an active query the records are selected with `matched` `null`. With one, on the compound catalogue, which carries `data-search="text"`, the matching IDs are those `match` gives for the records and the query, at once. On a procedure catalogue they come from the searcher, one search per distinct normalised query in a page view; while a search is pending, `div.catalogue-results` carries `aria-busy="true"` and the count reads the `data-text-searching` text. Each change of state starts a new render, and a search result is used only by the latest render. The displayed rows are shown in order and every other row is hidden. Each `span.facet-count` holds its value's count; outside the fixed facet, an unselected value whose count is 0 is hidden, and a selected one is shown whatever its count. The fixed facet's count is the number of displayed rows.
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

### Requirement: Fixed scope on term pages
A term page's catalogue SHALL treat its term as a fixed scope, applied with every user choice, and the catalogue of `/general-procedures/` SHALL treat the `kind` value `general` so, with the scope text that general-procedures "General procedures view" gives:
- **Static label.** `p.catalogue-scope` reads `Only procedures of the reaction type <label>`, `Only procedures with the tag <tag>` or `Only procedures by <author>`, then ` · ` and an `a` with `data-browse-all`, the text `Browse all procedures` and the `href` `/procedures/`. It holds no other link.
- **Fixed facet.** The page's facet is a `details.facet` carrying `data-fixed` and `open`, whose only value is the term, its checkbox `checked` and `disabled`. The other facets list their values as on `/procedures/`; a value that no row of the page carries counts 0, so the script shows it only while it is selected.
- **Results.** The records are the page's rows, so no search result or filter shows a procedure outside the scope; `Clear all` keeps the scope.
- **Browse all.** The script sets the `data-browse-all` link to its original URL followed by `serialize` of the current state, which never holds a value of the fixed facet. Without JavaScript it leads to `/procedures/`.

#### Scenario: Scope in the HTML
- **WHEN** a test scans `public/tags/cinnamate/index.html`, `public/reaction_types/hydrolysis/index.html` and `public/authors/a.-example/index.html` after a theme build in locale `en`
- **THEN** each has the scope text and the `Browse all procedures` link to `/procedures/` as the scope line's only link, and the fixed facet with one checked, disabled value, while its other facets list the same values as those of `/procedures/`

#### Scenario: Searching inside a scope
- **WHEN** the orchestrator opens `/tags/cinnamate/?author=a.+example`, then `/tags/cinnamate/`, chooses a sort, searches `acid`, ticks a status, follows Browse all procedures, goes Back and presses Clear all (manual verification, tasks.md section 6)
- **THEN** the first shows no row and the author as a removable selection with the count 0; every row shown on the term page carries the tag `cinnamate`; the link leads to `/procedures/` with the query, the status and the sort and without the tag; and Clear all keeps the scope and the sort

### Requirement: Details view
Each catalogue row's `Procedure` cell SHALL hold, after the title link, a `div.row-details` with:
- a `dl` with one `dt`/`dd` pair per field that is set, labelled as the metadata panel labels them: `Product` or `Products` (the shown names of the products, joined by `, `, as text; absent when there is one product whose shown name equals the title), `Formula` (each digit run in `<sub>`), `MW` (`<mw> g/mol`) and `CAS`, these three only for a procedure with one product, from its compound, then `Yield` (written as the key facts write it, site-theme "Procedure page structure") and `Created` (`<time datetime="<RFC 3339 date>">YYYY-MM-DD</time>`), numbers with the site language's decimal separator;
- when a product's compound sets `structure_image`, an `img.row-structure` for the first such product, whose `src` resolves to the published image, with `alt` `Structure of <name>`, `loading="lazy"` and `decoding="async"`; otherwise no image and no placeholder.

The screen stylesheet hides `div.row-details` unless the catalogue carries `data-view="details"`. The Details view uses the same rows, order and controls as the table.

#### Scenario: Details markup
- **WHEN** a test scans `public/procedures/index.html` of a theme build that adds the catalogue fixtures to the test collection
- **THEN** each row's `div.row-details` has exactly the pairs that its content file and the registry give, in the stated order, OSDB-0003's row has the image with its `alt` and lazy loading, no other row has an `img`, and the fixture whose compound has no CAS number has no `CAS` pair

#### Scenario: Details in a browser
- **WHEN** the orchestrator switches `/procedures/` to Details, sorts it, filters it and opens it at 500 CSS pixels in both colour schemes (manual verification, tasks.md section 6)
- **THEN** the same IDs are listed in the same order as in the table view, the image is shown only for OSDB-0003, no cell shows a broken image or an empty link, and the text stays readable

### Requirement: Compound catalogue
The page `/compounds/` SHALL be the compound catalogue: a catalogue of every compound of the registry whose facets are the fields its collection declares with `facet = true` (compound-fields "Field declarations"). Its `main` holds one `div.catalogue` carrying `data-catalogue`, `data-search="text"`, `data-text-empty` `No compounds match the search and filters.`, and `data-text-ignored` and `data-text-remove` with the procedure catalogue's texts. It holds, in this order:
1. `div.list-head`, holding the `h1` `Compounds` and `p.catalogue-count`, which carries `role="status"`, `data-catalogue-count` and `data-filtered="{shown} of {total} compounds"`, and whose text is `<n> compounds`, or `1 compound`, where `n` is the number of table rows.
2. A `noscript` element holding `p.catalogue-noscript`, whose text is `Search and filters need JavaScript. Without it, this page lists every compound.`
3. `div.catalogue-layout`, holding, when the collection declares a facet field, `div.catalogue-facets`, and then `div.catalogue-results`.

The parts are these:
- **Facets.** `div.catalogue-facets` carries `id="catalogue-facets"`, `data-catalogue-controls` and `hidden`, and holds an `h2` `Filters`, then one `details.facet` per facet field, in declared order, carrying `open` and `data-facet` with the field's key. Its `summary` carries an `id` and the field's shown label, and is followed by a `div` with `role="group"` and `aria-labelledby` naming that `id`, which holds one `label.facet-value` per value: an `input` with `type="checkbox"`, `name` the field's key and `value` the machine value, then `span.facet-label` with the value's display label, then an empty `span.facet-count`.
- **Facet values.** A `boolean` field lists `true` and `false`, in that order, each only when some compound sets it, with the display labels `Yes` and `No`. A `choice` field lists, in the field data's `order` (compound-fields "Field data for the site"), each value that some compound sets or that is an ancestor of a value some compound sets, with its shown label as the display label; its `label.facet-value` carries `style="--depth: <n>"`, where `n` is the number of the value's ancestors, and the screen stylesheet indents it by `n` steps.
- **Results.** `div.catalogue-results` holds `div.catalogue-toolbar`, with `data-catalogue-controls` and `hidden`, holding, when the page has facets, `button.facets-toggle` as the procedure catalogue's, then an empty `ul.catalogue-active` and `button.clear-all` `Clear all`; then `p.catalogue-message`, as the procedure catalogue's; then the compound table (site-theme "Compound directory"). The page has no sort select and no view select.
- **Rows.** Each body row of the table carries `data-id`, the compound's key; `data-title`, its shown name; `data-text`, its `name`, its `name_de` when set, its `formula`, its CAS number when set, its SMILES and its value of each `text` field declared with `search = true` that it sets, joined by single spaces; and, for each facet field, `data-<key>`, a JSON array of machine values: for a `boolean` field `"true"` or `"false"`, for a `choice` field each value the compound sets and each ancestor of one, each once; an unset field gives `[]`.
- **Search.** The site header's form (site-theme "Page shell") carries `data-catalogue-search`, its `action` resolves to `/compounds/`, and its input carries `id="catalogue-q"`, the `aria-label` `Search compounds` and the placeholder `Name, formula, CAS or SMILES`.

The catalogue script makes the page interactive as the requirement "Catalogue in a browser" states: a value selects the compounds whose row carries it, so that a value of a vocabulary also selects the compounds filed under a value below it; the facets combine as the procedure catalogue's do; the search matches the rows' text through `match`; the rows keep their order by shown name. Its address holds the query and one parameter per selected value, named by the field's key, such as `/compounds/?q=ester&chemical_class=esters&in_house=true`. These texts are those of an English site; a German site has the German texts that the localization spec gives.

#### Scenario: The compound catalogue in the HTML
- **WHEN** a test scans `public/compounds/index.html` after a theme build in locale `en`
- **THEN** it has the stated elements, attributes and texts, its count reads `20 compounds`, its facets are `chemical_class` and `in_house`, in this order, labelled `Chemical class` and `Made in house`, and their values, labels, order and depths are those computed from the test collection's registry and field data
- **AND** every row's `data-id`, `data-title`, `data-text`, `data-chemical_class` and `data-in_house` equal the values computed from the registry and the field data, the `data-chemical_class` of `4-bromoacetophenone` holding exactly `aryl-ketones`, `ketones`, `carbonyl-compounds` and `aryl-halides`
- **AND** the header's form has the stated `action`, `id`, `aria-label` and placeholder

#### Scenario: A value set beside its ancestor
- **WHEN** a test builds a copy of the test collection in locale `en` after setting `chemical_class = ["carbonyl-compounds", "ketones"]` in `compounds/acetone.toml`, and scans `public/compounds/index.html`
- **THEN** the `data-chemical_class` of the acetone row holds exactly `carbonyl-compounds` and `ketones`, each once

#### Scenario: A collection without facet fields
- **WHEN** a test builds a copy of the test collection in locale `en` after removing every `facet = true` line from its `orgsyndb.toml`, and scans `public/compounds/index.html`
- **THEN** the catalogue has no `div.catalogue-facets` and no `button.facets-toggle`, and still has the count, the chips list, `Clear all`, the message, the table and the header's compound search

#### Scenario: Filtering and searching compounds
- **WHEN** the orchestrator opens `/compounds/` of the German demo build from `tools/orgsyndb serve`, ticks `Carbonylverbindungen`, then `Ja` under `Eigene Herstellung`, types `ester`, reloads, removes the chip of `Carbonylverbindungen`, goes Back, and opens `/compounds/?chemical_class=nope&sort=title` (manual verification, tasks.md section 3)
- **THEN** the rows narrow to the compounds filed under a carbonyl class, then to those made in house, then to those whose text contains `ester`, with the count, the facet counts, the chips and the address following each step; the reload keeps the address `/compounds/?q=ester&chemical_class=carbonyl-compounds&in_house=true`, removing the chip leaves `/compounds/?q=ester&in_house=true`, and Back restores the first address with its rows, counts and chips; and the last shows every compound, the ignored-parameters notice naming both parameters, and the address `/compounds/`

### Requirement: Compound text search
`OrgSynCatalogue.match(records, q)` SHALL return the IDs of the records whose `text` contains every word of `OrgSynSearch.normaliseTerm(q)`, in the order of `records`, each once. A word is contained in a text when it is a substring of the text normalised by `normaliseTerm`, both compared in lower case. When the normalised query is empty it returns `[]`.

#### Scenario: Substrings of names, numbers and SMILES
- **WHEN** a Node test calls `match` on records whose texts are those of `acetylsalicylic-acid`, `salicylic-acid`, `acetone` and `ethyl-cinnamate` in the test collection, in this order, with the queries `salicyl`, `ACID acetyl`, `50-78-2`, `c1ccccc1C(=O)O`, `c1ccccc1O`, `zimt`, `ASA` and `--`
- **THEN** it returns `acetylsalicylic-acid` and `salicylic-acid` for the first; `acetylsalicylic-acid` for the second, third, fourth and seventh, the seventh through its searchable short name; `salicylic-acid` for the fifth; `ethyl-cinnamate` for the sixth, through its German name; and `[]` for the last

