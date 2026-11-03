## ADDED Requirements

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
- **WHEN** a test removes `vocabularies/projects.toml` from a copy of the test collection and runs `tools/orgsyndb -C <collection> index`
- **THEN** it exits 1, stderr begins with `orgsyndb: error:` and contains `projects`, and stdout is empty

## MODIFIED Requirements

### Requirement: Entry point conventions
`tools/orgsyndb` SHALL be an executable Python 3.14 program that uses only the standard library, besides importing `pipeline` and `validate` from its own directory. It has a `#!/usr/bin/env python3` shebang and is invoked as `orgsyndb [-C DIR] <subcommand> [options] [arguments]`, with the subcommands `export`, `validate`, `build`, `serve`, `pdf`, `new`, `init`, `clean`, `check-deps`, `index` and `help`. It follows these conventions:
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

### Requirement: Missing tools stop a subcommand before its first step
Each subcommand SHALL check, before its first step, every external tool it will need. A collection has Org sources when `org/procedures/` holds at least one entry that `validate.discover(org_root, ".org")` returns, with or without a problem attached, that is, an entry that the export either exports or reports (org-export "Org sources and their problems"). `pipeline.has_org_sources(org_root)` makes this decision from the entry names alone.
- `export`: `emacs` and `git` when the collection has Org sources, and no external tool otherwise. With Org sources, `git` is needed on every run, not only for the bootstrap, because every export checks the installed checkouts against their pins.
- `validate`: what `export` needs.
- `new`, `init`, `clean`, `check-deps`, `index` and `help`: no external tool. `git` is optional for `new`; without it `new` warns and scans the directories alone.
- `build`: what `export` needs, plus `hugo`.
- `serve`: what `build` needs.
- `pdf`: what `build` needs, plus `weasyprint`.

For a missing tool it prints `orgsyndb: error: <tool> not found; install it with your system's package manager` and exits 1 without starting any step. It never invokes `sudo`. A subcommand that works on a collection finds the collection before it checks the tools, so a missing or malformed collection is reported whatever tools are installed.

#### Scenario: Org sources by entry names
- **WHEN** a test calls `has_org_sources` on a directory that does not exist, an empty directory, a directory holding only `.gitkeep`, one holding only `notes.txt`, one holding only a subdirectory `nested/`, and one holding only `OSDB-0001-a.org`
- **THEN** it returns false, false, false, true, true and true

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

### Requirement: Pipeline helper module
`tools/pipeline.py` SHALL be a Python 3.14 module that uses only the standard library, besides importing `validate` from its own directory, and it annotates every callable. It has no command-line interface: `tools/orgsyndb` imports it, and the messages it prints name the program `orgsyndb`. It reads no Org source; of `org/procedures/` it reads only the entry names. The only Org files it reads are the documents of the application's `docs/` that it stages as help pages (site-help spec). It exposes the functions `slugify`, `next_id`, `org_timestamp`, `rfc3339`, `fill_template`, `has_org_sources`, `org_stems`, `org_error_reported`, `check_staging`, `recover_export`, `replace_export`, `new_procedure`, `pdf_jobs`, `install_pagefind`, `ensure_pagefind`, `hugo_overlay`, `help_slug`, `help_page`, `stage_help`, `index_data` and `remove_tree`.

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/pipeline.py` with `ast` and collects the top-level module names of every import
- **THEN** every name is in `sys.stdlib_module_names` or is `validate`

#### Scenario: No command-line interface
- **WHEN** a test reads `tools/pipeline.py`
- **THEN** it is not executable, does not begin with `#!`, and has no `if __name__ == "__main__":` block

#### Scenario: No Org reading in Python
- **WHEN** a test reads `tools/pipeline.py`, `tools/validate.py` and `tools/orgsyndb`
- **THEN** none contains `--org-root`, `export-plan`, `lint_org`, `cross_check` or `export_instants`
