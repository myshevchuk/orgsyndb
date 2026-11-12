## MODIFIED Requirements

### Requirement: new subcommand
`tools/orgsyndb new [--md | --sequence] TITLE...` SHALL create one procedure stub in the collection with `pipeline.new_procedure(collection, words, md, now, language)`, or with `--sequence` one sequence stub with `pipeline.new_sequence(collection, words, now)`, and print the created file's path relative to the collection. `--sequence` with `--md` or `--lang` is a usage error. `new_procedure` and `new_sequence` check the title, and `new_procedure` the `--lang` value; a bad value raises `pipeline.UsageError`, and the program exits 2. When no ID can be had, they raise `validate.ConfigError`, printed as `orgsyndb: error: <message>` with exit 1, and create nothing. The stub is created as follows:
- The title is the words of `TITLE...` joined by single spaces and trimmed. It must not be empty or contain a newline.
- A procedure stub is `org/procedures/<ID>-<slug>.org`, or `md/procedures/<ID>-<slug>.md` with `--md`, copied from the application's `templates/procedure.org` or `templates/procedure.md` and filled by `pipeline.fill_template` with the kind `org` or `md`. A sequence stub is `md/sequences/<ID>-<slug>.md`, copied from `templates/sequence.md` and filled with the kind `sequence`: every `SEQ-0000` becomes the ID and every `seq-0000` its lowercase form, and the `title`, `date` and `lastmod` lines take the title and the time as in a Markdown procedure stub.
- It is created with exclusive creation, so an existing file is never overwritten.
- `ID` is `pipeline.take_id(collection, kind)`, the kind `procedure` or `sequence`. When the `registry` that the collection's `orgsyndb.toml` names is an address, whatever `ORGSYNDB_REGISTRY` holds, the lab application issues it: `take_id` posts `{"kind": <kind>}` to `<origin>/lab/collection/ids/` (collection-import "Issued IDs"), `<origin>` being the address's scheme, host and port, with a timeout of 30 seconds and `Authorization: Bearer <token>`. The token is `ORGSYNDB_TOKEN` when it is set and not empty, else the first line of `$XDG_CONFIG_HOME/orgsyndb/token`, `XDG_CONFIG_HOME` being `~/.config` when unset or empty; without one, `take_id` fails with a message naming both. An answer other than 201 with an `id` of the kind fails with a message naming the address, the status and the answer's `error` when it has one. When the collection's `registry` is a path or is not named, `ID` is `pipeline.next_id(<candidate names>, <prefix>)`, the prefix `OSDB` or `SEQ`. `slug` is `pipeline.slugify(title)`.
- The stub records no AI model. An Org stub has no `#+AI_MODEL` line, even when the template has one, and a Markdown stub has no `ai_model` key; the Markdown template's commented-out `ai_model` line stays commented out.

`pipeline.next_id(names, prefix="OSDB")` returns the ID one above the highest `<prefix>-NNNN` that a name begins with, in any case, and `<prefix>-0001` when none does; it raises `ValueError` when the highest is `<prefix>-9999`. The candidate names of a procedure are:
- the top-level entry names of the collection's `org/procedures/`, `md/procedures/` and `build/export/`;
- the base names of every path that `git -C <collection> log --all --no-renames --format= --name-only -- org/procedures md/procedures` reports.

Those of a sequence are the top-level entry names of `md/sequences/` and the base names of the paths that the same command reports for `md/sequences`.

When `git` is unavailable or the collection is not inside a git work tree, `new` prints a warning to stderr and uses the directories alone. When the work tree is a shallow clone, `new` still scans the history it has, and prints a warning to stderr containing `shallow`, because IDs deleted before the shallow boundary cannot be seen.

#### Scenario: Next ID across trees, exports and history
- **WHEN** a test calls `next_id` with `OSDB-0001-a.org`, `OSDB-0002-b.md`, `OSDB-0007-c.md`, `OSDB-0004-d.md`, `notes.txt` and `osdb-0011-lowercase.md`
- **THEN** it returns `OSDB-0012`

#### Scenario: First ID
- **WHEN** a test calls `next_id` with no names that begin with an ID
- **THEN** it returns `OSDB-0001`

#### Scenario: ID space exhausted
- **WHEN** a test calls `next_id` with `OSDB-9999-last.md`
- **THEN** it raises `ValueError`

