## MODIFIED Requirements

### Requirement: build subcommand
`tools/orgsyndb build` SHALL perform these steps in order:
1. Run `export`.
2. Validate as `validate` does without arguments, stopping with exit 1 on any validation error while tolerating warnings.
3. Remove `public/`, write the staged substance data `build/data/compounds/` (site-build "Hugo configuration"), write the field data `build/data/fields.json`, the JSON form of `pipeline.fields_data(<collection>/orgsyndb.toml, <registry>, <language>)` for the site's language (compound-fields "Field data for the site"), write the reaction-type data `build/data/reaction_types.json`, the JSON form of `pipeline.reaction_types_data(<registry>, <language>)` (reaction-types "Reaction-type data for the site"), `<registry>` being the collection's registry as `pipeline.registry` read it for this build (compound-registry "Reading the registry"), write the route data `build/data/routes.json`, the JSON form of `pipeline.routes_data(<published procedures>)`, the published procedures being the `(path, front matter)` pairs of the variants the build staged (synthesis-routes "Derived routes"), and write the Hugo overlay `build/hugo-config/_default/hugo.toml` (site-build "Hugo configuration"), with the lab application's views when the environment variable `ORGSYNDB_LAB` is `true`, `1`, `yes` or `on`, in any case, and without them when it is unset, empty, `false`, `0`, `no` or `off`.
4. Run `hugo --source <app>/site --configDir <collection>/build/hugo-config --minify --quiet --noBuildLock`.
5. Obtain the Pagefind binary, and run it with `--site <collection>/public --quiet`.

A failing step stops the command with exit 1. Any other value of `ORGSYNDB_LAB` stops it with exit 1 before its first step, with a message naming the variable and the value.

#### Scenario: Validation error stops the build before Hugo
- **WHEN** an integration test builds once, adds an invalid Markdown procedure to `md/procedures/`, and builds again
- **THEN** the second build exits 1, and `public/` still holds the first build's output

#### Scenario: Second build without changes
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` twice on a copy of the demo collection without changing any source
- **THEN** both runs exit 0, and `build/export/` is not empty and holds identical bytes after each

#### Scenario: Field data is staged
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection
- **THEN** it exits 0, and `build/data/fields.json` parses as JSON to `pipeline.fields_data` of the copy's `orgsyndb.toml` and registry for the language `pipeline.site_language` reports

#### Scenario: Reaction-type data is staged
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection
- **THEN** it exits 0, and `build/data/reaction_types.json` parses as JSON to `pipeline.reaction_types_data` of the copy's registry for the language `pipeline.site_language` reports

#### Scenario: Route data is staged
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection
- **THEN** it exits 0, and `build/data/routes.json` parses as JSON to `pipeline.routes_data` of the procedures the build staged

#### Scenario: Lab views on request
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection with `ORGSYNDB_LAB=true`, and once with `ORGSYNDB_LAB=maybe`
- **THEN** the first exits 0, its overlay sets `params.lab = true` and its home page's header links `/lab/tasks/`; the second exits 1 with a message naming `ORGSYNDB_LAB` and `maybe`, and runs no export

### Requirement: index subcommand
`tools/orgsyndb index` SHALL take no arguments, and print to stdout the JSON form of `pipeline.index_data(<collection>)` (collection-index "Index data") on one line, as strict JSON with non-ASCII characters written as themselves, followed by a newline. It prints no step line, creates no file or directory, and exits 0. A configuration error that `index_data` raises is printed as `orgsyndb: error: <message>` with exit 1. Any argument is a usage error.

#### Scenario: Index of the demo
- **WHEN** a test runs `tools/orgsyndb -C <collection> index` on a copy of the demo collection without `build/`
- **THEN** it exits 0, stdout is one line that parses as JSON to `pipeline.index_data` of the copy, and the copy still has no `build/`

#### Scenario: No external tool
- **WHEN** a test runs `tools/orgsyndb -C <collection> index` on a copy of the demo collection, which has Org sources, with a `PATH` that holds only `python3`
- **THEN** it exits 0

#### Scenario: Arguments are refused
- **WHEN** a test runs `tools/orgsyndb -C <collection> index compounds`
- **THEN** it exits 2, and stderr contains the word `usage`

#### Scenario: Configuration error
- **WHEN** a test sets `vocabulary = "storage"` in the declaration of `project` in a copy of the test collection's `orgsyndb.toml` and runs `tools/orgsyndb -C <collection> index`
- **THEN** it exits 1, stderr begins with `orgsyndb: error:` and contains `storage`, and stdout is empty

#### Scenario: Registry unreachable
- **WHEN** a test points `ORGSYNDB_REGISTRY` at an address that does not answer and runs `tools/orgsyndb -C <collection> index` on a copy of the test collection without `build/`
- **THEN** it exits 1, stderr begins with `orgsyndb: error:` and names the address, and stdout is empty

### Requirement: validate subcommand
`tools/orgsyndb validate` SHALL take no arguments. It reads the collection's registry (compound-registry "Reading the registry"), which leaves it in `build/registry.json`, runs `export`, then the validator with the arguments `--settings orgsyndb.toml --static-dir static --registry build/registry.json --sequences md/sequences build/export md/procedures` and the collection as working directory, leaving out any content root whose directory does not exist. It prints the validator's stdout and stderr unchanged and exits with the validator's status. A configuration error that reading the registry raises is printed as `orgsyndb: error: <message>` with exit 1, before the export. The problem lines of the Org sources come from the export step, on stdout, in the same form; when the Org sources have an error, `validate` stops there with exit 1 and the validator does not run. Any argument is a usage error; other directories are validated by running `tools/validate.py` directly.

#### Scenario: Seeds validate
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> validate` on a copy of the test collection `tests/fixtures/collection/`
- **THEN** it exits 0, and no validator problem line is printed

#### Scenario: Invalid Markdown procedure
- **WHEN** an integration test copies `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` into the collection's `md/procedures/` and runs `tools/orgsyndb -C <collection> validate`
- **THEN** it exits 1, and stdout contains a line beginning `md/procedures/OSDB-0101-missing-title.md:title: error:`

#### Scenario: Arguments are refused
- **WHEN** a test runs `tools/orgsyndb -C <collection> validate md/procedures`, and the same with `--collection=<collection>`
- **THEN** each exits 2, stderr contains `validate.py`, and the collection's `build/` was not created
