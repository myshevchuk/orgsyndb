## MODIFIED Requirements

### Requirement: Missing tools stop a subcommand before its first step
Each subcommand SHALL check, before its first step, every external tool it will need. A collection has Org sources when `org/procedures/` holds at least one top-level entry that the export either exports or reports (org-export "Org sources and their problems"), decided from the entry names alone (ignoring dotfiles and `_index.md`).
- `export`: `emacs` and `git` when the collection has Org sources, and no external tool otherwise. With Org sources, `git` is needed on every run, not only for the bootstrap, because every export checks the installed checkouts against their pins.
- `validate`: what `export` needs.
- `new`, `init`, `clean`, `check-deps`, `index` and `help`: no external tool. `git` is optional for `new`; without it `new` warns and scans the directories alone.
- `build`: what `export` needs, plus `hugo`.
- `serve`: what `build` needs.
- `pdf`: what `build` needs, plus `weasyprint`.

For a missing tool it prints `orgsyndb: error: <tool> not found; install it with your system's package manager` and exits 1 without starting any step. It never invokes `sudo`. A subcommand that works on a collection finds the collection before it checks the tools, so a missing or malformed collection is reported whatever tools are installed.

#### Scenario: Org sources by entry names
- **WHEN** a test checks whether a directory has Org sources for one that does not exist, an empty directory, one holding only `.gitkeep`, one holding only `notes.txt`, one holding only a subdirectory `nested/`, and one holding only `OSDB-0001-a.org`
- **THEN** they report false, false, false, true, true and true respectively

#### Scenario: Hugo missing
- **WHEN** a test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection `tests/fixtures/collection/`, which has no Org sources, with a `PATH` that holds `python3` and a recording fake `sudo`, but not `hugo`
- **THEN** it exits 1, stderr contains `hugo not found; install it with your system's package manager`, the collection's `build/` was not created, and the fake `sudo` was never invoked

#### Scenario: git missing although ox-hugo is installed
- **WHEN** a test runs `tools/orgsyndb -C <collection> export` on a copy of the demo collection in an application copy whose `.emacs-batch/` is linked from a bootstrapped checkout, with a `PATH` that holds `python3`, `emacs` (real or stub executable) and a recording fake `sudo`, but not `git`
- **THEN** it exits 1, stderr contains `git not found; install it with your system's package manager`, the collection's `build/` was not created, and the fake `sudo` was never invoked

#### Scenario: Emacs missing with Org sources
- **WHEN** a test runs `tools/orgsyndb -C <collection> build` on the demo collection with a `PATH` that holds `python3`, `git`, `hugo` and a recording fake `sudo`, but not `emacs`
- **THEN** it exits 1, stderr contains `emacs not found; install it with your system's package manager`, the collection's `build/` was not created, and the fake `sudo` was never invoked

#### Scenario: Markdown-only collection builds without Emacs and git
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection `tests/fixtures/collection/` with a `PATH` that holds `python3` and `hugo` but neither `emacs` nor `git`, skipping when Hugo or the Pagefind cache is absent
- **THEN** it exits 0, and `public/index.html` and `public/procedures/osdb-0002/index.html` exist

#### Scenario: Collection error comes before missing tools
- **WHEN** a test runs `tools/orgsyndb -C <directory without orgsyndb.toml> build` with a `PATH` that holds only `python3` and a recording fake `sudo`
- **THEN** it exits 1, stderr contains `orgsyndb.toml` and no `not found`, and the fake `sudo` was never invoked

### Requirement: build subcommand
`tools/orgsyndb build` SHALL perform these steps in order:
1. Run `export`.
2. Validate as `validate` does without arguments, stopping with exit 1 on any validation error while tolerating warnings.
3. Remove `public/` and `build/data/`, so that `build/data/` holds only what this build writes, stage the substance data `build/data/compounds/` (site-build "Hugo configuration"), write `build/data/fields.json` (compound-fields "Field data for the site"), `build/data/reaction_types.json` (reaction-types "Reaction-type data for the site") and `build/data/authors.json` (procedure-authors "Author data for the site") from the collection's registry for the site's language (compound-registry "Reading the registry"), and write the Hugo overlay `build/hugo-config/_default/hugo.toml` (site-build "Hugo configuration"), with the lab application's views when the environment variable `ORGSYNDB_LAB` is `true`, `1`, `yes` or `on`, in any case, and without them when it is unset, empty, `false`, `0`, `no` or `off`.
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
- **THEN** it exits 0, and `build/data/fields.json` matches the field data of the copy's `orgsyndb.toml` and registry for the site's language

