## MODIFIED Requirements

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
