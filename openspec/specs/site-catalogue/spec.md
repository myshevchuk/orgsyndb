# site-catalogue Specification

## Purpose
Define the procedure catalogue at `/procedures/` and on the term pages: its pages and row records, its controls, the state it keeps in the address, facet matching and counts, sort orders, the Details view, the fixed scope of a term page, its behaviour in a browser and the functions of its core script.
## Requirements
### Requirement: Catalogue pages
The site SHALL publish the catalogue at `/procedures/`, from `site/layouts/section.html`, and on every reaction-type, tag and author term page, from `site/layouts/term.html`. On each of these pages `main` holds one `div.catalogue` carrying `data-catalogue`, and on a term page also `data-fixed` naming the page's facet (`type`, `tag` or `author`). It holds, in this order:
1. `div.list-head`, holding the `h1` and `p.catalogue-count`. The `h1` is `Procedures` on `/procedures/` and the term's display title on a term page. `p.catalogue-count` carries `role="status"`, `data-catalogue-count` and `data-filtered="{shown} of {total} procedures"`, and its text is `<n> procedures`, or `1 procedure`, where `n` is the number of table rows.
2. On a term page only, `p.catalogue-scope`, as the requirement "Fixed scope on term pages" states.
3. A `noscript` element holding `p.catalogue-noscript`, whose text is `Search, filters and sorting need JavaScript. Without it, this page lists its procedures by ID. Browse them by reaction type, tag or author.`, where `reaction type`, `tag` and `author` link to `/reaction_types/`, `/tags/` and `/authors/`.
4. `div.catalogue-layout`, holding `div.catalogue-facets` and then `div.catalogue-results`. The results hold `div.catalogue-toolbar`, then `p.catalogue-message`, then the procedure table.

The procedure table is rendered by `site/layouts/_partials/procedure-table.html`: a `table.procedure-list`, the only child of a `div.table-scroll` with `tabindex="0"`, `role="region"` and `aria-label="Procedures"`. Its column headers are `ID`, `Procedure`, `Reaction type`, `Status` and `Modified`, each a `th` with `scope="col"`. It has one body row per procedure in scope, by `id` ascending: on `/procedures/` every published procedure, on a term page exactly the published procedures that carry the term. In each row:
- the `ID` cell links the procedure page with the ID as text;
- the `Procedure` cell links it with the title as text;
- the `Reaction type` cell holds the vocabulary labels of its reaction types, joined by `, `;
- the `Status` cell holds `span.badge.badge--<status>` with the status;
- the `Modified` cell holds `<time datetime="<RFC 3339 lastmod>">YYYY-MM-DD</time>`.

Each of these pages loads the catalogue script. Its one `input` with `name="q"` is the catalogue's search field, in the site header (requirement "Catalogue controls").

#### Scenario: The catalogue lists every procedure once
- **WHEN** a test scans `public/procedures/index.html` after a theme build in locale `en`
- **THEN** its `h1` is `Procedures`, `p.catalogue-count` reads `8 procedures` with the stated attributes, and the table has the five column headers and one row per published ID, each ID once, in ascending order
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
- `data-type`, `data-tag` and `data-author`: JSON arrays of the term keys of its reaction types, tags and authors, in front-matter order;
- `data-created` and `data-modified`: its `date` and `lastmod`, formatted `2006-01-02T15:04:05Z07:00`.

A term key is the key of the term in Hugo's taxonomy (`site.Taxonomies.<plural>`), which is the term as written, lowercased: `hydrolysis`, `sample-data`, `a. example` for the author `A. Example`, and `ä. müller` for `Ä. Müller`. A reaction type's key is its vocabulary slug. The facets' machine values are these keys and the status literals `draft`, `checked` and `retired`.

#### Scenario: Rows carry the records
- **WHEN** a test scans `public/procedures/index.html` of a theme build that adds the catalogue fixtures to the test collection
- **THEN** every row's attributes equal the values computed from its published content file, each term key is the term as written, lowercased, and the author `Ä. Müller` has the key `ä. müller`