#### Scenario: Deleted committed procedure is not reused
- **WHEN** a test makes a temporary git repository holding a collection, commits `md/procedures/OSDB-0012-old.md`, deletes it in a second commit, and calls `new_procedure` on it for the Markdown title `Test product` at `2026-10-19T17:42:05+02:00`
- **THEN** the created file is `md/procedures/OSDB-0013-test-product.md`

#### Scenario: Collection in a subdirectory of a work tree
- **WHEN** a test makes a temporary git repository with a collection in its subdirectory `data/`, commits `data/md/procedures/OSDB-0012-old.md`, deletes it in a second commit, and calls `new_procedure` on `<repo>/data` for the Markdown title `Test product` at `2026-10-19T17:42:05+02:00`
- **THEN** the created file is `data/md/procedures/OSDB-0013-test-product.md`, and stderr contains no warning

#### Scenario: Shallow clone warns
- **WHEN** a test makes a temporary git repository holding a collection and two commits, clones it with `git clone --depth 1 file://…`, and calls `new_procedure` on the clone for the Markdown title `Test product` at `2026-10-19T17:42:05+02:00`
- **THEN** it creates the stub, and stderr contains `shallow`

#### Scenario: Slugs from titles
- **WHEN** a test calls `slugify` on `4-tert-Butylcyclohexanol`, `(E)-Chalcone`, `Salicylic acid` and `Ethyl  acetate!`
- **THEN** it returns `4-tert-butylcyclohexanol`, `e-chalcone`, `salicylic-acid` and `ethyl-acetate`

#### Scenario: Long and empty titles
- **WHEN** a test calls `slugify` on a 60-character title of hyphen-separated words, and on `αβγ`
- **THEN** the first result has at most 40 characters, matches `^[a-z0-9]+(-[a-z0-9]+)*$`, and is a prefix of the full slug ending at a word boundary
- **AND** the second call raises `ValueError`

#### Scenario: Org timestamps in summer and winter
- **WHEN** a test calls `org_timestamp` on `2026-10-19T15:42:05+00:00` and on `2026-01-05T08:00:00+00:00`
- **THEN** it returns `[2026-10-19 Mon 17:42:05]` and `[2026-01-05 Mon 09:00:00]`

#### Scenario: Weekday independent of the locale
- **WHEN** a test sets the process's `LC_TIME` locale to `de_DE.UTF-8`, skipping when that locale is not installed, and calls `new_procedure` for an Org stub at `2026-10-19T17:42:05+02:00`
- **THEN** the created Org stub contains `#+CREATED: [2026-10-19 Mon 17:42:05]`

#### Scenario: Org stub
- **WHEN** a test calls `new_procedure` on a temporary collection with empty trees for the Org title `Salicylic acid` at `2026-10-19T17:42:05+02:00`
- **THEN** it returns `org/procedures/OSDB-0001-salicylic-acid.org`, and that file exists
- **AND** it contains the lines `#+TITLE: Salicylic acid`, `#+CREATED: [2026-10-19 Mon 17:42:05]`, `#+LAST_MODIFIED: [2026-10-19 Mon 17:42:05]` and `#+HUGO_SLUG: osdb-0001`, each exactly once, no line that begins, case-insensitively, with `#+AI_MODEL:`, and no `OSDB-0000` or `osdb-0000`

#### Scenario: Markdown stub with a quoted title
- **WHEN** a test calls `new_procedure` in an empty temporary collection for the Markdown title `Bob's "best" ester` at `2026-10-19T17:42:05+02:00`
- **THEN** the created file is `md/procedures/OSDB-0001-bob-s-best-ester.md`
- **AND** its front matter parses with `tomllib`, with `title` equal to `Bob's "best" ester`, `date` and `lastmod` equal to `2026-10-19T17:42:05+02:00`, `id` equal to `OSDB-0001`, and no `ai_model` key
- **AND** `tools/validate.py` on its directory exits 0 and prints nothing to stdout

#### Scenario: An ID from the application
- **WHEN** a test serves an ID endpoint answering `{"id": "OSDB-0042"}` beside a snapshot, points a collection's registry at that snapshot, sets `ORGSYNDB_TOKEN`, and runs `tools/orgsyndb new --md "Test product"`
- **THEN** it creates `md/procedures/OSDB-0042-test-product.md`, and the endpoint received the kind `procedure` with that token

