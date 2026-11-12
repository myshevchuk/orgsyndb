## MODIFIED Requirements

### Requirement: Catalogue rows
Each body row of a catalogue table SHALL carry these attributes, which are the catalogue's records:
- `data-id`: the procedure's `id`;
- `data-title`: its `title`;
- `data-status`: its `status`;
- `data-kind`: `general` for a general procedure and `specific` otherwise (general-procedures "Scope entries");
- `data-type`, `data-tag` and `data-author`: JSON arrays of the term keys of its reaction types, tags and authors, in front-matter order;
- `data-created` and `data-modified`: its `date` and `lastmod`, formatted `2006-01-02T15:04:05Z07:00`;
- for each procedure field declared with `facet = true` (procedure-fields "Procedure field declarations"), `data-<key>`: a JSON array of machine values, as a compound catalogue row gives them (requirement "Compound catalogue"): for a `boolean` field `"true"` or `"false"`, for a `choice` field each value the procedure sets and each ancestor of one, each once; an unset field gives `[]`.

A term key is the key of the term in Hugo's taxonomy (`site.Taxonomies.<plural>`), which is the term as written, lowercased: `hydrolysis`, `sample-data`, and for an author its user name, such as `a.example` (procedure-authors "Author data for the site"). A reaction type's key is its vocabulary slug. The facets' machine values are these keys, the status literals `draft`, `checked` and `retired`, the kind literals `specific` and `general`, and the values of the declared facets.

#### Scenario: Rows carry the records
- **WHEN** a test scans `public/procedures/index.html` of a theme build that adds the catalogue fixtures to the test collection
- **THEN** every row's attributes equal the values computed from its published content file, each term key is the term as written, lowercased, and the author `ae.mueller`, named `Ä. Müller`, has the key `ae.mueller`

#### Scenario: Rows carry the declared facets
- **WHEN** a test scans `public/procedures/index.html` after a theme build in locale `en`
- **THEN** every row's `data-project` and `data-inert_atmosphere` equal the values computed from its published content file and the field data of the test collection's `orgsyndb.toml`, and the row of a procedure that sets `project = "first-year-practical"` has the `data-project` `["first-year-practical", "teaching"]` in some order

### Requirement: Fixed scope on term pages
A term page's catalogue SHALL treat its term as a fixed scope, applied with every user choice, and the catalogue of `/general-procedures/` SHALL treat the `kind` value `general` so, with the scope text that general-procedures "General procedures view" gives:
- **Static label.** `p.catalogue-scope` reads `Only procedures of the reaction type <label>`, `Only procedures with the tag <tag>` or `Only procedures by <author>`, then ` · ` and an `a` with `data-browse-all`, the text `Browse all procedures` and the `href` `/procedures/`. It holds no other link.
- **Fixed facet.** The page's facet is a `details.facet` carrying `data-fixed` and `open`, whose only value is the term, its checkbox `checked` and `disabled`. The other facets list their values as on `/procedures/`; a value that no row of the page carries counts 0, so the script shows it only while it is selected.
- **Results.** The records are the page's rows, so no search result or filter shows a procedure outside the scope; `Clear all` keeps the scope.
- **Browse all.** The script sets the `data-browse-all` link to its original URL followed by `serialize` of the current state, which never holds a value of the fixed facet. Without JavaScript it leads to `/procedures/`.

#### Scenario: Scope in the HTML
- **WHEN** a test scans `public/tags/cinnamate/index.html`, `public/reaction_types/hydrolysis/index.html` and `public/authors/klehmann/index.html` after a theme build in locale `en`
- **THEN** each has the scope text and the `Browse all procedures` link to `/procedures/` as the scope line's only link, and the fixed facet with one checked, disabled value, while its other facets list the same values as those of `/procedures/`

#### Scenario: Searching inside a scope
- **WHEN** the orchestrator opens `/tags/cinnamate/?author=a.example`, then `/tags/cinnamate/`, chooses a sort, searches `acid`, ticks a status, follows Browse all procedures, goes Back and presses Clear all (manual verification, tasks.md section 6)
- **THEN** the first shows no row and the author as a removable selection with the count 0; every row shown on the term page carries the tag `cinnamate`; the link leads to `/procedures/` with the query, the status and the sort and without the tag; and Clear all keeps the scope and the sort