### Requirement: Catalogue controls
Each catalogue SHALL carry its controls in the published HTML. Its search form is the site header's; the others lie inside elements that carry `data-catalogue-controls` and `hidden`:
- **Search.** The header's `form.site-search` (site-theme "Page shell") carries `data-catalogue-search`, and its `action` resolves to the page's own URL. Its `input` carries `id="catalogue-q"`. On `/procedures/` the input's `aria-label` is `Search procedures` and its placeholder `Product, CAS, SMILES or keyword`. On a term page the `aria-label` names the scope, `Search procedures of the reaction type <label>`, `Search procedures with the tag <tag>` or `Search procedures by <author>`, and the placeholder is `Search these procedures`, short enough to show whole whatever the term. The form is shown without JavaScript; submitting it then reloads the page with `q`, which the static list does not apply.
- **Facets.** `div.catalogue-facets`, with `id="catalogue-facets"`, `data-catalogue-controls` and `hidden`, holds an `h2` `Filters`, then one `details.facet` per facet in the order `type`, `status`, `tag`, `author`, each carrying `data-facet` with the facet's name. A facet's `summary` carries an `id` and the text `Reaction type`, `Status`, `Tag` or `Author`, and is followed by a `div` with `role="group"` and `aria-labelledby` naming that `id`, which holds one `label.facet-value` per value. Each holds an `input` with `type="checkbox"`, `name` the facet's name and `value` the machine value, then `span.facet-label` with the value's display label, then an empty `span.facet-count`. The `type` and `status` facets carry `open`. After the group, the `type`, `tag` and `author` facets each link their directory: `All reaction types` to `/reaction_types/`, `All tags` to `/tags/` and `All authors` to `/authors/`.
- **Facet values.** The `status` facet lists `draft`, `checked` and `retired`, in that order. The other facets, apart from a term page's fixed facet, list each value that some published procedure carries, on every catalogue page, ordered by display label. The display label is the vocabulary label for a reaction type, the tag itself, the author's name as written, and the status in the site's language.
- **Toolbar.** `div.catalogue-toolbar`, with `data-catalogue-controls` and `hidden`, holds, in order: `button.facets-toggle` with `type="button"`, `aria-controls="catalogue-facets"`, `aria-expanded="false"` and the text `Filters`; an empty `ul.catalogue-active`; `button.clear-all` with `type="button"` and the text `Clear all`; a `label` `Sort by` for `select#catalogue-sort`, whose options have the values and texts `relevance` `Relevance`, `id` `ID`, `title` `Title (A–Z)`, `created` `Created (newest first)` and `modified` `Modified (newest first)`; and a `label` `View` for `select#catalogue-view`, whose options are `table` `Table` and `details` `Details`.
- **Message.** `p.catalogue-message` carries `data-catalogue-message`, `role="status"` and `hidden`, and is empty.
- **Texts for the script.** `div.catalogue` carries the texts the script shows: `data-text-searching` `Searching…`, `data-text-unavailable` `Search unavailable`, `data-text-error` `The search index could not be loaded, so the search was not applied.`, `data-text-error-action` `Show the list without the search`, `data-text-empty` `No procedures match the search and filters.`, `data-text-ignored` `Ignored in the address: {list}` and `data-text-remove` `Remove {facet}: {value}`.

#### Scenario: Controls in the HTML
- **WHEN** a test scans `public/procedures/index.html` after a theme build in locale `en`
- **THEN** its header has the search form with the stated attributes and texts, and `div.catalogue` holds no form and has the facets, the toolbar and the message with the stated elements, attributes and texts, each container carrying `hidden`
- **AND** the header search of `public/tags/cinnamate/index.html` has the `action` `/tags/cinnamate/`, the `aria-label` `Search procedures with the tag cinnamate` and the placeholder `Search these procedures`
- **AND** the `type`, `tag` and `author` facets list exactly the term keys in use in the collection, ordered by label, and the `status` facet lists the three literals in order

