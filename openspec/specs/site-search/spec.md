# site-search Specification

## Purpose
Define the Pagefind search: what is indexed, the ID filter and sort key, the result metadata, SMILES substring search, query normalisation, and the catalogue's text search over the index.
## Requirements
### Requirement: Indexed content
The indexed element of a procedure page SHALL be its `article.procedure`, as the site-theme spec places it. The following are outside it, and are never part of the indexed text:
- the sample banner;
- the procedure header (ID line, status badge, `h1`, print facts, actions);
- the site header and its navigation;
- the footer.

The indexed text includes the metadata panel and the index-terms element. The panel shows neither the ID nor a product name that equals the title (site-theme "Metadata panel"), so `article.procedure` holds, after the rendered body and before the SMILES index element, a `span.index-terms` carrying `hidden`, whose text is the ID, a space and `product.name`, or the ID alone when the product has no name. It is never shown, and Pagefind indexes its text. Each of these therefore occurs as a separate word or words in the indexed body:
- the ID;
- the product name;
- the formula;
- the CAS number;
- the SMILES string;
- each tag;
- the reaction-type label;
- each author.

#### Scenario: Metadata inside the body, chrome outside
- **WHEN** a test scans every procedure page after a theme build
- **THEN** the text of its single `data-pagefind-body` element contains the ID, `product.name`, `product.cas` when set, `product.smiles`, every tag and every author
- **AND** it contains neither the banner text nor the navigation link texts as a sequence
- **AND** it has exactly one `span.index-terms`, carrying `hidden`, whose text is the ID and `product.name` separated by a space

#### Scenario: CAS numbers are separate words
- **WHEN** a search test searches `50-78-2`
- **THEN** the results are exactly `OSDB-0002`

### Requirement: Search filters
Each procedure page SHALL give Pagefind its ID as a filter and as a sort key. The element holding the ID in the procedure header, which carries `data-pagefind-meta="id"` (site-theme "Procedure page structure"), also carries `data-pagefind-filter="id"` and `data-pagefind-sort="id"`, and its whole text is the ID. No other element carries `data-pagefind-filter` or `data-pagefind-sort`.

#### Scenario: Filter attributes on every procedure page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** it has exactly one element with `data-pagefind-filter` and exactly one with `data-pagefind-sort`, the same element, whose attributes are both `id` and whose text equals the procedure's `id`
- **AND** no other page under `public/` carries either attribute

#### Scenario: The ID filter and sort key
- **WHEN** a search test reads the bundle's `filters()`, searches with a `null` term sorted by `id` ascending, and searches with a `null` term and the filter `id` set to each published ID in turn
- **THEN** the filter keys are exactly `id`, whose values are exactly the published IDs, each with the count 1
- **AND** the sorted search returns every procedure page, their `meta.id` values in ascending order, and each filtered search returns exactly that procedure

### Requirement: Result metadata
Each procedure page SHALL give Pagefind:
- the meta field `id`, from the element holding the ID in the header;
- the meta field `smiles_index`, from the SMILES index element.

Pagefind takes the result title from the page's `h1`. The catalogue shows no field of a Pagefind result: its rows are the static rows of the page (site-catalogue "Catalogue rows"), so neither an excerpt nor the SMILES index is ever displayed.

#### Scenario: Result data
- **WHEN** a search test searches `wintergreen`
- **THEN** the single result has `meta.id` `OSDB-0001` and `meta.title` `Salicylic acid`

### Requirement: SMILES substring index
Each procedure page SHALL end its `article.procedure` with a `span` element carrying `hidden`, `data-pagefind-meta="smiles_index[data-smiles-index]"` and a `data-smiles-index` attribute. Let `n` be `N(product.smiles)`. The attribute holds every suffix of `n`, from `n` itself down to its last character, separated by single spaces.

#### Scenario: Index value
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build
- **THEN** the `data-smiles-index` value is `ccooc1ccccc1coo cooc1ccccc1coo ooc1ccccc1coo oc1ccccc1coo c1ccccc1coo 1ccccc1coo ccccc1coo cccc1coo ccc1coo cc1coo c1coo 1coo coo oo o`

#### Scenario: Index on every procedure page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** each has exactly one such element, as the last element child of `article.procedure`, whose value is computed from that procedure's `product.smiles` as stated

### Requirement: Query normalisation
`site/assets/js/search-terms.js` SHALL be a classic script, with no `import` or `export`, that defines `globalThis.OrgSynSearch` with one function, `normaliseTerm(term)`. It splits `term` on whitespace, removes from each word every character that is not a Unicode letter (`\p{L}`) or number (`\p{N}`), drops empty words, and joins the rest with single spaces.

#### Scenario: Normalised terms
- **WHEN** a Node test loads `search-terms.js` and calls `normaliseTerm` on `CC(=O)O c1ccccc1`, `50-78-2`, `  sample-data  `, `α-pinene` and `(E)-chalcone`, skipping when `node` is absent
- **THEN** it returns `CCOO c1ccccc1`, `50782`, `sampledata`, `αpinene` and `Echalcone`
- **AND** `OrgSynSearch` has no other property

