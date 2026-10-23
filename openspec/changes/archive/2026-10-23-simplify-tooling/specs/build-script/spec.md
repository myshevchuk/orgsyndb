## MODIFIED Requirements

### Requirement: Missing tools stop a subcommand before its first step
Each subcommand SHALL check, before its first step, every external tool it will need:
- `export`: `emacs` and `git`. `git` is needed on every run, not only for the bootstrap, because every export checks the installed checkouts against their pins.
- `validate`: what `export` needs.
- `new`, `init`, `clean`, `check-deps` and `help`: no external tool. `git` is optional for `new`; without it `new` warns and scans the directories alone.
- `build`: what `export` needs, plus `hugo`.
- `serve`: what `build` needs.
- `pdf`: what `build` needs, plus `weasyprint`.

For a missing tool it prints `orgsyndb: error: <tool> not found; install it with: sudo dnf install <package>` and exits 1 without starting any step. It never invokes `sudo`. A subcommand that works on a collection finds the collection before it checks the tools, so a missing or malformed collection is reported whatever tools are installed.

#### Scenario: Hugo missing
- **WHEN** a test runs `tools/orgsyndb -C <collection> build` with a `PATH` that holds `python3`, `emacs`, `git` and a recording fake `sudo`, but not `hugo`
- **THEN** it exits 1, stderr contains `sudo dnf install hugo`, the collection's `build/` was not created, and the fake `sudo` was never invoked

#### Scenario: git missing although ox-hugo is installed
- **WHEN** a test runs `tools/orgsyndb -C <collection> export` in an application copy whose `.emacs-batch/` is linked from a bootstrapped checkout, with a `PATH` that holds `python3`, `emacs` and a recording fake `sudo`, but not `git`
- **THEN** it exits 1, stderr contains `sudo dnf install git`, the collection's `build/` was not created, and the fake `sudo` was never invoked

#### Scenario: Collection error comes before missing tools
- **WHEN** a test runs `tools/orgsyndb -C <directory without orgsyndb.toml> build` with a `PATH` that holds only `python3` and a recording fake `sudo`
- **THEN** it exits 1, stderr contains `orgsyndb.toml` and no `not found`, and the fake `sudo` was never invoked

### Requirement: validate subcommand
`tools/orgsyndb validate` SHALL take no arguments. It runs `export`, then the validator with the arguments `--org-root org/procedures --static-dir static build/export md/procedures` and the collection as working directory, leaving out `--org-root org/procedures` and any content root whose directory does not exist. It prints the validator's stdout and stderr unchanged and exits with the validator's status. Any argument is a usage error; other directories are validated by running `tools/validate.py` directly.

#### Scenario: Seeds validate
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> validate` on the demo collection
- **THEN** it exits 0, and no validator problem line is printed

#### Scenario: Invalid Markdown procedure
- **WHEN** an integration test copies `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` into the collection's `md/procedures/` and runs `tools/orgsyndb -C <collection> validate`
- **THEN** it exits 1, and stdout contains a line beginning `md/procedures/OSDB-0101-missing-title.md:title: error:`

#### Scenario: Arguments are refused
- **WHEN** a test runs `tools/orgsyndb -C <collection> validate md/procedures`, and the same with `--collection=<collection>`
- **THEN** each exits 2, stderr contains `validate.py`, and the collection's `build/` was not created

### Requirement: new subcommand
`tools/orgsyndb new [--md] [--ai-model ID] TITLE...` SHALL create one procedure stub in the collection with `pipeline.new_procedure(collection, words, md, ai_model, now, language)`, and print the created file's path relative to the collection. `new_procedure` is the only place that checks the title and the `--ai-model` and `--lang` values; a bad value raises `pipeline.UsageError`, and the program exits 2. The stub is created as follows:
- The title is the words of `TITLE...` joined by single spaces and trimmed. It must not be empty or contain a newline.
- The file is `org/procedures/<ID>-<slug>.org`, or `md/procedures/<ID>-<slug>.md` with `--md`. It is copied from the application's `templates/procedure.org` or `templates/procedure.md` and filled by `pipeline.fill_template`.
- It is created with exclusive creation, so an existing file is never overwritten.
- `ID` is `pipeline.next_id` over the candidate names, and `slug` is `pipeline.slugify(title)`.
- The `--ai-model` value must match `^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$`.

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
- **AND** it contains `#+TITLE: Salicylic acid`, `#+CREATED: [2026-10-19 Mon 17:42:05]`, `#+LAST_MODIFIED: [2026-10-19 Mon 17:42:05]`, `#+AI_MODEL: none` and `#+HUGO_SLUG: osdb-0001`, and no `OSDB-0000` or `osdb-0000`
- **AND** `tools/validate.py --org-root` on its directory exits 0 and prints nothing to stdout