### Requirement: Catalogue core functions
`site/assets/js/catalogue-core.js` SHALL be a classic script, with no `import`, `export` or use of `document`, `window` or `location`, that defines `globalThis.OrgSynCatalogue`. It needs `globalThis.OrgSynSearch` from `search-terms.js`, loaded before it. A state is an object `{q, type, status, tag, author, sort, view}`: `q` a string, the four facets arrays of machine values, `sort` `null` or one of `relevance`, `id`, `title`, `created` and `modified`, and `view` `table` or `details`. A record is an object `{id, title, created, modified, type, status, tag, author}`, with `created` and `modified` RFC 3339 strings and the four facets arrays. The functions are:
- `parse(search, known, fixed)`: the state and the ignored parameters of an address, as the requirement "Catalogue address" states. Returns `{state, ignored}`.
- `serialize(state)`: the canonical query string of a state.
- `active(state)`: whether `OrgSynSearch.normaliseTerm(state.q)` is non-empty.
- `sortOf(state)`: the sort in effect.
- `withQuery(state, q)`: a copy of `state` with the query `q`.
- `clear(state)`: the state that Clear all leaves.
- `select(records, state, matched, language)`: the displayed IDs and the facet counts. Returns `{ids, counts}`.
- `searcher(pagefind)`: the catalogue's text search, as the site-search spec states.

No function changes its arguments.

#### Scenario: A classic script without the DOM
- **WHEN** a Node test reads `site/assets/js/catalogue-core.js` and loads it with `search-terms.js` into a fresh context that defines no `document`, `window` or `location`
- **THEN** the file has no `import` or `export` statement, and `OrgSynCatalogue` has the eight functions

### Requirement: Catalogue address
`OrgSynCatalogue.parse(search, known, fixed)` SHALL read the query string `search`, with or without its leading `?`, as `URLSearchParams` does. `known` maps each facet name to the machine values the page knows, in the order the page lists them; `fixed` is the term page's facet or `null`. It returns the state and `ignored`, the list of `[name, value]` pairs it did not apply, in their order in `search`:
- **`q`.** The first `q` value, without leading or trailing whitespace, is the query; absent, it is `""`. Every later `q` is ignored.
- **Facets.** A `type`, `status`, `tag` or `author` value is selected when it is one of `known` for that facet and the facet is not `fixed`; a value given twice is selected once and not reported. Every other value of these names, including an empty one and every value of the fixed facet, is ignored. Each facet's selected values are listed in `known` order.
- **`sort`.** The first `sort` value is the sort when it is `id`, `title`, `created` or `modified`, or `relevance` while the query is active; otherwise it is ignored and the sort is `null`. Every later `sort` is ignored.
- **`view`.** The first `view` value is the view when it is `table` or `details`; otherwise it is ignored. Every later `view` is ignored. Without one the view is `table`.
- **Other names.** Every parameter with another name is ignored.

`serialize(state)` returns `""` for the default state, and otherwise `?` followed by, in order: `q`, without leading or trailing whitespace, when that is non-empty; one `type`, `status`, `tag` and `author` per selected value, in the state's order; `sort` when it is not `null`; and `view=details` when the view is `details`. Values are encoded as `URLSearchParams` encodes them. For every state `s` whose selections are known and listed in `known` order, and whose sort `parse` would keep, `serialize(parse(serialize(s), known, null).state)` equals `serialize(s)`.

#### Scenario: Reading an address
- **WHEN** a Node test calls `parse` with `known` holding `type` `hydrolysis` and `acylation`, `status` the three literals, `tag` `sample-data` and `cinnamate`, `author` `a. example` and `ä. müller`, and `fixed` `null`, on `?q=+acid+&type=acylation&type=hydrolysis&type=acylation&tag=nope&tag=&sort=title&view=details&page=2&q=x`
- **THEN** the state is `q` `acid`, `type` `["hydrolysis", "acylation"]`, no other selection, `sort` `title` and `view` `details`, and `ignored` is `[["tag", "nope"], ["tag", ""], ["page", "2"], ["q", "x"]]`

#### Scenario: Sorts and views that do not apply
- **WHEN** the same test parses `?sort=relevance`, `?q=acid&sort=relevance`, `?q=---&sort=relevance`, `?sort=newest`, `?sort=id&sort=title`, `?view=grid` and `?view=table`
- **THEN** the sorts are `null`, `relevance`, `null`, `null`, `id`, `null` and `null`, every view is `table`, and `ignored` names `sort=relevance`, nothing, `sort=relevance`, `sort=newest`, `sort=title`, `view=grid` and nothing respectively

#### Scenario: The fixed facet is not read from the address
- **WHEN** the test parses `?tag=cinnamate&status=draft` with `fixed` `tag`
- **THEN** the state selects `status` `draft` and no tag, and `ignored` is `[["tag", "cinnamate"]]`

