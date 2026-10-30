## MODIFIED Requirements

### Requirement: validate subcommand
`tools/orgsyndb validate` SHALL take no arguments. It runs `export`, then the validator with the arguments `--static-dir static --compounds compounds --sequences md/sequences build/export md/procedures` and the collection as working directory, leaving out any content root whose directory does not exist. It prints the validator's stdout and stderr unchanged and exits with the validator's status. The problem lines of the Org sources come from the export step, on stdout, in the same form; when the Org sources have an error, `validate` stops there with exit 1 and the validator does not run. Any argument is a usage error; other directories are validated by running `tools/validate.py` directly.

#### Scenario: Seeds validate
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> validate` on a copy of the test collection `tests/fixtures/collection/`
- **THEN** it exits 0, and no validator problem line is printed

#### Scenario: Invalid Markdown procedure
- **WHEN** an integration test copies `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` into the collection's `md/procedures/` and runs `tools/orgsyndb -C <collection> validate`
- **THEN** it exits 1, and stdout contains a line beginning `md/procedures/OSDB-0101-missing-title.md:title: error:`

#### Scenario: Arguments are refused
- **WHEN** a test runs `tools/orgsyndb -C <collection> validate md/procedures`, and the same with `--collection=<collection>`
- **THEN** each exits 2, stderr contains `validate.py`, and the collection's `build/` was not created
