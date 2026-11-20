## MODIFIED Requirements

### Requirement: Entry point conventions
`tools/orgsyndb` SHALL be an executable Python program that uses only the standard library, besides importing `pipeline` and `validate` from its own directory. It has a `#!/usr/bin/env python3` shebang and is invoked as `orgsyndb [-C DIR] <subcommand> [options] [arguments]`, with the subcommands `export`, `validate`, `build`, `serve`, `pdf`, `new`, `init`, `clean`, `check-deps`, `index`, `manifest` and `help`. It follows these conventions:
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

### Requirement: check-deps subcommand
`tools/orgsyndb check-deps` SHALL run no external program other than the tools it probes. It reports the required tools `python3`, `hugo` and `weasyprint`, in that order, as follows:
- Each required tool gets a line beginning `ok ` or `missing `, followed by the tool's name and nothing else.
- Lines beginning `optional ` report `emacs` and `git`, each saying whether it is installed and that it is only for Org procedures, and then `caddy`.
- Lines beginning `auto ` report Pagefind and ox-hugo/tomelr, each saying whether it is cached or will be fetched on first use.
- When any required tool is missing, the last line is exactly `install with your package manager: <tools>`, listing the missing required tools, separated by single spaces, in that order (`python3`, `hugo`, `weasyprint`), and the exit status is 1. Otherwise the exit status is 0.

It never installs anything and never invokes `sudo`.

#### Scenario: Two tools missing
- **WHEN** a test runs `tools/orgsyndb check-deps` with a `PATH` that holds only `python3`, `emacs` and `git` (real or stub executables) and a recording fake `sudo`
- **THEN** it exits 1, stdout has a line beginning `missing hugo` and one beginning `missing weasyprint`, and the last line is exactly `install with your package manager: hugo weasyprint`
- **AND** the fake `sudo` was never invoked

#### Scenario: Nothing missing
- **WHEN** a test runs `tools/orgsyndb check-deps` with a `PATH` holding the three required tools (real or stub executables) and neither `emacs` nor `git`
- **THEN** it exits 0, no line begins `missing ` or `install `, and each `ok ` line ends with its tool's name
- **AND** stdout has the lines `optional emacs (not installed; only for Org procedures)` and `optional git (not installed; only for Org procedures)`

### Requirement: Pipeline helper module
`tools/pipeline.py` SHALL be a Python module that uses only the standard library, besides importing `validate` from its own directory, and it annotates every callable. It has no command-line interface: `tools/orgsyndb` imports it, and the messages it prints name the program `orgsyndb`. It reads no Org source; of `org/procedures/` it reads only the entry names. The only Org files it reads are the documents of the application's `docs/` that it stages as help pages (site-help spec). It exposes the functions `slugify`, `next_id`, `org_timestamp`, `rfc3339`, `fill_template`, `has_org_sources`, `org_stems`, `org_error_reported`, `check_staging`, `recover_export`, `replace_export`, `new_procedure`, `pdf_jobs`, `install_pagefind`, `ensure_pagefind`, `hugo_overlay`, `help_slug`, `help_page`, `stage_help`, `index_data` and `remove_tree`.

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/pipeline.py` with `ast` and collects the top-level module names of every import
- **THEN** every name is in `sys.stdlib_module_names` or is `validate`

#### Scenario: No command-line interface
- **WHEN** a test reads `tools/pipeline.py`
- **THEN** it is not executable, does not begin with `#!`, and has no `if __name__ == "__main__":` block

#### Scenario: No Org reading in Python
- **WHEN** a test reads `tools/pipeline.py`, `tools/validate.py` and `tools/orgsyndb`
- **THEN** none contains `--org-root`, `export-plan`, `lint_org`, `cross_check` or `export_instants`

### Requirement: Ignore rules
The application's `.gitignore` SHALL keep `__pycache__/` and `.pytest_cache/`, and it SHALL ignore `/.emacs-batch/` and `/.tools/`, anchored at the application root, and nothing else; build output belongs to collections. The demo collection's `.gitignore` ignores its `/build/`, `/public/` and `/pdf/`.

#### Scenario: Generated paths ignored, sources not
- **WHEN** a test runs `git check-ignore` in the application on `examples/demo/build/export/x.md`, `examples/demo/public/index.html`, `examples/demo/pdf/x.pdf`, `.emacs-batch/elpa` and `.tools/pagefind/pagefind`, skipping when `git` is absent
- **THEN** each path is reported as ignored
- **AND** `examples/demo/org/procedures/OSDB-0001-salicylic-acid.org`, `examples/demo/md/procedures/OSDB-0002-aspirin.md`, `examples/demo/static/structures/aryl-ketone-reduction.svg`, `webapp/demo/substances/isopentyl-acetate/structure.svg`, `site/hugo.toml`, `site/.hugo_build.lock`, `build/x` and `tests/fixtures/export/build/x` are not
