## MODIFIED Requirements

### Requirement: validate subcommand
`tools/orgsyndb validate` SHALL take no arguments. It runs `export`, then the validator with the arguments `--settings orgsyndb.toml --static-dir static --compounds compounds --sequences md/sequences build/export md/procedures` and the collection as working directory, leaving out any content root whose directory does not exist. It prints the validator's stdout and stderr unchanged and exits with the validator's status. The problem lines of the Org sources come from the export step, on stdout, in the same form; when the Org sources have an error, `validate` stops there with exit 1 and the validator does not run. Any argument is a usage error; other directories are validated by running `tools/validate.py` directly.

#### Scenario: Seeds validate
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> validate` on a copy of the test collection `tests/fixtures/collection/`
- **THEN** it exits 0, and no validator problem line is printed

#### Scenario: Invalid Markdown procedure
- **WHEN** an integration test copies `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` into the collection's `md/procedures/` and runs `tools/orgsyndb -C <collection> validate`
- **THEN** it exits 1, and stdout contains a line beginning `md/procedures/OSDB-0101-missing-title.md:title: error:`

#### Scenario: Arguments are refused
- **WHEN** a test runs `tools/orgsyndb -C <collection> validate md/procedures`, and the same with `--collection=<collection>`
- **THEN** each exits 2, stderr contains `validate.py`, and the collection's `build/` was not created

### Requirement: build subcommand
`tools/orgsyndb build` SHALL perform these steps in order:
1. Run `export`.
2. Validate as `validate` does without arguments, stopping with exit 1 on any validation error while tolerating warnings.
3. Remove `public/`, write the field data `build/data/fields.json`, the JSON form of `pipeline.fields_data(<collection>/orgsyndb.toml, <language>)` for the site's language (compound-fields "Field data for the site"), and write the Hugo overlay `build/hugo-config/_default/hugo.toml` (site-build "Hugo configuration").
4. Run `hugo --source <app>/site --configDir <collection>/build/hugo-config --minify --quiet --noBuildLock`.
5. Obtain the Pagefind binary, and run it with `--site <collection>/public --quiet`.

A failing step stops the command with exit 1.

#### Scenario: Validation error stops the build before Hugo
- **WHEN** an integration test builds once, adds an invalid Markdown procedure to `md/procedures/`, and builds again
- **THEN** the second build exits 1, and `public/` still holds the first build's output

#### Scenario: Second build without changes
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` twice on a copy of the demo collection without changing any source
- **THEN** both runs exit 0, and `build/export/` is not empty and holds identical bytes after each

#### Scenario: Field data is staged
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection
- **THEN** it exits 0, and `build/data/fields.json` parses as JSON to `pipeline.fields_data` of the copy's `orgsyndb.toml` for the language `pipeline.site_language` reports