#### Scenario: Canonical addresses
- **WHEN** the test serializes the default state; a state with query ` acetic acid `, `status` `draft` and `checked`, `author` `ä. müller`, `sort` `modified` and view `details`; and parses each result again
- **THEN** the first is `""`, the second is `?q=acetic+acid&status=draft&status=checked&author=%C3%A4.+m%C3%BCller&sort=modified&view=details`, and serializing each parsed state gives the same string

### Requirement: Facet matching and counts
`OrgSynCatalogue.select(records, state, matched, language)` SHALL compute the displayed IDs and the facet counts. Records after the first with the same `id` are left out. `matched` is `null` when the query is not active, and otherwise the list of IDs that match the query, in relevance order. A record:
- matches the query when `matched` is `null` or holds its `id`;
- matches a facet when the state selects no value of that facet, or when the record carries at least one selected value of it;
- is displayed when it matches the query and every facet.

`ids` lists each displayed record's `id` once, in the order of the requirement "Sort orders". `counts` maps each facet to an object that holds every value some record carries or the state selects, and gives for a value `v` of facet `f` the number of records that match the query, carry `v` in `f`, and match every facet other than `f`.

#### Scenario: OR within a facet, AND across facets
- **WHEN** a Node test calls `select` on six records with `matched` `null`, selecting `type` `hydrolysis` and `acylation`; then also `status` `draft`; then only `status` `retired`
- **THEN** the first lists every record of either type, the second only those that are also `draft`, and the third exactly the retired ones

#### Scenario: Counts leave out the facet's own selections
- **WHEN** the same test selects `type` `hydrolysis` and `tag` `cinnamate`, with `matched` naming four of the records
- **THEN** each `type` count is the number of matched records with that type and the tag `cinnamate`, each `tag` count the number of matched records of type `hydrolysis` with that tag, each `status` and `author` count the number of displayed records with that value, and a selected value that no remaining record carries has the count 0

#### Scenario: Filters without a query and an empty result
- **WHEN** the test selects `author` `ä. müller` with `matched` `null`, and then sets `matched` to `[]`
- **THEN** the first lists exactly that author's records, and the second lists none and gives every count as 0

#### Scenario: Each procedure once
- **WHEN** the test passes a record list that repeats one `id` and a `matched` list that names it twice
- **THEN** `ids` holds that `id` once and every count counts it once

### Requirement: Sort orders
`OrgSynCatalogue.sortOf(state)` SHALL return the state's `sort` when it is not `null` and either is not `relevance` or the query is active; otherwise `relevance` while the query is active, and `id` when it is not. `withQuery(state, q)` returns the state with the query `q`, and with the sort `null` when the sort was `relevance` and the new query is not active. `clear(state)` returns the state with the query `""` and no selections, keeping the sort, unless it was `relevance`, and the view. `select` orders the displayed records by the sort in effect:
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

### Requirement: Catalogue script
The catalogue and term pages SHALL load one script, `/js/catalogue.<hash>.js`, with `defer`. It is built with Hugo Pipes by concatenating `site/assets/js/search-terms.js`, `catalogue-core.js` and `catalogue.js`, minified and fingerprinted. No other page loads it, and no page loads `pagefind-ui.js` or `pagefind-ui.css`. The script imports the Pagefind bundle only while the query is active, from `pagefind/pagefind.js` beside the directory of its own script URL (the URL `../pagefind/pagefind.js` resolved against it), so that the bundle loads under any path prefix.

#### Scenario: Script wiring
- **WHEN** a test scans every HTML page after a theme build
- **THEN** exactly the catalogue and term pages load `/js/catalogue.<hash>.js`, which contains `OrgSynSearch`, `OrgSynCatalogue` and `pagefind/pagefind.js`, and no page references `pagefind-ui`