#### Scenario: Reaction-type data is staged
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection
- **THEN** it exits 0, and `build/data/reaction_types.json` matches the reaction-type data of the copy's registry for the site's language

#### Scenario: No route data
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection
- **THEN** it exits 0, and `build/data/routes.json` does not exist

#### Scenario: Data of an earlier build
- **WHEN** an integration test writes `build/data/routes.json` and `build/data/compounds/gone.json` into a copy of the test collection and runs `tools/orgsyndb -C <collection> build`
- **THEN** it exits 0, and neither file exists

#### Scenario: Lab views on request
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection with `ORGSYNDB_LAB=true`, and once with `ORGSYNDB_LAB=maybe`
- **THEN** the first exits 0, its overlay sets `params.lab = true` and its home page's navigation links under `/lab/`; the second exits 1 with a message naming `ORGSYNDB_LAB` and `maybe`, and runs no export

### Requirement: pdf subcommand
`tools/orgsyndb pdf` SHALL run `build`, delete `pdf/`, and render one PDF per procedure content file from `build/export/` and `md/procedures/`, sorted by PDF name:
- The output is `pdf/<content file stem>.pdf`, rendered from `public/procedures/<slug>/index.html`. When a procedure's expected HTML page does not exist under `public/`, rendering refuses with an error naming that HTML path.
- It invokes `weasyprint --allowed-protocols file <html> <pdf>` with `PYTHONWARNINGS` set so that pyphen's `pkg_resources is deprecated` `UserWarning` is not shown.
- A job fails when WeasyPrint exits non-zero or writes a line beginning `ERROR:`. A failed job's output file is removed, and the remaining jobs still run.
- It prints one line per PDF, and exits 1 when any job failed.

#### Scenario: Job naming
- **WHEN** a test computes PDF jobs for `md/procedures/OSDB-0002-aspirin.md` with front matter `slug = "osdb-0002"`
- **THEN** the single job's input is `<public>/procedures/osdb-0002/index.html` and its output is `<pdf>/OSDB-0002-aspirin.pdf`

#### Scenario: Missing page
- **WHEN** a test computes PDF jobs for a content file whose HTML page does not exist under `public`
- **THEN** it raises `ValueError`, whose message contains the expected HTML path

#### Scenario: One PDF per procedure, no stale files
- **WHEN** an integration test places `pdf/OSDB-0999-stale.pdf` in the collection copy and runs `tools/orgsyndb -C <collection> pdf`
- **THEN** it exits 0, `pdf/` holds exactly one file `<stem>.pdf` for each procedure content file `<stem>.md` in `build/export/` and `md/procedures/`, among them `OSDB-0001-salicylic-acid.pdf` and `OSDB-0002-aspirin.pdf`, and each file begins with `%PDF-`
- **AND** neither stdout nor stderr contains `pkg_resources`

#### Scenario: Remote stylesheet fails the job
- **WHEN** an integration test adds `<link rel="stylesheet" href="https://cdn.example.invalid/x.css">` to the application copy's procedure layout and runs `tools/orgsyndb -C <collection> pdf`
- **THEN** it exits 1, and stderr names the failing PDF

