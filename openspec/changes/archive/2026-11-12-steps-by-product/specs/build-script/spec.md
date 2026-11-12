## MODIFIED Requirements

### Requirement: manifest subcommand
`tools/orgsyndb manifest` SHALL take no arguments and print to stdout the JSON form of `pipeline.manifest_data(<collection>)` on one line, as strict JSON with non-ASCII characters written as themselves, followed by a newline. It prints no step line, writes no file and exits 0. It reads the Org procedures from the export a build leaves in `build/export/`: when `org/procedures/` holds an Org source and `build/export/` does not exist, it prints `orgsyndb: error:` and a message naming `build/export/` with exit 1, and so it does when a procedure or sequence file has no front matter it can read, naming the file. Any argument is a usage error.

`pipeline.manifest_data(collection)` returns a table of:

- `language`: `pipeline.site_language(<app>/site)`;
- `procedures`: one table per procedure ID among the files of `build/export/` and `md/procedures/` whose names the validator's procedure file-name pattern accepts, ordered by ID, each with `id`; `source`, `org` when the variant the site publishes for that ID (localization "Choosing the variant to publish") is an export of an Org source, else `md`; `title`, that variant's title; `title_de`, the title of the ID's file tagged `de`, or `null` when it has none; `reaction_type`, the one element of that variant's `reaction_types`; `general`, whether the procedure has `scope`; and `entries`, the procedure's scope entries in file order, one per element of `scope` for a general procedure, else one made of the top-level `substrates` and `products`, each a table of `substrates`, a list of keys in file order, and `products`, a list of tables of `compound` and `yield_percent`, in file order;
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