### Requirement: Catalogue in a browser
With JavaScript, the catalogue script SHALL make the catalogue interactive, as follows:
- **Start.** It removes `hidden` from every element with `data-catalogue-controls`. Its records are the table rows; its known values are the values of the facet checkboxes outside the fixed facet; its fixed facet is the catalogue's `data-fixed`. It reads the state with `parse` from the page's address. When values were ignored, it shows the `data-text-ignored` text in `p.catalogue-message`, `{list}` replaced by the ignored pairs written `name=value` and joined by `, `. When the canonical address `serialize` gives differs from the page's, it replaces the history entry with it.
- **Controls follow the state.** The search field is set to the query when the state comes from the address, from `Clear all` or from the error button, and typing never rewrites it; each checkbox outside the fixed facet is checked when its value is selected, and the fixed facet's checkbox stays checked, disabled and shown; the sort select shows `sortOf`, and offers `Relevance` only while the query is active; the view select shows the view, and the catalogue carries `data-view` with it. `ul.catalogue-active` holds one `li` per selected value, in facet order and then the state's order, holding a `button` whose text is `<facet name>: <display label>` and whose `aria-label` is the `data-text-remove` text with `{facet}` and `{value}` replaced. `Clear all` is shown only while the query is non-empty or a value is selected. A `tag` or `author` facet with a selected value is open.
- **Results.** Without an active query the records are selected with `matched` `null`. With one, the matching IDs come from the searcher, one search per distinct normalised query in a page view. While a search is pending, `div.catalogue-results` carries `aria-busy="true"` and the count reads the `data-text-searching` text. Each change of state starts a new render, and a search result is used only by the latest render. The displayed rows are shown in order and every other row is hidden. Each `span.facet-count` holds its value's count; outside the fixed facet, an unselected value whose count is 0 is hidden, and a selected one is shown whatever its count. The fixed facet's count is the number of displayed rows.
- **Count and messages.** While the query is non-empty or a value is selected, `p.catalogue-count` reads its `data-filtered` text with `{shown}` and `{total}` replaced by the number of displayed rows and of all rows; otherwise it reads its original text. Numbers are written with `Intl.NumberFormat` of the page's language. When no row is displayed, `p.catalogue-message` shows the `data-text-empty` text.
- **Index errors.** When the bundle cannot be imported or a search fails while the query is active, no row is shown, the facet counts are hidden, the count reads the `data-text-unavailable` text, and `p.catalogue-message` shows the `data-text-error` text followed by a `button` with the `data-text-error-action` text, which removes the query.
- **Changes and history.** Typing in the search field changes the query 250 ms after the last keystroke, through `withQuery`. The first such change of a run of edits pushes a history entry and later ones replace it; the run ends when the field loses focus, when the form is submitted, or with any other change. Submitting the form applies the field at once and loads no page. Each checkbox change, chip, `Clear all` (through `clear`), sort change, view change and the error button pushes one history entry. A change that leaves the address unchanged adds no entry. Back and Forward restore the state of the address they reach, with its controls, results, counts and order.
- **Focus.** Removing a selection with its chip moves focus to the next chip, else the previous one, else the search field. `Clear all` and the error button move focus to the search field. No other change moves focus.
- **Narrow windows.** Below 55rem the facets are hidden until `button.facets-toggle` opens them; the button's `aria-expanded` follows. At 55rem and wider the facets are always shown and the button is not.

#### Scenario: Searching and filtering together
- **WHEN** the orchestrator opens `/procedures/` from `tools/orgsyndb serve`, types `cinnamate`, then ticks the status `draft` and a tag (manual verification, tasks.md section 6)
- **THEN** the rows narrow to the matches of the query and the filters, the count reads `<shown> of <total> procedures`, every facet count follows the stated rule, the chips list the selections, and the sort select offers and shows `Relevance`
- **AND** the page text contains no part of a SMILES index

#### Scenario: The address restores the catalogue
- **WHEN** the orchestrator opens `/procedures/?q=acid&type=hydrolysis&sort=title&view=details` directly, reloads it, changes the sort and a facet, types a word letter by letter into the cleared search field with pauses longer than 250 ms, moves focus away, then goes Back three times and Forward once (manual verification, tasks.md section 6)
- **THEN** each page shown has the controls, rows, counts and order of its address, and the typed word added exactly one history entry
- **AND** opening `/procedures/?type=nope&tag=` shows the ignored-parameters notice, lists every procedure, and leaves the address `/procedures/`

#### Scenario: A slow search does not overwrite a newer state
- **WHEN** a browser check delays the first Pagefind search and changes the query before it resolves (manual verification, tasks.md section 6)
- **THEN** the rows and counts shown are those of the later query

