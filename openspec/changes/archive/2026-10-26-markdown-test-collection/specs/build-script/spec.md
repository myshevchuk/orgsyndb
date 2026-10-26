## MODIFIED Requirements

### Requirement: Missing tools stop a subcommand before its first step
Each subcommand SHALL check, before its first step, every external tool it will need. A collection has Org sources when `org/procedures/` holds at least one entry that `validate.discover(org_root, ".org")` returns with no problem attached, the files the validator examines as Org procedures.
- `export`: `emacs` and `git` when the collection has Org sources, and no external tool otherwise. With Org sources, `git` is needed on every run, not only for the bootstrap, because every export checks the installed checkouts against their pins.
- `validate`: what `export` needs.
- `new`, `init`, `clean`, `check-deps` and `help`: no external tool. `git` is optional for `new`; without it `new` warns and scans the directories alone.
- `build`: what `export` needs, plus `hugo`.
- `serve`: what `build` needs.
- `pdf`: what `build` needs, plus `weasyprint`.

For a missing tool it prints `orgsyndb: error: <tool> not found; install it with: sudo dnf install <package>` and exits 1 without starting any step. It never invokes `sudo`. A subcommand that works on a collection finds the collection before it checks the tools, so a missing or malformed collection is reported whatever tools are installed.

#### Scenario: Hugo missing
- **WHEN** a test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection `tests/fixtures/collection/`, which has no Org sources, with a `PATH` that holds `python3` and a recording fake `sudo`, but not `hugo`
- **THEN** it exits 1, stderr contains `sudo dnf install hugo`, the collection's `build/` was not created, and the fake `sudo` was never invoked

#### Scenario: git missing although ox-hugo is installed
- **WHEN** a test runs `tools/orgsyndb -C <collection> export` on a copy of the demo collection in an application copy whose `.emacs-batch/` is linked from a bootstrapped checkout, with a `PATH` that holds `python3`, `emacs` (real or stub executable) and a recording fake `sudo`, but not `git`
- **THEN** it exits 1, stderr contains `sudo dnf install git`, the collection's `build/` was not created, and the fake `sudo` was never invoked

#### Scenario: Emacs missing with Org sources
- **WHEN** a test runs `tools/orgsyndb -C <collection> build` on the demo collection with a `PATH` that holds `python3`, `git`, `hugo` and a recording fake `sudo`, but not `emacs`
- **THEN** it exits 1, stderr contains `sudo dnf install emacs`, the collection's `build/` was not created, and the fake `sudo` was never invoked

#### Scenario: Markdown-only collection builds without Emacs and git
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the test collection `tests/fixtures/collection/` with a `PATH` that holds `python3` and `hugo` but neither `emacs` nor `git`, skipping when Hugo or the Pagefind cache is absent
- **THEN** it exits 0, and `public/index.html` and `public/procedures/osdb-0002/index.html` exist

#### Scenario: Collection error comes before missing tools
- **WHEN** a test runs `tools/orgsyndb -C <directory without orgsyndb.toml> build` with a `PATH` that holds only `python3` and a recording fake `sudo`
- **THEN** it exits 1, stderr contains `orgsyndb.toml` and no `not found`, and the fake `sudo` was never invoked

### Requirement: validate subcommand
`tools/orgsyndb validate` SHALL take no arguments. It runs `export`, then the validator with the arguments `--org-root org/procedures --static-dir static build/export md/procedures` and the collection as working directory, leaving out `--org-root org/procedures` and any content root whose directory does not exist. It prints the validator's stdout and stderr unchanged and exits with the validator's status. Any argument is a usage error; other directories are validated by running `tools/validate.py` directly.

#### Scenario: Seeds validate
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> validate` on a copy of the test collection `tests/fixtures/collection/`
- **THEN** it exits 0, and no validator problem line is printed

#### Scenario: Invalid Markdown procedure
- **WHEN** an integration test copies `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` into the collection's `md/procedures/` and runs `tools/orgsyndb -C <collection> validate`
- **THEN** it exits 1, and stdout contains a line beginning `md/procedures/OSDB-0101-missing-title.md:title: error:`

#### Scenario: Arguments are refused
- **WHEN** a test runs `tools/orgsyndb -C <collection> validate md/procedures`, and the same with `--collection=<collection>`
- **THEN** each exits 2, stderr contains `validate.py`, and the collection's `build/` was not created

### Requirement: build subcommand
`tools/orgsyndb build` SHALL perform these steps in order:
1. Run `export`.
2. Validate as `validate` does without arguments, stopping with exit 1 on any validation error while tolerating warnings.
3. Remove `public/`, and write the Hugo overlay `build/hugo-config/_default/hugo.toml` (site-build "Hugo configuration").
4. Run `hugo --source <app>/site --configDir <collection>/build/hugo-config --minify --quiet --noBuildLock`.
5. Obtain the Pagefind binary, and run it with `--site <collection>/public --quiet`.

A failing step stops the command with exit 1.

#### Scenario: Validation error stops the build before Hugo
- **WHEN** an integration test builds once, adds an invalid Markdown procedure to `md/procedures/`, and builds again
- **THEN** the second build exits 1, and `public/` still holds the first build's output

#### Scenario: Second build without changes
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` twice on a copy of the demo collection without changing any source
- **THEN** both runs exit 0, and `build/export/` is not empty and holds identical bytes after each

