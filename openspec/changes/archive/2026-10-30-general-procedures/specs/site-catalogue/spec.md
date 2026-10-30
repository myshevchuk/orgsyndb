## MODIFIED Requirements

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

### Requirement: Catalogue address
`OrgSynCatalogue.parse(search, known, fixed)` SHALL read the query string `search`, with or without its leading `?`, as `URLSearchParams` does. `known` maps each facet name to the machine values the page knows, in the order the page lists them; `fixed` is the term page's facet or `null`. It returns the state and `ignored`, the list of `[name, value]` pairs it did not apply, in their order in `search`:
- **`q`.** The first `q` value, without leading or trailing whitespace, is the query; absent, it is `""`. Every later `q` is ignored.
- **Facets.** A `type`, `kind`, `status`, `tag` or `author` value is selected when it is one of `known` for that facet and the facet is not `fixed`; a value given twice is selected once and not reported. Every other value of these names, including an empty one and every value of the fixed facet, is ignored. Each facet's selected values are listed in `known` order.
- **`sort`.** The first `sort` value is the sort when it is `id`, `title`, `created` or `modified`, or `relevance` while the query is active; otherwise it is ignored and the sort is `null`. Every later `sort` is ignored.
- **`view`.** The first `view` value is the view when it is `table` or `details`; otherwise it is ignored. Every later `view` is ignored. Without one the view is `table`.
- **Other names.** Every parameter with another name is ignored.

`serialize(state)` returns `""` for the default state, and otherwise `?` followed by, in order: `q`, without leading or trailing whitespace, when that is non-empty; one `type`, `kind`, `status`, `tag` and `author` per selected value, in the state's order; `sort` when it is not `null`; and `view=details` when the view is `details`. Values are encoded as `URLSearchParams` encodes them. For every state `s` whose selections are known and listed in `known` order, and whose sort `parse` would keep, `serialize(parse(serialize(s), known, null).state)` equals `serialize(s)`.

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

### Requirement: Catalogue script
The catalogue, the term pages and `/general-procedures/` SHALL load one script, `/js/catalogue.<hash>.js`, with `defer`. It is built with Hugo Pipes by concatenating `site/assets/js/search-terms.js`, `catalogue-core.js` and `catalogue.js`, minified and fingerprinted. No other page loads it, and no page loads `pagefind-ui.js` or `pagefind-ui.css`. The script imports the Pagefind bundle only while the query is active, from `pagefind/pagefind.js` beside the directory of its own script URL (the URL `../pagefind/pagefind.js` resolved against it), so that the bundle loads under any path prefix.

#### Scenario: Script wiring
- **WHEN** a test scans every HTML page after a theme build
- **THEN** exactly the catalogue, the term pages and `/general-procedures/` load `/js/catalogue.<hash>.js`, which contains `OrgSynSearch`, `OrgSynCatalogue` and `pagefind/pagefind.js`, and no page references `pagefind-ui`

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
