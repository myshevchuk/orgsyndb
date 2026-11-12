# procedure-authors Specification

## Purpose
Define a procedure's authors as lab accounts named by user name, the check of them against the collection's registry, and the authors' names the site shows.
## Requirements
### Requirement: Authors are accounts
A procedure's `authors` SHALL be user names of accounts the collection's registry lists (lab-registry "Snapshot"), each once. A name the registry lacks is an error under `authors` containing `unknown author "<name>"; the registry has no account of this user name`, and a name given twice an error containing `"<name>" is named twice`. An account named as an author need not be active.

#### Scenario: Unknown author
- **WHEN** a variant run sets `authors = ["a.example", "z.nobody"]` in the baseline
- **THEN** it reports exactly one error, field `authors`, containing `unknown author "z.nobody"`

#### Scenario: An author twice
- **WHEN** a variant run sets `authors = ["a.example", "a.example"]`
- **THEN** it reports exactly one error, field `authors`, containing `"a.example" is named twice`

### Requirement: Author data for the site
`pipeline.authors_data(registry)` SHALL return a table mapping the user name of every account of the registry to its name, and the build stages it as `build/data/authors.json` (build-script "build subcommand"). The site's author taxonomy has the user names as its terms, so an author's term key is its user name and its page is `/authors/<user name>/`. Wherever the site writes an author — the metadata panel's `Authors`, the authors' taxonomy page and an author's term page, the catalogue's author facet and its static label `Only procedures by <author>`, and the search text of a procedure — it writes the account's name from that data, and the user name where the data lacks it.

#### Scenario: An author's page
- **WHEN** a test builds a copy of the test collection in locale `en`
- **THEN** `public/authors/klehmann/index.html` exists, its `h1` is `Katrin Lehmann`, and the metadata panel of every procedure that names `klehmann` links `/authors/klehmann/` with the text `Katrin Lehmann`

#### Scenario: Author data
- **WHEN** a test calls `authors_data` on the test collection's registry
- **THEN** it maps `a.example` to `A. Example` and has one key per account of the registry

