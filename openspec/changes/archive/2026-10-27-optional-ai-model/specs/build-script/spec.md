## MODIFIED Requirements

### Requirement: new subcommand
`tools/orgsyndb new [--md] TITLE...` SHALL create one procedure stub in the collection with `pipeline.new_procedure(collection, words, md, now, language)`, and print the created file's path relative to the collection. `new_procedure` is the only place that checks the title and the `--lang` value; a bad value raises `pipeline.UsageError`, and the program exits 2. The stub is created as follows:
- The title is the words of `TITLE...` joined by single spaces and trimmed. It must not be empty or contain a newline.
- The file is `org/procedures/<ID>-<slug>.org`, or `md/procedures/<ID>-<slug>.md` with `--md`. It is copied from the application's `templates/procedure.org` or `templates/procedure.md` and filled by `pipeline.fill_template`.
- It is created with exclusive creation, so an existing file is never overwritten.
- `ID` is `pipeline.next_id` over the candidate names, and `slug` is `pipeline.slugify(title)`.
- The stub records no AI model. An Org stub has no `#+AI_MODEL` line, even when the template has one, and a Markdown stub has no `ai_model` key; the Markdown template's commented-out `ai_model` line stays commented out.

The candidate names for `next_id` are:
- the top-level entry names of the collection's `org/procedures/`, `md/procedures/` and `build/export/`;
- the base names of every path that `git -C <collection> log --all --no-renames --format= --name-only -- org/procedures md/procedures` reports.

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
