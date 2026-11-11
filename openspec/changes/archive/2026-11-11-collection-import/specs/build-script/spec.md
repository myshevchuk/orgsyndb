## ADDED Requirements

### Requirement: manifest subcommand
`tools/orgsyndb manifest` SHALL take no arguments and print to stdout the JSON form of `pipeline.manifest_data(<collection>)` on one line, as strict JSON with non-ASCII characters written as themselves, followed by a newline. It prints no step line, writes no file and exits 0. It reads the Org procedures from the export a build leaves in `build/export/`: when `org/procedures/` holds an Org source and `build/export/` does not exist, it prints `orgsyndb: error:` and a message naming `build/export/` with exit 1, and so it does when a procedure or sequence file has no front matter it can read, naming the file. Any argument is a usage error.

`pipeline.manifest_data(collection)` returns a table of:

- `language`: `pipeline.site_language(<app>/site)`;
- `procedures`: one table per procedure ID among the files of `build/export/` and `md/procedures/` whose names the validator's procedure file-name pattern accepts, ordered by ID, each with `id`; `source`, `org` when the variant the site publishes for that ID (localization "Choosing the variant to publish") is an export of an Org source, else `md`; `title`, that variant's title; `title_de`, the title of the ID's file tagged `de`, or `null` when it has none; `reaction_type`, the one element of that variant's `reaction_types`; `general`, whether the procedure has `scope`; and `entries`, the procedure's scope entries in file order, one per element of `scope` for a general procedure, else one made of the top-level `substrates` and `products`, each a table of `substrates`, a list of keys in file order, and `products`, a list of tables of `compound` and `yield_percent`, in file order;
- `sequences`: one table per sequence ID among the files of `md/sequences/` whose names the sequence file-name pattern accepts, ordered by ID, each with `id`; `title`, the title of the variant the site publishes; `title_de`, as for a procedure; `target`; and `steps`, a list of tables of `procedure` and `entry`, the step's entry number or `null` when it gives none.

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

### Requirement: Entry point conventions
`tools/orgsyndb` SHALL be an executable Python 3.14 program that uses only the standard library, besides importing `pipeline` and `validate` from its own directory. It has a `#!/usr/bin/env python3` shebang and is invoked as `orgsyndb [-C DIR] <subcommand> [options] [arguments]`, with the subcommands `export`, `validate`, `build`, `serve`, `pdf`, `new`, `init`, `clean`, `check-deps`, `index`, `manifest` and `help`. It follows these conventions:
- It locates the application from its own resolved path, following symlinks, so it works from any working directory. It refuses to run, with exit 1, unless `<app>/tools/orgsyndb` and `<app>/site/hugo.toml` exist.
- It chooses the collection as the `collection` capability says.
- It sets `TZ=Europe/Berlin` and `LC_TIME=C` in its own environment, so every child process inherits them.
- It prints a line beginning `==> ` before each step, and writes errors to stderr as `orgsyndb: error: <message>`.
- It exits 0 on success, 1 on failure, and 2 on a usage error. A usage error is a missing or unknown subcommand, an unknown option, or a missing or malformed option value, and its usage text goes to stderr. `help`, `-h` and `--help` print the usage text to stdout and exit 0.
- It deletes nothing outside the collection's `build/`, `public/` and `pdf/` and the application's `.emacs-batch/` and `.tools/`.
- It does not write Python bytecode caches.

#### Scenario: Unknown subcommand
- **WHEN** a test runs `tools/orgsyndb frobnicate` from a temporary working directory
- **THEN** it exits 2, and stderr contains `frobnicate` and the word `usage`

#### Scenario: No subcommand
- **WHEN** a test runs `tools/orgsyndb` with no arguments
- **THEN** it exits 2, and stderr contains the word `usage`

#### Scenario: Help
- **WHEN** a test runs `tools/orgsyndb help`
- **THEN** it exits 0, and stdout names every subcommand and `-C`

#### Scenario: Syntax and formatting
- **WHEN** a test compiles `tools/orgsyndb` with `py_compile` and runs `sh -n tools/hooks/pre-commit`
- **THEN** both succeed

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/orgsyndb` with `ast` and collects the top-level module names of every import
- **THEN** every name is in `sys.stdlib_module_names` or is `pipeline` or `validate`

#### Scenario: Invoked through a symlink
- **WHEN** a test creates a symlink to `tools/orgsyndb` in a temporary directory and runs `<symlink> help` from that directory
- **THEN** it exits 0

#### Scenario: No fish
- **WHEN** a test lists the files under `tools/`
- **THEN** none ends in `.fish`, and none begins with a `#!` line naming `fish`