#### Scenario: Markdown stub with an AI model and a quoted title
- **WHEN** a test calls `new_procedure` in an empty temporary collection for the Markdown title `Bob's "best" ester`, with `ai_model` `example-model-1`, at `2026-10-19T17:42:05+02:00`
- **THEN** the created file is `md/procedures/OSDB-0001-bob-s-best-ester.md`
- **AND** its front matter parses with `tomllib`, with `title` equal to `Bob's "best" ester`, `date` and `lastmod` equal to `2026-10-19T17:42:05+02:00`, `ai_model` equal to `example-model-1`, and `id` equal to `OSDB-0001`
- **AND** `tools/validate.py` on its directory exits 0 and prints nothing to stdout

#### Scenario: Human-authored Markdown stub
- **WHEN** a test calls `new_procedure` in an empty temporary collection for the Markdown title `Test product` at `2026-10-19T17:42:05+02:00`, without `ai_model`
- **THEN** the stub's front matter has no `ai_model` key

#### Scenario: Invalid AI model identifier
- **WHEN** a test calls `new_procedure` in an empty temporary collection for `Test product` with `ai_model` `two words`
- **THEN** it raises `pipeline.UsageError` whose message mentions `--ai-model`, and no file is created

### Requirement: check-deps subcommand
`tools/orgsyndb check-deps` SHALL run no external program other than the tools it probes. It reports the required tools `emacs`, `git`, `python3`, `hugo` and `weasyprint`, in that order, as follows:
- Each required tool gets a line beginning `ok ` or `missing `, followed by the tool's name and nothing else.
- A line beginning `optional ` reports `caddy`.
- Lines beginning `auto ` report Pagefind 1.5.2 and ox-hugo/tomelr, each saying whether it is cached or will be fetched on first use.
- When any required tool is missing, the last line is exactly `sudo dnf install <packages>`, listing the Fedora packages of the missing tools in that order (`emacs`, `git`, `python3`, `hugo`, `weasyprint`), and the exit status is 1. Otherwise the exit status is 0.

It never installs anything and never invokes `sudo`.

#### Scenario: Two tools missing
- **WHEN** a test runs `tools/orgsyndb check-deps` with a `PATH` that holds only `python3`, `emacs`, `git` and a recording fake `sudo`
- **THEN** it exits 1, stdout has a line beginning `missing hugo` and one beginning `missing weasyprint`, and the last line is exactly `sudo dnf install hugo weasyprint`
- **AND** the fake `sudo` was never invoked

#### Scenario: Nothing missing
- **WHEN** a test runs `tools/orgsyndb check-deps` with a `PATH` holding all five required tools (real or stub executables)
- **THEN** it exits 0, no line begins `missing ` or `sudo `, and each `ok ` line ends with its tool's name

### Requirement: Pipeline helper module
`tools/pipeline.py` SHALL be a Python 3.14 module that uses only the standard library, besides importing `validate` from its own directory, and it annotates every callable. It has no command-line interface: `tools/orgsyndb` imports it, and the messages it prints name the program `orgsyndb`. It exposes the functions `slugify`, `next_id`, `org_timestamp`, `rfc3339`, `export_instants`, `fill_template`, `write_export_plan`, `recover_export`, `replace_export`, `new_procedure`, `pdf_jobs`, `install_pagefind`, `ensure_pagefind`, `hugo_overlay` and `remove_tree`.

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/pipeline.py` with `ast` and collects the top-level module names of every import
- **THEN** every name is in `sys.stdlib_module_names` or is `validate`

#### Scenario: No command-line interface
- **WHEN** a test reads `tools/pipeline.py`
- **THEN** it is not executable, does not begin with `#!`, and has no `if __name__ == "__main__":` block

### Requirement: Ignore rules
The application's `.gitignore` SHALL keep `__pycache__/` and `.pytest_cache/`, and it SHALL ignore `/.emacs-batch/` and `/.tools/`, anchored at the application root, and nothing else; build output belongs to collections. The demo collection's `.gitignore` ignores its `/build/`, `/public/` and `/pdf/`.

#### Scenario: Generated paths ignored, sources not
- **WHEN** a test runs `git check-ignore` in the application on `examples/demo/build/export/x.md`, `examples/demo/public/index.html`, `examples/demo/pdf/x.pdf`, `.emacs-batch/elpa` and `.tools/pagefind-1.5.2/pagefind`, skipping when `git` is absent
- **THEN** each path is reported as ignored
- **AND** `examples/demo/org/procedures/OSDB-0001-salicylic-acid.org`, `examples/demo/md/procedures/OSDB-0002-aspirin.md`, `examples/demo/static/structures/osdb-0003.svg`, `site/hugo.toml`, `site/.hugo_build.lock`, `build/x` and `tests/fixtures/export/build/x` are not

