## MODIFIED Requirements

### Requirement: Missing tools stop a subcommand before its first step
Each subcommand SHALL check, before its first step, every external tool it will need. A collection has Org sources when `org/procedures/` holds at least one entry that `validate.discover(org_root, ".org")` returns, with or without a problem attached, that is, an entry that the export either exports or reports (org-export "Org sources and their problems"). `pipeline.has_org_sources(org_root)` makes this decision from the entry names alone.
- `export`: `emacs` and `git` when the collection has Org sources, and no external tool otherwise. With Org sources, `git` is needed on every run, not only for the bootstrap, because every export checks the installed checkouts against their pins.
- `validate`: what `export` needs.
- `new`, `init`, `clean`, `check-deps` and `help`: no external tool. `git` is optional for `new`; without it `new` warns and scans the directories alone.
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

### Requirement: check-deps subcommand
`tools/orgsyndb check-deps` SHALL run no external program other than the tools it probes. It reports the required tools `python3`, `hugo` and `weasyprint`, in that order, as follows:
- Each required tool gets a line beginning `ok ` or `missing `, followed by the tool's name and nothing else.
- Lines beginning `optional ` report `emacs` and `git`, each saying whether it is installed and that it is only for Org procedures, and then `caddy`.
- Lines beginning `auto ` report Pagefind 1.5.2 and ox-hugo/tomelr, each saying whether it is cached or will be fetched on first use.
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