### Requirement: new subcommand
`tools/orgsyndb new [--md | --sequence] [--lang CODE] TITLE...` SHALL create one procedure stub in the collection, or with `--sequence` one sequence stub, and print the created file's path relative to the collection. `--sequence` with `--md` or `--lang`, an invalid title, or an invalid `--lang` value is a usage error (exit 2). When no ID can be obtained, the command prints `orgsyndb: error: <message>` to stderr, exits 1, and creates nothing. The stub is created as follows:
- The title is the words of `TITLE...` joined by single spaces and trimmed. It must not be empty or contain a newline.
- A procedure stub is `org/procedures/<ID>-<slug>.org`, or `md/procedures/<ID>-<slug>.md` with `--md`, filled from the application's `templates/procedure.org` or `templates/procedure.md` (or the language-specific template when `--lang` names one). A sequence stub is `md/sequences/<ID>-<slug>.md`, filled from `templates/sequence.md`: every `SEQ-0000` becomes the ID and every `seq-0000` its lowercase form, and the `title`, `date` and `lastmod` lines take the title and the Europe/Berlin timestamp as in a Markdown procedure stub. Org timestamps use English weekday abbreviations regardless of process locale.
- It is created with exclusive creation, so an existing file is never overwritten.
- When the `registry` that the collection's `orgsyndb.toml` names is an address, whatever `ORGSYNDB_REGISTRY` holds, the lab application issues `ID`: the command posts `{"kind": <kind>}` (`procedure` or `sequence`) to `<origin>/lab/collection/ids/` (collection-import "Issued IDs"), `<origin>` being the address's scheme, host and port, with a timeout of 30 seconds and `Authorization: Bearer <token>`. The token is `ORGSYNDB_TOKEN` when it is set and not empty, else the first line of `$XDG_CONFIG_HOME/orgsyndb/token`, `XDG_CONFIG_HOME` being `~/.config` when unset or empty; without one, it fails with a message naming both. An answer other than 201 with an `id` of the kind fails with a message naming the address, the status and the answer's `error` when it has one.
- When the collection's `registry` is a path or is not named, `ID` is one above the highest `<prefix>-NNNN` (prefix `OSDB` or `SEQ`, matched in any case) that any candidate name begins with, or `<prefix>-0001` when none does; exhausting `<prefix>-9999` fails. The candidate names of a procedure are the top-level entry names of `org/procedures/`, `md/procedures/` and `build/export/` plus the base names of every path that `git -C <collection> log --all --no-renames --format= --name-only -- org/procedures md/procedures` reports; those of a sequence are the top-level entry names of `md/sequences/` plus the base names reported for `md/sequences`.
- The file-name `<slug>` is derived from the title as lowercase ASCII words joined by `-`, at most 40 characters ending on a word boundary; a title that yields no ASCII alphanumeric characters is refused.
- The stub records no AI model. An Org stub has no `#+AI_MODEL` line, even when the template has one, and a Markdown stub has no `ai_model` key; the Markdown template's commented-out `ai_model` line stays commented out.

When `git` is unavailable or the collection is not inside a git work tree, `new` prints a warning to stderr and uses the directories alone. When the work tree is a shallow clone, `new` still scans the history it has, and prints a warning to stderr containing `shallow`, because IDs deleted before the shallow boundary cannot be seen.

#### Scenario: Next ID across trees, exports and history
- **WHEN** a test computes the next procedure ID from `OSDB-0001-a.org`, `OSDB-0002-b.md`, `OSDB-0007-c.md`, `OSDB-0004-d.md`, `notes.txt` and `osdb-0011-lowercase.md`
- **THEN** it returns `OSDB-0012`

#### Scenario: First ID
- **WHEN** a test computes the next procedure ID with no names that begin with an ID
- **THEN** it returns `OSDB-0001`

#### Scenario: ID space exhausted
- **WHEN** a test computes the next procedure ID with `OSDB-9999-last.md`
- **THEN** it raises `ValueError`

#### Scenario: Deleted committed procedure is not reused
- **WHEN** a test makes a temporary git repository holding a collection, commits `md/procedures/OSDB-0012-old.md`, deletes it in a second commit, and creates a Markdown procedure stub titled `Test product` at `2026-10-19T17:42:05+02:00`
- **THEN** the created file is `md/procedures/OSDB-0013-test-product.md`

#### Scenario: Collection in a subdirectory of a work tree
- **WHEN** a test makes a temporary git repository with a collection in its subdirectory `data/`, commits `data/md/procedures/OSDB-0012-old.md`, deletes it in a second commit, and creates a Markdown procedure stub in `<repo>/data` titled `Test product` at `2026-10-19T17:42:05+02:00`
- **THEN** the created file is `data/md/procedures/OSDB-0013-test-product.md`, and stderr contains no warning

#### Scenario: Shallow clone warns
- **WHEN** a test makes a temporary git repository holding a collection and two commits, clones it with `git clone --depth 1 file://…`, and creates a Markdown procedure stub on the clone titled `Test product` at `2026-10-19T17:42:05+02:00`
- **THEN** it creates the stub, and stderr contains `shallow`

