## MODIFIED Requirements

### Requirement: Problem report format
The validator SHALL print each problem to stdout as one line of the form `<path>:<field>: <severity>: <message>`, where `<severity>` is `error` or `warning`.
- `<path>` is the root argument as given, joined with the entry name; for a compound file, the `--compounds` argument as given, joined with the file name.
- `<field>` is the front-matter key, or `products[n].<key>` for a key inside the `n`-th product (procedure-schema "Products"), or `scope[n].<key>` and `scope[n].products[m].<key>` for a key inside the `n`-th scope entry and its `m`-th product (general-procedures "Scope entries"). For a compound file it is the key in the file. Otherwise it is one of `file_name`, `front_matter`, `toml` or `body`.
- After the problem lines it prints one summary line to stderr: `validated <F> files: <E> errors, <W> warnings`, where `<F>` counts the Markdown procedure files and the compound files examined and excludes ignored or rejected entries.
- Entries are examined in sorted path order, and checks run in a fixed order within a file, so identical input yields identical output.

#### Scenario: Line shape
- **WHEN** a fixture run on `invalid/yield-out-of-range` completes
- **THEN** its single stdout line matches `^.+/OSDB-0110-yield-out-of-range\.md:products\[1\]\.yield_percent: error: .+$`

#### Scenario: Summary line
- **WHEN** the valid-set run completes
- **THEN** stderr contains `validated <F> files: 0 errors, 0 warnings`, where `<F>` is 4 plus the number of compound files in `tests/fixtures/compounds/`

#### Scenario: Deterministic output
- **WHEN** the same fixture run on all `invalid/*` roots at once is executed twice
- **THEN** both runs produce byte-identical stdout