### Requirement: Every sample is findable
Search SHALL find every shipped procedure by each of the following. Each search, made with the catalogue's searcher (requirement "Catalogue text search"), returns that procedure among its IDs:
- its product name;
- its product CAS number, written with hyphens;
- a SMILES substring;
- each of its tags;
- its ID;
- a word of its body text.

Two further rules apply:
- For every contiguous substring `q` of a procedure's SMILES with `len(N(q)) >= 3`, searching `q` returns that procedure.
- Searching a procedure's full SMILES returns exactly the procedures whose `N(product.smiles)` contains `N` of it.

#### Scenario: Name, CAS, tag, ID and body word
- **WHEN** a search test builds a copy of the test collection `tests/fixtures/collection/` and searches, for each published procedure, its `product.name`, its `product.cas`, each of its tags, its `id`, and the body word chosen below
- **THEN** every search returns that procedure
- **AND** the body word is chosen from the procedure's source file in that copy as the longest word matching `[A-Za-z]{6,}` in its `Procedure` section that, compared case-insensitively, occurs in no other procedure's source file in that copy, with ties broken alphabetically. Every published procedure has such a word.

#### Scenario: CAS numbers are separate words
- **WHEN** a search test searches `50-78-2`
- **THEN** the results are exactly `OSDB-0002`

#### Scenario: Every SMILES substring
- **WHEN** a search test searches every contiguous substring `q` of every published procedure's `product.smiles` with `len(N(q)) >= 3`
- **THEN** each search returns the procedure the substring was taken from

#### Scenario: Full SMILES is exact
- **WHEN** a search test searches each published procedure's full `product.smiles`
- **THEN** the results are exactly the published procedures whose `N(product.smiles)` contains `N` of the searched string

#### Scenario: SMILES substring in the catalogue
- **WHEN** the orchestrator searches `c1ccccc1O`, `ccc(cc1)-c1`, `O=C(/C=C/c1`, `CCOC(=O)/C=C` and `OC(=O)/C=C/c1` on `/procedures/` in a browser (manual verification, tasks.md section 6)
- **THEN** they show exactly OSDB-0001; OSDB-0004 and OSDB-0005; OSDB-0006; OSDB-0007; and OSDB-0007 and OSDB-0008, the sets whose normalised SMILES contain the normalised query
- **AND** the page shows no SMILES index text

### Requirement: Node stays optional
Node SHALL be used only by tests. `tools/orgsyndb`, `tools/pipeline.py`, `tools/export.el` and `tools/hooks/pre-commit` neither invoke nor mention `node` or `npm`, and `check-deps` neither reports nor requires Node. Tests that need Node skip with a reason that names `node` when it is absent.

#### Scenario: No Node in the tools
- **WHEN** a test searches the files under `tools/` for the words `node` and `npm`, and runs `tools/orgsyndb check-deps` with a `PATH` that holds `python3`, `hugo`, `weasyprint`, `emacs` and `git`, real or stub executables, and no `node`
- **THEN** neither word is found, and `check-deps` exits 0 and prints no line mentioning `node`

### Requirement: Catalogue text search
`OrgSynCatalogue.searcher(pagefind)` SHALL take the module object of an imported `pagefind.js` and return an object whose method `search(q)` returns a promise of the IDs of the procedure pages Pagefind finds for `OrgSynSearch.normaliseTerm(q)`, in Pagefind's result order, each once:
- **Empty query.** When the normalised query is empty, it resolves to `[]` without calling Pagefind.
- **Pairing.** On its first search, the searcher calls `pagefind.filters()` and then `pagefind.search(null, {sort: {id: "asc"}})`. It pairs the result pages of that search, in their order, with the IDs whose `id` filter count is positive, sorted by code point. Later searches reuse the pairing.
- **Searching.** Each search calls `pagefind.search` with the normalised query and replaces each result page's `id` by its paired procedure ID.
- **Refusal.** It rejects with an `Error` when the number of counted IDs differs from the number of pages of the sorted search, or when a result page has no paired ID. After a rejection, the next search starts over with the pairing.
- **No fragments.** It never calls a result's `data()`.

#### Scenario: Same procedures in the same order as the result data
- **WHEN** a search test builds a copy of the test collection, loads the real bundle under Node, and runs every search of the requirement "Every sample is findable" both through the searcher and as a plain `pagefind.search` of the normalised query
- **THEN** for each, the searcher's IDs equal the `meta.id` values of the plain search's results, read with `data()`, in the same order

#### Scenario: A mismatched index is refused
- **WHEN** a Node test gives the searcher a stub whose `filters()` counts three IDs while its sorted search returns two pages; then a stub whose query result names a page the sorted search did not return; then a consistent stub with the query `--`
- **THEN** the first two searches reject with an `Error`, the third resolves to `[]` without a call to the stub's `search`, and no stub result's `data()` is ever called