#### Scenario: No token
- **WHEN** the same test runs `new` without `ORGSYNDB_TOKEN` and with no token file under the home directory
- **THEN** it exits 1, creates nothing, and stderr names `ORGSYNDB_TOKEN` and `~/.config/orgsyndb/token`

#### Scenario: Refused by the application
- **WHEN** the endpoint of the same test answers 409 with `{"error": "no import yet"}`
- **THEN** `new` exits 1, creates nothing, and stderr contains `409` and `no import yet`

#### Scenario: The registry setting decides
- **WHEN** the same test sets `ORGSYNDB_REGISTRY` to a snapshot file and runs `new --md "Test product"` with a token
- **THEN** the endpoint is still asked, and the file created is `md/procedures/OSDB-0042-test-product.md`

#### Scenario: Next sequence ID
- **WHEN** a test calls `next_id` with `SEQ-0002-a.md`, `OSDB-0007-b.md` and `seq-0004-c.md` and the prefix `SEQ`
- **THEN** it returns `SEQ-0005`

#### Scenario: A sequence stub
- **WHEN** a test makes a temporary git repository holding a collection whose registry is a file, commits `md/sequences/SEQ-0002-a.md` and `md/sequences/SEQ-0004-old.md`, deletes the second in another commit, and calls `new_sequence` on it for the title `Aspirin route` at `2026-10-19T17:42:05+02:00`
- **THEN** it creates `md/sequences/SEQ-0005-aspirin-route.md`, whose front matter parses with `tomllib` to `id` `SEQ-0005`, `slug` `seq-0005`, `title` `Aspirin route`, and `date` and `lastmod` `2026-10-19T17:42:05+02:00`
- **AND** `tools/orgsyndb new --sequence --md "Aspirin route"` exits 2 and creates nothing

### Requirement: manifest subcommand
`tools/orgsyndb manifest` SHALL take no arguments and print to stdout the JSON form of `pipeline.manifest_data(<collection>)` on one line, as strict JSON with non-ASCII characters written as themselves, followed by a newline. It prints no step line, writes no file and exits 0. It reads the Org procedures from the export a build leaves in `build/export/`: when `org/procedures/` holds an Org source and `build/export/` does not exist, it prints `orgsyndb: error:` and a message naming `build/export/` with exit 1, and so it does when a procedure or sequence file has no front matter it can read, naming the file. Any argument is a usage error.

`pipeline.manifest_data(collection)` returns a table of:

- `language`: `pipeline.site_language(<app>/site)`;
- `procedures`: one table per procedure ID among the files of `build/export/` and `md/procedures/` whose names the validator's procedure file-name pattern accepts, ordered by ID, each with `id`; `source`, `org` when the variant the site publishes for that ID (localization "Choosing the variant to publish") is an export of an Org source, else `md`; `title`, that variant's title; `title_de`, the title of the ID's file tagged `de`, or `null` when it has none; `reaction_type`, the one element of that variant's `reaction_types`; `general`, whether the procedure has `scope`; and `entries`, the procedure's scope entries in file order, one per element of `scope` for a general procedure, else one made of the top-level `substrates` and `products`, each a table of `substrates`, a list of keys in file order, and `products`, a list of tables of `compound` and `yield_percent`, in file order;
- `sequences`: one table per sequence ID among the files of `md/sequences/` whose names the sequence file-name pattern accepts, ordered by ID, each with `id`; `title`, the title of the variant the site publishes; `title_de`, as for a procedure; `target`; and `steps`, a list of tables of `procedure` and `entry`, the number, counted from 1, of the entry the step names (synthesis-sequences "Sequence fields"), or `null` for a step of a specific procedure.

- `deleted`: the procedure and sequence IDs, in upper case and in order, that the base name of a path under `org/procedures`, `md/procedures` or `md/sequences` in the collection's git history begins with, read as `new` reads it (new subcommand), and that `procedures` and `sequences` do not name. Without usable git history, or in a shallow clone, it warns on stderr as `new` does.

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

#### Scenario: Deleted IDs
- **WHEN** a test makes a temporary git repository holding a collection, commits `md/procedures/OSDB-0012-old.md` and `md/sequences/SEQ-0004-old.md`, deletes both in a second commit, and calls `manifest_data` on it
- **THEN** its `deleted` is `["OSDB-0012", "SEQ-0004"]`

#### Scenario: Nothing deleted from the demo
- **WHEN** a test builds a copy of the demo collection and runs `tools/orgsyndb -C <collection> manifest`
- **THEN** its `deleted` is `[]`