### Requirement: Optional pre-commit hook
`tools/hooks/pre-commit` SHALL be an executable POSIX `sh` script for a repository holding collections. It resolves its own path with `readlink -f`, so that it works both when `core.hooksPath` names `<app>/tools/hooks` and when it is symlinked into `.git/hooks/`. It runs `<app>/tools/orgsyndb -C <collection> validate` for the collection at the top level of the work tree, when `orgsyndb.toml` exists there, and for every directory whose `orgsyndb.toml` is in the index, each once, and exits with the status of the first that fails. When there is no such collection it prints a note to stderr and exits 0. No subcommand enables the hook or writes to `.git/hooks/` or `core.hooksPath`.

#### Scenario: Hook refuses an invalid commit
- **WHEN** an integration test makes the collection copy a git repository with `core.hooksPath` set to the application copy's absolute `tools/hooks`, adds `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` to `md/procedures/`, and runs `git commit`
- **THEN** the commit fails, and the new file is not committed

#### Scenario: Hook through a symlink accepts a valid commit
- **WHEN** an integration test makes the collection copy, a copy of the test collection `tests/fixtures/collection/`, a git repository, symlinks `.git/hooks/pre-commit` to the application copy's hook, adds every file of the collection copy, and runs `git commit`
- **THEN** the commit succeeds

#### Scenario: Hook validates a collection in a subdirectory
- **WHEN** an integration test makes the directory holding the collection copy a git repository with `core.hooksPath` set to the application copy's absolute `tools/hooks`, adds the collection copy, then adds `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` to its `md/procedures/` and runs `git commit`
- **THEN** the commit fails, and the new file is not committed

#### Scenario: Hook without a collection lets the commit through
- **WHEN** a test makes an empty temporary directory a git repository with `core.hooksPath` set to the application's absolute `tools/hooks`, adds a file and runs `git commit`
- **THEN** the commit succeeds, and stderr contains `no OrgSynDB collection`

#### Scenario: Nothing enables the hook
- **WHEN** a test searches `tools/orgsyndb` and `tools/pipeline.py` for `hooksPath` and `.git/hooks`
- **THEN** neither string is found

### Requirement: check-deps subcommand
`tools/orgsyndb check-deps` SHALL run no external program other than the tools it probes. It reports the required tools `python3`, `hugo` and `weasyprint`, in that order, as follows:
- Each required tool gets a line beginning `ok ` or `missing `, followed by the tool's name and nothing else.
- Lines beginning `optional ` report `emacs` and `git`, each saying whether it is installed and that it is only for Org procedures, and then `caddy`.
- Lines beginning `auto ` report Pagefind 1.5.2 and ox-hugo/tomelr, each saying whether it is cached or will be fetched on first use.
- When any required tool is missing, the last line is exactly `sudo dnf install <packages>`, listing the Fedora packages of the missing required tools in that order (`python3`, `hugo`, `weasyprint`), and the exit status is 1. Otherwise the exit status is 0.

It never installs anything and never invokes `sudo`.

#### Scenario: Two tools missing
- **WHEN** a test runs `tools/orgsyndb check-deps` with a `PATH` that holds only `python3`, `emacs` and `git` (real or stub executables) and a recording fake `sudo`
- **THEN** it exits 1, stdout has a line beginning `missing hugo` and one beginning `missing weasyprint`, and the last line is exactly `sudo dnf install hugo weasyprint`
- **AND** the fake `sudo` was never invoked

#### Scenario: Nothing missing
- **WHEN** a test runs `tools/orgsyndb check-deps` with a `PATH` holding the three required tools (real or stub executables) and neither `emacs` nor `git`
- **THEN** it exits 0, no line begins `missing ` or `sudo `, and each `ok ` line ends with its tool's name
- **AND** stdout has the lines `optional emacs (not installed; only for Org procedures)` and `optional git (not installed; only for Org procedures)`
