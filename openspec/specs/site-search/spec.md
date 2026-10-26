# site-search Specification

## Purpose
Define the Pagefind search: what is indexed, the status, reaction type, tag and author filters, SMILES substring search, and the search page with its no-JavaScript fallback.
## Requirements
### Requirement: Search page
The site SHALL publish `/search/` from `site/content/search.md`, with the following:
- **Assets.** It links `/pagefind/pagefind-ui.css` and loads, in order, `/pagefind/pagefind-ui.js` and the theme's search script. The search script is built from `site/assets/js/search-terms.js` and `site/assets/js/search.js`.
- **The UI.** It contains one empty element with `data-search`, into which the search script mounts Pagefind's default UI (`PagefindUI`). The UI is configured with:
  - `element: "[data-search]"`;
  - `showImages: false`;
  - `processTerm: OrgSynSearch.normaliseTerm`;
  - `processResult: OrgSynSearch.cleanResult`.
- **The `q` parameter.** When the page URL has a `q` query parameter, the script calls `triggerSearch` with its value.
- **No-JS fallback.** It contains a `noscript` element whose text says that search needs JavaScript, and which links `/procedures/`, `/reaction_types/`, `/tags/` and `/authors/`.

The page carries no `data-pagefind-body`.

#### Scenario: Search page wiring
- **WHEN** a test scans `public/search/index.html` after a theme build
- **THEN** it has the stylesheet, the two scripts in order, one empty `[data-search]` element, and a `noscript` with the four links
- **AND** the built search script contains `PagefindUI`, `processTerm`, `processResult` and `triggerSearch`

#### Scenario: Keyboard use in a browser
- **WHEN** the orchestrator opens `/search/?q=aspirin` from `tools/orgsyndb serve` and uses only the keyboard (manual verification, tasks.md section 9)
- **THEN** results are shown for `aspirin`, focus reaches the input, the filter groups, their checkboxes and the result links with Tab, a focus outline is visible on each, and Space toggles a filter

### Requirement: Indexed content
The indexed element of a procedure page SHALL be its `article.procedure`, as the site-theme spec places it. The following are outside it, and are never part of the indexed text:
- the sample banner;
- the procedure header (ID line, status badge, `h1`, print facts, actions);
- the site header and its navigation;
- the footer.

The indexed text includes the metadata panel. Each of these therefore occurs as a separate word or words in the indexed body:
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

#### Scenario: CAS numbers are separate words
- **WHEN** a search test searches `50-78-2`
- **THEN** the results are exactly `OSDB-0002`

### Requirement: Search filters
Procedure pages SHALL carry Pagefind filters in the content form `data-pagefind-filter="<key>"`, each on a visible element whose whole text is the value:
- `status`: on the header's status badge, whose text is the status;
- `reaction type`: on the panel's reaction-type link, whose text is the vocabulary label;
- `tag`: on each tag link, whose text is the tag;
- `author`: on each author link, whose text is the name.

No list or container element carries `data-pagefind-filter`.

#### Scenario: Filter attributes on every procedure page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** it has exactly one `status` filter element, whose text equals `status`; exactly one `reaction type` filter element, whose text equals the vocabulary label of its `reaction_types` entry; one `tag` filter element per tag; and one `author` filter element per author
- **AND** no `ul`, `ol` or `dl` element carries `data-pagefind-filter`

#### Scenario: Filter values and filter-only searches
- **WHEN** a search test reads the bundle's `filters()`, and searches with a `null` term and each single filter value in turn
- **THEN** the filter keys are exactly `author`, `reaction type`, `status` and `tag`, and their values are exactly the authors, labels, statuses and tags of the published procedures
- **AND** each filter-only search returns exactly the procedures that carry that value

#### Scenario: Filters in the UI
- **WHEN** the orchestrator searches `sample` on `/search/` in a browser and ticks filter values (manual verification, tasks.md section 9)
- **THEN** each ticked value narrows the results to the procedures carrying it, the groups read "Author", "Reaction type", "Status" and "Tag", and the reaction-type values are vocabulary labels

### Requirement: Result metadata
Each procedure page SHALL give Pagefind:
- the meta field `id`, from the element holding the ID in the header;
- the meta field `smiles_index`, from the SMILES index element.

Pagefind takes the result title from the page's `h1`. `OrgSynSearch.cleanResult` deletes `smiles_index` from a result's `meta` before the UI renders it, and leaves every other field unchanged.

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
`site/assets/js/search-terms.js` SHALL be a classic script, with no `import` or `export`, that defines `globalThis.OrgSynSearch` with these two functions:
- `normaliseTerm(term)`. It splits `term` on whitespace, removes from each word every character that is not a Unicode letter (`\p{L}`) or number (`\p{N}`), drops empty words, and joins the rest with single spaces.
- `cleanResult(result)`. It returns `result` with its `meta.smiles_index` key deleted.

#### Scenario: Normalised terms
- **WHEN** a Node test loads `search-terms.js` and calls `normaliseTerm` on `CC(=O)O c1ccccc1`, `50-78-2`, `  sample-data  `, `α-pinene` and `(E)-chalcone`, skipping when `node` is absent
- **THEN** it returns `CCOO c1ccccc1`, `50782`, `sampledata`, `αpinene` and `Echalcone`

#### Scenario: Cleaned result
- **WHEN** the same test calls `cleanResult` on `{"meta": {"id": "OSDB-0001", "smiles_index": "x y"}, "excerpt": "e"}`
- **THEN** it returns `{"meta": {"id": "OSDB-0001"}, "excerpt": "e"}`

### Requirement: Every sample is findable
Search SHALL find every shipped procedure by each of the following. Each search returns that procedure among its results:
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

#### Scenario: Every SMILES substring
- **WHEN** a search test searches every contiguous substring `q` of every published procedure's `product.smiles` with `len(N(q)) >= 3`
- **THEN** each search returns the procedure the substring was taken from

#### Scenario: Full SMILES is exact
- **WHEN** a search test searches each published procedure's full `product.smiles`
- **THEN** the results are exactly the published procedures whose `N(product.smiles)` contains `N` of the searched string

#### Scenario: SMILES substring in the UI
- **WHEN** the orchestrator searches `c1ccccc1O`, `ccc(cc1)-c1`, `O=C(/C=C/c1`, `CCOC(=O)/C=C` and `OC(=O)/C=C/c1` on `/search/` in a browser (manual verification, tasks.md section 9)
- **THEN** they show exactly OSDB-0001; OSDB-0004 and OSDB-0005; OSDB-0006; OSDB-0007; and OSDB-0007 and OSDB-0008, the sets whose normalised SMILES contain the normalised query
- **AND** no excerpt shows the SMILES index

### Requirement: Node stays optional
Node SHALL be used only by tests. `tools/orgsyndb`, `tools/pipeline.py`, `tools/export.el` and `tools/hooks/pre-commit` neither invoke nor mention `node` or `npm`, and `check-deps` neither reports nor requires Node. Tests that need Node skip with a reason that names `node` when it is absent.

#### Scenario: No Node in the tools
- **WHEN** a test searches the files under `tools/` for the words `node` and `npm`, and runs `tools/orgsyndb check-deps` with a `PATH` that holds `python3`, `hugo`, `weasyprint`, `emacs` and `git`, real or stub executables, and no `node`
- **THEN** neither word is found, and `check-deps` exits 0 and prints no line mentioning `node`

