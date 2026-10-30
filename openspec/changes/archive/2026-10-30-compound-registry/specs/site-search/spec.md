## MODIFIED Requirements

### Requirement: Indexed content
The indexed element of a procedure page SHALL be its `article.procedure`, as the site-theme spec places it. The following are outside it, and are never part of the indexed text:
- the sample banner;
- the procedure header (ID line, status badge, `h1`, print facts, actions);
- the site header and its navigation;
- the footer.

The indexed text includes the metadata panel and the index-terms element. The panel shows no ID, and the formula, CAS number and SMILES of a product only when the procedure has one (site-theme "Metadata panel"), so `article.procedure` holds, after the rendered body and before the SMILES index element, a `span.index-terms` carrying `hidden`, whose text is the ID followed, for each product in order, by its shown name, its formula, its CAS number when set and its SMILES, all separated by single spaces. It is never shown, and Pagefind indexes its text. Each of these therefore occurs as a separate word or words in the indexed body:
- the ID;
- every product's name;
- every product's formula;
- every product's CAS number;
- every product's SMILES string;
- every starting material's name;
- each tag;
- the reaction-type label;
- each author.

#### Scenario: Metadata inside the body, chrome outside
- **WHEN** a test scans every procedure page after a theme build
- **THEN** the text of its single `data-pagefind-body` element contains the ID, every product's shown name, CAS number when set and SMILES, every starting material's shown name, every tag and every author
- **AND** it contains neither the banner text nor the navigation link texts as a sequence
- **AND** it has exactly one `span.index-terms`, carrying `hidden`, whose text is the ID and the product terms as stated

#### Scenario: CAS numbers are separate words
- **WHEN** a search test searches `50-78-2`
- **THEN** the results are exactly `OSDB-0002`

### Requirement: SMILES substring index
Each procedure page SHALL end its `article.procedure` with a `span` element carrying `hidden`, `data-pagefind-meta="smiles_index[data-smiles-index]"` and a `data-smiles-index` attribute. For each product, in order, let `n` be `N(smiles)` of its compound. The attribute holds, for each product in turn, every suffix of its `n`, from `n` itself down to its last character, all separated by single spaces.

#### Scenario: Index value
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build
- **THEN** the `data-smiles-index` value is `ccooc1ccccc1coo cooc1ccccc1coo ooc1ccccc1coo oc1ccccc1coo c1ccccc1coo 1ccccc1coo ccccc1coo cccc1coo ccc1coo cc1coo c1coo 1coo coo oo o`

#### Scenario: Index on every procedure page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** each has exactly one such element, as the last element child of `article.procedure`, whose value is computed from the SMILES of that procedure's products as stated

### Requirement: Every sample is findable
Search SHALL find every shipped procedure by each of the following. Each search, made with the catalogue's searcher (requirement "Catalogue text search"), returns that procedure among its IDs:
- each of its products' names;
- each of its products' CAS numbers, written with hyphens;
- a SMILES substring;
- each of its tags;
- its ID;
- a word of its body text.

Two further rules apply:
- For every contiguous substring `q` of a procedure's SMILES with `len(N(q)) >= 3`, searching `q` returns that procedure.
- Searching a product's full SMILES returns exactly the procedures with a product whose `N(smiles)` contains `N` of it.

#### Scenario: Name, CAS, tag, ID and body word
- **WHEN** a search test builds a copy of the test collection `tests/fixtures/collection/` and searches, for each published procedure, each of its products' names and CAS numbers, each of its tags, its `id`, and the body word chosen below
- **THEN** every search returns that procedure
- **AND** the body word is chosen from the procedure's source file in that copy as the longest word matching `[A-Za-z]{6,}` in its `Procedure` section that, compared case-insensitively, occurs in no other procedure's source file in that copy, with ties broken alphabetically. Every published procedure has such a word.

#### Scenario: CAS numbers are separate words
- **WHEN** a search test searches `50-78-2`
- **THEN** the results are exactly `OSDB-0002`

#### Scenario: Every SMILES substring
- **WHEN** a search test searches every contiguous substring `q` of the SMILES of every product of every published procedure, with `len(N(q)) >= 3`
- **THEN** each search returns the procedure the substring was taken from

#### Scenario: Full SMILES is exact
- **WHEN** a search test searches the full SMILES of each product of each published procedure
- **THEN** the results are exactly the published procedures with a product whose `N(smiles)` contains `N` of the searched string

#### Scenario: SMILES substring in the catalogue
- **WHEN** the orchestrator searches `c1ccccc1O`, `ccc(cc1)-c1`, `O=C(/C=C/c1`, `CCOC(=O)/C=C` and `OC(=O)/C=C/c1` on `/procedures/` in a browser (manual verification, tasks.md section 6)
- **THEN** they show exactly OSDB-0001; OSDB-0004 and OSDB-0005; OSDB-0006; OSDB-0007; and OSDB-0007 and OSDB-0008, the sets whose normalised SMILES contain the normalised query
- **AND** the page shows no SMILES index text
