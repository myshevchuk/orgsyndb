## MODIFIED Requirements

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

### Requirement: Catalogue controls
Each catalogue SHALL carry its controls in the published HTML. Its search form is the site header's; the others lie inside elements that carry `data-catalogue-controls` and `hidden`:
- **Search.** The header's `form.site-search` (site-theme "Page shell") carries `data-catalogue-search`, and its `action` resolves to the page's own URL. Its `input` carries `id="catalogue-q"`. On `/procedures/` the input's `aria-label` is `Search procedures` and its placeholder `Product, CAS, SMILES or keyword`. On a term page both are `Search procedures of the reaction type <label>`, `Search procedures with the tag <tag>` or `Search procedures by <author>`. The form is shown without JavaScript; submitting it then reloads the page with `q`, which the static list does not apply.
- **Facets.** `div.catalogue-facets`, with `id="catalogue-facets"`, `data-catalogue-controls` and `hidden`, holds an `h2` `Filters`, then one `details.facet` per facet in the order `type`, `status`, `tag`, `author`, each carrying `data-facet` with the facet's name. A facet's `summary` carries an `id` and the text `Reaction type`, `Status`, `Tag` or `Author`, and is followed by a `div` with `role="group"` and `aria-labelledby` naming that `id`, which holds one `label.facet-value` per value. Each holds an `input` with `type="checkbox"`, `name` the facet's name and `value` the machine value, then `span.facet-label` with the value's display label, then an empty `span.facet-count`. The `type` and `status` facets carry `open`. After the group, the `type`, `tag` and `author` facets each link their directory: `All reaction types` to `/reaction_types/`, `All tags` to `/tags/` and `All authors` to `/authors/`.
- **Facet values.** The `status` facet lists `draft`, `checked` and `retired`, in that order. The other facets, apart from a term page's fixed facet, list each value that some published procedure carries, on every catalogue page, ordered by display label. The display label is the vocabulary label for a reaction type, the tag itself, the author's name as written, and the status in the site's language.
- **Toolbar.** `div.catalogue-toolbar`, with `data-catalogue-controls` and `hidden`, holds, in order: `button.facets-toggle` with `type="button"`, `aria-controls="catalogue-facets"`, `aria-expanded="false"` and the text `Filters`; an empty `ul.catalogue-active`; `button.clear-all` with `type="button"` and the text `Clear all`; a `label` `Sort by` for `select#catalogue-sort`, whose options have the values and texts `relevance` `Relevance`, `id` `ID`, `title` `Title (A–Z)`, `created` `Created (newest first)` and `modified` `Modified (newest first)`; and a `label` `View` for `select#catalogue-view`, whose options are `table` `Table` and `details` `Details`.
- **Message.** `p.catalogue-message` carries `data-catalogue-message`, `role="status"` and `hidden`, and is empty.
- **Texts for the script.** `div.catalogue` carries the texts the script shows: `data-text-searching` `Searching…`, `data-text-unavailable` `Search unavailable`, `data-text-error` `The search index could not be loaded, so the search was not applied.`, `data-text-error-action` `Show the list without the search`, `data-text-empty` `No procedures match the search and filters.`, `data-text-ignored` `Ignored in the address: {list}` and `data-text-remove` `Remove {facet}: {value}`.

#### Scenario: Controls in the HTML
- **WHEN** a test scans `public/procedures/index.html` after a theme build in locale `en`
- **THEN** its header has the search form with the stated attributes and texts, and `div.catalogue` holds no form and has the facets, the toolbar and the message with the stated elements, attributes and texts, each container carrying `hidden`
- **AND** the header search of `public/tags/cinnamate/index.html` has the `action` `/tags/cinnamate/` and the `aria-label` and placeholder `Search procedures with the tag cinnamate`
- **AND** the `type`, `tag` and `author` facets list exactly the term keys in use in the collection, ordered by label, and the `status` facet lists the three literals in order
