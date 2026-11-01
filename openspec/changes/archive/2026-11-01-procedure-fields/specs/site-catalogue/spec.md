## MODIFIED Requirements

### Requirement: Catalogue core functions
`site/assets/js/catalogue-core.js` SHALL be a classic script, with no `import`, `export` or use of `document`, `window` or `location`, that defines `globalThis.OrgSynCatalogue`. It needs `globalThis.OrgSynSearch` from `search-terms.js`, loaded before it. A catalogue names its own facets: the procedure catalogues `type`, `kind`, `status`, the procedure fields declared with `facet = true` (requirement "Catalogue controls"), `tag` and `author`, and the compound catalogue its facet fields (requirement "Compound catalogue"). A state is an object holding `q`, a string; `sort`, `null` or one of `relevance`, `id`, `title`, `created` and `modified`; `view`, `table` or `details`; and one key per facet of its catalogue, an array of machine values. The facets of a state are its keys other than `q`, `sort` and `view`, in the state's key order. A record is an object holding `id`; `title`; `created` and `modified`, RFC 3339 strings, on a procedure catalogue; `text`, the text the compound catalogue searches; and, for each facet, an array of machine values or a single one, a missing key holding no value. The functions are:
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

### Requirement: Catalogue controls
Each catalogue SHALL carry its controls in the published HTML. Its search form is the site header's; the others lie inside elements that carry `data-catalogue-controls` and `hidden`:
- **Search.** The header's `form.site-search` (site-theme "Page shell") carries `data-catalogue-search`, and its `action` resolves to the page's own URL. Its `input` carries `id="catalogue-q"`. On `/procedures/` the input's `aria-label` is `Search procedures` and its placeholder `Product, CAS, SMILES or keyword`. On a term page the `aria-label` names the scope, `Search procedures of the reaction type <label>`, `Search procedures with the tag <tag>` or `Search procedures by <author>`, and the placeholder is `Search these procedures`, short enough to show whole whatever the term. On `/general-procedures/` the `aria-label` is `Search general procedures` with the same placeholder. The form is shown without JavaScript; submitting it then reloads the page with `q`, which the static list does not apply.
- **Facets.** `div.catalogue-facets`, with `id="catalogue-facets"`, `data-catalogue-controls` and `hidden`, holds an `h2` `Filters`, then one `details.facet` per facet in the order `type`, `kind`, `status`, then each procedure field declared with `facet = true` (procedure-fields "Procedure field declarations"), in declared order, then `tag` and `author`, each carrying `data-facet` with the facet's name, which for a declared field is its key. A facet's `summary` carries an `id` and the text `Reaction type`, `Kind`, `Status`, the declared field's shown label, `Tag` or `Author`, and is followed by a `div` with `role="group"` and `aria-labelledby` naming that `id`, which holds one `label.facet-value` per value. Each holds an `input` with `type="checkbox"`, `name` the facet's name and `value` the machine value, then `span.facet-label` with the value's display label, then an empty `span.facet-count`. The `type`, `kind` and `status` facets and the declared facets carry `open`. After the group, the `type`, `tag` and `author` facets each link their directory: `All reaction types` to `/reaction_types/`, `All tags` to `/tags/` and `All authors` to `/authors/`.
- **Facet values.** The `status` facet lists `draft`, `checked` and `retired`, in that order, and the `kind` facet `specific` and `general`, in that order, with the display labels `Specific procedure` and `General procedure`. The other facets, apart from a term page's fixed facet, list each value that some published procedure carries, on every catalogue page, ordered by display label. The display label is the vocabulary label for a reaction type, the tag itself, the author's name as written, and the status and kind in the site's language. A declared facet lists, on every catalogue page, the values that the compound catalogue's facet of the same type lists (requirement "Compound catalogue"), with the same display labels and depths, as some published procedure carries them: for a `boolean` field `true` and `false`, in that order, each only when some published procedure sets it; for a `choice` field, in the field data's `order`, each value that some published procedure sets or that is an ancestor of such a value, its `label.facet-value` carrying `style="--depth: <n>"`, where `n` is the number of the value's ancestors.
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

### Requirement: Catalogue rows
Each body row of a catalogue table SHALL carry these attributes, which are the catalogue's records:
- `data-id`: the procedure's `id`;
- `data-title`: its `title`;
- `data-status`: its `status`;
- `data-kind`: `general` for a general procedure and `specific` otherwise (general-procedures "Scope entries");
- `data-type`, `data-tag` and `data-author`: JSON arrays of the term keys of its reaction types, tags and authors, in front-matter order;
- `data-created` and `data-modified`: its `date` and `lastmod`, formatted `2006-01-02T15:04:05Z07:00`;
- for each procedure field declared with `facet = true` (procedure-fields "Procedure field declarations"), `data-<key>`: a JSON array of machine values, as a compound catalogue row gives them (requirement "Compound catalogue"): for a `boolean` field `"true"` or `"false"`, for a `choice` field each value the procedure sets and each ancestor of one, each once; an unset field gives `[]`.

A term key is the key of the term in Hugo's taxonomy (`site.Taxonomies.<plural>`), which is the term as written, lowercased: `hydrolysis`, `sample-data`, `a. example` for the author `A. Example`, and `ä. müller` for `Ä. Müller`. A reaction type's key is its vocabulary slug. The facets' machine values are these keys, the status literals `draft`, `checked` and `retired`, the kind literals `specific` and `general`, and the values of the declared facets.

#### Scenario: Rows carry the records
- **WHEN** a test scans `public/procedures/index.html` of a theme build that adds the catalogue fixtures to the test collection
- **THEN** every row's attributes equal the values computed from its published content file, each term key is the term as written, lowercased, and the author `Ä. Müller` has the key `ä. müller`

#### Scenario: Rows carry the declared facets
- **WHEN** a test scans `public/procedures/index.html` after a theme build in locale `en`
- **THEN** every row's `data-project` and `data-inert_atmosphere` equal the values computed from its published content file and the field data of the test collection's `orgsyndb.toml`, and the row of a procedure that sets `project = "first-year-practical"` has the `data-project` `["first-year-practical", "teaching"]` in some order
