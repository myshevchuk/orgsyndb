## MODIFIED Requirements

### Requirement: manifest subcommand
`tools/orgsyndb manifest` SHALL take no arguments and print to stdout the JSON form of `pipeline.manifest_data(<collection>)` on one line, as strict JSON with non-ASCII characters written as themselves, followed by a newline. It prints no step line, writes no file and exits 0. It reads the Org procedures from the export a build leaves in `build/export/`: when `org/procedures/` holds an Org source and `build/export/` does not exist, it prints `orgsyndb: error:` and a message naming `build/export/` with exit 1, and so it does when a procedure or sequence file has no front matter it can read, naming the file. Any argument is a usage error.

`pipeline.manifest_data(collection)` returns a table of:

- `language`: `pipeline.site_language(<app>/site)`;
- `procedures`: one table per procedure ID among the files of `build/export/` and `md/procedures/` whose names the validator's procedure file-name pattern accepts, ordered by ID, each with `id`; `source`, `org` when the variant the site publishes for that ID (localization "Choosing the variant to publish") is an export of an Org source, else `md`; `title`, that variant's title; `title_de`, the title of the ID's file tagged `de`, or `null` when it has none; `reaction_type`, the one element of that variant's `reaction_types`; `general`, whether the procedure has `scope`; `authors`, the user names of that variant's `authors`, in order; and `entries`, the procedure's scope entries in file order, one per element of `scope` for a general procedure, else one made of the top-level `substrates` and `products`, each a table of `substrates`, a list of keys in file order, and `products`, a list of tables of `compound` and `yield_percent`, in file order;
- `sequences`: one table per sequence ID among the files of `md/sequences/` whose names the sequence file-name pattern accepts, ordered by ID, each with `id`; `title`, the title of the variant the site publishes; `title_de`, as for a procedure; `target`; and `steps`, a list of tables of `procedure` and `entry`, the number, counted from 1, of the entry the step names (synthesis-sequences "Sequence fields"), or `null` for a step of a specific procedure.

It reads no registry and checks no value: it runs after a build that validated the collection.

#### Scenario: Manifest of the demo
- **WHEN** a test builds a copy of the demo collection and runs `tools/orgsyndb -C <collection> manifest`
- **THEN** it exits 0 and stdout is one line of JSON whose `language` is `de`, whose `procedures` are `OSDB-0001` to `OSDB-0009` in order, `OSDB-0001` with `source` `org` and `OSDB-0002` with `source` `md`, whose `OSDB-0009` has three entries, the first with the substrates `["4-acetylbiphenyl"]` and the products `[{"compound": "1-biphenyl-4-yl-ethanol", "yield_percent": 90}]`, and whose `SEQ-0002` has the steps `OSDB-0004` with entry `null` and `OSDB-0009` with entry `1`

#### Scenario: Titles in both languages
- **WHEN** the same test reads the entry of `OSDB-0002`
- **THEN** its `title` is the title of `OSDB-0002-aspirin.de.md`, since the demo site is German, and its `title_de` the same

#### Scenario: Org sources need the export
- **WHEN** a test runs `tools/orgsyndb -C <collection> manifest` on a copy of the demo collection without `build/`
- **THEN** it exits 1, stderr begins with `orgsyndb: error:` and names `build/export/`, and stdout is empty

#### Scenario: Markdown only
- **WHEN** a test runs `tools/orgsyndb -C <collection> manifest` on a copy of the test collection without `build/`, with a `PATH` that holds only `python3`
- **THEN** it exits 0 and lists the collection's procedures and sequences

#### Scenario: Arguments are refused
- **WHEN** a test runs `tools/orgsyndb -C <collection> manifest all`
- **THEN** it exits 2, and stderr contains the word `usage`
## MODIFIED Requirements

### Requirement: build subcommand
`tools/orgsyndb build` SHALL perform these steps in order:
1. Run `export`.
2. Validate as `validate` does without arguments, stopping with exit 1 on any validation error while tolerating warnings.
3. Remove `public/`, write the staged substance data `build/data/compounds/` (site-build "Hugo configuration"), write the field data `build/data/fields.json`, the JSON form of `pipeline.fields_data(<collection>/orgsyndb.toml, <registry>, <language>)` for the site's language (compound-fields "Field data for the site"), write the reaction-type data `build/data/reaction_types.json`, the JSON form of `pipeline.reaction_types_data(<registry>, <language>)` (reaction-types "Reaction-type data for the site"), write the author data `build/data/authors.json`, the JSON form of `pipeline.authors_data(<registry>)` (procedure-authors "Author data for the site"), `<registry>` being the collection's registry as `pipeline.registry` read it for this build (compound-registry "Reading the registry"), write the route data `build/data/routes.json`, the JSON form of `pipeline.routes_data(<published procedures>)`, the published procedures being the `(path, front matter)` pairs of the variants the build staged (synthesis-routes "Derived routes"), and write the Hugo overlay `build/hugo-config/_default/hugo.toml` (site-build "Hugo configuration"), with the lab application's views when the environment variable `ORGSYNDB_LAB` is `true`, `1`, `yes` or `on`, in any case, and without them when it is unset, empty, `false`, `0`, `no` or `off`.
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