#### Scenario: Slugs from titles
- **WHEN** a test slugifies `4-tert-Butylcyclohexanol`, `(E)-Chalcone`, `Salicylic acid` and `Ethyl  acetate!`
- **THEN** it returns `4-tert-butylcyclohexanol`, `e-chalcone`, `salicylic-acid` and `ethyl-acetate`

#### Scenario: Long and empty titles
- **WHEN** a test slugifies a 60-character title of hyphen-separated words, and `αβγ`
- **THEN** the first result has at most 40 characters, matches `^[a-z0-9]+(-[a-z0-9]+)*$`, and is a prefix of the full slug ending at a word boundary
- **AND** the second raises `ValueError`

#### Scenario: Org timestamps in summer and winter
- **WHEN** a test formats `2026-10-19T15:42:05+00:00` and `2026-01-05T08:00:00+00:00` as Org timestamps
- **THEN** it returns `[2026-10-19 Mon 17:42:05]` and `[2026-01-05 Mon 09:00:00]`

#### Scenario: Weekday independent of the locale
- **WHEN** a test sets the process's `LC_TIME` locale to `de_DE.UTF-8`, skipping when that locale is not installed, and creates an Org stub at `2026-10-19T17:42:05+02:00`
- **THEN** the created Org stub contains `#+CREATED: [2026-10-19 Mon 17:42:05]`

#### Scenario: Org stub
- **WHEN** a test creates an Org stub in a temporary collection with empty trees titled `Salicylic acid` at `2026-10-19T17:42:05+02:00`
- **THEN** it returns `org/procedures/OSDB-0001-salicylic-acid.org`, and that file exists
- **AND** it contains the lines `#+TITLE: Salicylic acid`, `#+CREATED: [2026-10-19 Mon 17:42:05]`, `#+LAST_MODIFIED: [2026-10-19 Mon 17:42:05]` and `#+HUGO_SLUG: osdb-0001`, each exactly once, no line that begins, case-insensitively, with `#+AI_MODEL:`, and no `OSDB-0000` or `osdb-0000`

#### Scenario: Markdown stub with a quoted title
- **WHEN** a test creates a Markdown stub in an empty temporary collection titled `Bob's "best" ester` at `2026-10-19T17:42:05+02:00`
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
- **WHEN** a test computes the next sequence ID from `SEQ-0002-a.md`, `OSDB-0007-b.md` and `seq-0004-c.md`
- **THEN** it returns `SEQ-0005`

#### Scenario: A sequence stub
- **WHEN** a test makes a temporary git repository holding a collection whose registry is a file, commits `md/sequences/SEQ-0002-a.md` and `md/sequences/SEQ-0004-old.md`, deletes the second in another commit, and creates a sequence stub titled `Aspirin route` at `2026-10-19T17:42:05+02:00`
- **THEN** it creates `md/sequences/SEQ-0005-aspirin-route.md`, whose front matter parses with `tomllib` to `id` `SEQ-0005`, `slug` `seq-0005`, `title` `Aspirin route`, and `date` and `lastmod` `2026-10-19T17:42:05+02:00`
- **AND** `tools/orgsyndb new --sequence --md "Aspirin route"` exits 2 and creates nothing

### Requirement: index subcommand
`tools/orgsyndb index` SHALL take no arguments, and print to stdout the collection's index JSON (collection-index "Index data") on one line, as strict JSON with non-ASCII characters written as themselves, followed by a newline. It prints no step line, creates no file or directory, and exits 0. A configuration error is printed as `orgsyndb: error: <message>` with exit 1. Any argument is a usage error.

#### Scenario: Index of the demo
- **WHEN** a test runs `tools/orgsyndb -C <collection> index` on a copy of the demo collection without `build/`
- **THEN** it exits 0, stdout is one line that parses as JSON to the collection's index data, and the copy still has no `build/`

#### Scenario: No external tool
- **WHEN** a test runs `tools/orgsyndb -C <collection> index` on a copy of the demo collection, which has Org sources, with a `PATH` that holds only `python3`
- **THEN** it exits 0

#### Scenario: Arguments are refused
- **WHEN** a test runs `tools/orgsyndb -C <collection> index compounds`
- **THEN** it exits 2, and stderr contains the word `usage`