#### Scenario: Keyboard use
- **WHEN** the orchestrator uses only the keyboard on `/procedures/` (manual verification, tasks.md section 6)
- **THEN** Tab reaches the search field, the facets' summaries and checkboxes, the chips, Clear all, both selects and the table links, each shows a focus outline, Space toggles a checkbox and opens a summary, and focus moves only as the requirement states

#### Scenario: Index error
- **WHEN** the orchestrator removes `pagefind/pagefind.js` from a served copy of the build and searches (manual verification, tasks.md section 6)
- **THEN** the catalogue shows no rows, the error text and its button, and the button returns to the full list with the filters kept

### Requirement: Fixed scope on term pages
A term page's catalogue SHALL treat its term as a fixed scope, applied with every user choice:
- **Static label.** `p.catalogue-scope` reads `Only procedures of the reaction type <label>`, `Only procedures with the tag <tag>` or `Only procedures by <author>`, then ` · `, an `a` with `data-browse-all`, the text `Browse all procedures` and the `href` `/procedures/`, then ` · ` and the directory link `All reaction types`, `All tags` or `All authors`.
- **Fixed facet.** The page's facet is a `details.facet` carrying `data-fixed` and `open`, whose only value is the term, its checkbox `checked` and `disabled`. The other three facets list their values as on `/procedures/`; a value that no row of the page carries counts 0, so the script shows it only while it is selected.
- **Results.** The records are the page's rows, so no search result or filter shows a procedure outside the scope; `Clear all` keeps the scope.
- **Browse all.** The script sets the `data-browse-all` link to its original URL followed by `serialize` of the current state, which never holds a value of the fixed facet. Without JavaScript it leads to `/procedures/`.

#### Scenario: Scope in the HTML
- **WHEN** a test scans `public/tags/cinnamate/index.html`, `public/reaction_types/hydrolysis/index.html` and `public/authors/a.-example/index.html` after a theme build in locale `en`
- **THEN** each has the scope text, the `Browse all procedures` link to `/procedures/`, the directory link, and the fixed facet with one checked, disabled value, while its other facets list the same values as those of `/procedures/`

#### Scenario: Searching inside a scope
- **WHEN** the orchestrator opens `/tags/cinnamate/?author=a.+example`, then `/tags/cinnamate/`, chooses a sort, searches `acid`, ticks a status, follows Browse all procedures, goes Back and presses Clear all (manual verification, tasks.md section 6)
- **THEN** the first shows no row and the author as a removable selection with the count 0; every row shown on the term page carries the tag `cinnamate`; the link leads to `/procedures/` with the query, the status and the sort and without the tag; and Clear all keeps the scope and the sort

### Requirement: Details view
Each catalogue row's `Procedure` cell SHALL hold, after the title link, a `div.row-details` with:
- a `dl` with one `dt`/`dd` pair per field that is set, labelled as the metadata panel labels them: `Product` (`product.name`, only when it differs from the title), `Formula` (each digit run in `<sub>`), `MW` (`<mw> g/mol`), `CAS`, `Yield` (`<n> %`) and `Created` (`<time datetime="<RFC 3339 date>">YYYY-MM-DD</time>`), numbers with the site language's decimal separator;
- when the procedure sets `structure_image`, an `img.row-structure` whose `src` resolves to the published image, with `alt` `Structure of <product name>`, `loading="lazy"` and `decoding="async"`; otherwise no image and no placeholder.

The screen stylesheet hides `div.row-details` unless the catalogue carries `data-view="details"`. The Details view uses the same rows, order and controls as the table.

#### Scenario: Details markup
- **WHEN** a test scans `public/procedures/index.html` of a theme build that adds the catalogue fixtures to the test collection
- **THEN** each row's `div.row-details` has exactly the pairs of the fields its content file sets, in the stated order, OSDB-0003's row has the image with its `alt` and lazy loading, no other row has an `img`, and the fixture without a CAS number has no `CAS` pair

#### Scenario: Details in a browser
- **WHEN** the orchestrator switches `/procedures/` to Details, sorts it, filters it and opens it at 500 CSS pixels in both colour schemes (manual verification, tasks.md section 6)
- **THEN** the same IDs are listed in the same order as in the table view, the image is shown only for OSDB-0003, no cell shows a broken image or an empty link, and the text stays readable

