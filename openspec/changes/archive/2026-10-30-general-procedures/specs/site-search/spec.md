## MODIFIED Requirements

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
- **THEN** they show exactly OSDB-0001; OSDB-0004, OSDB-0005 and OSDB-0009; OSDB-0006; OSDB-0007; and OSDB-0007 and OSDB-0008, the sets whose normalised SMILES contain the normalised query
- **AND** the page shows no SMILES index text