#### Scenario: Configuration error
- **WHEN** a test adds a declaration with `key = "funding"`, `type = "choice"`, `label = "Funding"` and `vocabulary = "storage"` to a copy of the test collection's `orgsyndb.toml` and runs `tools/orgsyndb -C <collection> index`
- **THEN** it exits 1, stderr begins with `orgsyndb: error:` and contains `storage`, and stdout is empty

#### Scenario: Registry unreachable
- **WHEN** a test points `ORGSYNDB_REGISTRY` at an address that does not answer and runs `tools/orgsyndb -C <collection> index` on a copy of the test collection without `build/`
- **THEN** it exits 1, stderr begins with `orgsyndb: error:` and names the address, and stdout is empty

### Requirement: manifest subcommand
`tools/orgsyndb manifest` SHALL take no arguments and print to stdout the collection's manifest JSON on one line, as strict JSON with non-ASCII characters written as themselves, followed by a newline. It prints no step line, writes no file and exits 0. It reads the Org procedures from the export a build leaves in `build/export/`: when `org/procedures/` holds an Org source and `build/export/` does not exist, it prints `orgsyndb: error:` and a message naming `build/export/` with exit 1, and so it does when a procedure or sequence file has no front matter it can read, naming the file. Any argument is a usage error.

The manifest is a JSON object with:

- `language`: the site's configured language;
- `procedures`: one table per procedure ID among the files of `build/export/` and `md/procedures/` whose names the validator's procedure file-name pattern accepts, ordered by ID, each with `id`; `source`, `org` when the variant the site publishes for that ID (localization "Choosing the variant to publish") is an export of an Org source, else `md`; `title`, that variant's title; `status`, that variant's `status`; `title_de`, the title of the ID's file tagged `de`, or `null` when it has none; `reaction_type`, the one element of that variant's `reaction_types`; `general`, whether the procedure has `scope`; `notebook` and `project`, that variant's values of the journal fields (procedure-fields "Journal fields"), each `null` when it sets none; and `entries`, the procedure's scope entries in file order, one per element of `scope` for a general procedure, else one made of the top-level `substrates` and `products`, each a table of `substrates`, a list of keys in file order, and `products`, a list of tables of `compound` and `yield_percent`, in file order;
- `sequences`: one table per sequence ID among the files of `md/sequences/` whose names the sequence file-name pattern accepts, ordered by ID, each with `id`; `title`, the title of the variant the site publishes; `title_de`, as for a procedure; `target`; and `steps`, a list of tables of `procedure` and `entry`, the number, counted from 1, of the entry the step names (synthesis-sequences "Sequence fields"), or `null` for a step of a specific procedure;
- `deleted`: the procedure and sequence IDs, in upper case and in order, that the base name of a path under `org/procedures`, `md/procedures` or `md/sequences` in the collection's git history begins with, read as `new` reads it (new subcommand), and that `procedures` and `sequences` do not name. Without usable git history, or in a shallow clone, it warns on stderr as `new` does.

It reads no registry and checks no value: it runs after a build that validated the collection.

#### Scenario: Manifest of the demo
- **WHEN** a test builds a copy of the demo collection and runs `tools/orgsyndb -C <collection> manifest`
- **THEN** it exits 0 and stdout is one line of JSON whose `language` is `de`, whose `procedures` are the demo's procedures in the order of their IDs, beginning with `OSDB-0001` to `OSDB-0009`, `OSDB-0001` with `source` `org` and `OSDB-0002` with `source` `md`, whose `OSDB-0009` has three entries, the first with the substrates `["4-acetylbiphenyl"]` and the products `[{"compound": "1-biphenyl-4-yl-ethanol", "yield_percent": 90}]`, and whose `SEQ-0002` has the steps `OSDB-0004` with entry `null` and `OSDB-0009` with entry `1`

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
- **WHEN** a test makes a temporary git repository holding a collection, commits `md/procedures/OSDB-0012-old.md` and `md/sequences/SEQ-0004-old.md`, deletes both in a second commit, and builds its manifest
- **THEN** its `deleted` is `["OSDB-0012", "SEQ-0004"]`

#### Scenario: Nothing deleted from the demo
- **WHEN** a test builds a copy of the demo collection and runs `tools/orgsyndb -C <collection> manifest`
- **THEN** its `deleted` is `[]`

#### Scenario: Journal fields in the manifest
- **WHEN** the same test reads the entry of `OSDB-0002`
- **THEN** its `notebook` is `AE-1/2` and its `project` `first-year-practical`
