# build-script Specification

## Purpose
Define `tools/orgsyndb`, its subcommands and conventions, the stdlib pipeline helper module, the optional pre-commit hook, the Caddyfile example and the ignore rules. Content and output paths are relative to the collection; `tools/`, `site/`, `templates/`, `.emacs-batch/` and `.tools/` belong to the application.

## Requirements

### Requirement: Entry point conventions
`tools/orgsyndb` SHALL be an executable Python 3.14 program that uses only the standard library, besides importing `pipeline` and `validate` from its own directory. It has a `#!/usr/bin/env python3` shebang and is invoked as `orgsyndb [-C DIR] <subcommand> [options] [arguments]`, with the subcommands `export`, `validate`, `build`, `serve`, `pdf`, `new`, `init`, `clean`, `check-deps` and `help`. It follows these conventions:
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
Each subcommand SHALL check, before its first step, every external tool it will need:
- `export`: `emacs` and `git`. `git` is needed on every run, not only for the bootstrap, because every export checks the installed checkouts against their pins.
- `validate` without arguments: what `export` needs.
- `validate` with arguments, `new`, `init`, `clean`, `check-deps` and `help`: no external tool. `git` is optional for `new`; without it `new` warns and scans the directories alone.
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

#### Scenario: validate with arguments needs only Python
- **WHEN** a test runs `tools/orgsyndb validate --vocabulary tests/fixtures/reaction_types.toml --static-dir tests/fixtures/static tests/fixtures/valid/md tests/fixtures/valid/export`, with the application as working directory and a `PATH` that holds only `python3`
- **THEN** it exits 0, and stderr contains no `not found`

### Requirement: validate subcommand
`tools/orgsyndb validate` SHALL behave in one of two ways:
- **Without arguments,** it runs `export`, then the validator as `validate.py --org-root org/procedures --static-dir static build/export md/procedures` with the collection as working directory, leaving out `--org-root org/procedures` and any content root whose directory does not exist. It prints the validator's stdout and stderr unchanged and exits with the validator's status.
- **With arguments,** it runs the validator with exactly those arguments, in the caller's working directory, without exporting and without a collection. Combined with `-C` or `--collection` it is a usage error, because the arguments would not be read relative to the named collection.

#### Scenario: Seeds validate
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> validate` on the demo collection
- **THEN** it exits 0, and no validator problem line is printed

#### Scenario: Invalid Markdown procedure
- **WHEN** an integration test copies `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` into the collection's `md/procedures/` and runs `tools/orgsyndb -C <collection> validate`
- **THEN** it exits 1, and stdout contains a line beginning `md/procedures/OSDB-0101-missing-title.md:title: error:`

#### Scenario: Arguments pass through to the validator
- **WHEN** a test runs `tools/orgsyndb validate --vocabulary tests/fixtures/reaction_types.toml --static-dir tests/fixtures/static tests/fixtures/invalid/missing-title` with the application as working directory
- **THEN** it exits 1, its stdout equals that of `tools/validate.py` run with the same arguments, and no `build/` directory was created or modified

#### Scenario: Arguments with a collection are refused
- **WHEN** a test runs `tools/orgsyndb -C <collection> validate md/procedures`, and the same with `--collection=<collection>`
- **THEN** each exits 2, stderr contains `-C`, and the collection's `build/` was not created

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
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` twice without changing any source
- **THEN** both runs exit 0, and `build/export/` holds identical bytes after each

### Requirement: serve subcommand
`tools/orgsyndb serve [--port N]` SHALL run `build`, bind `127.0.0.1:<N>`, print the line `serving http://127.0.0.1:<N>/ (Ctrl-C to stop)` once the port is bound, and then serve the collection's `public/` with the standard library's HTTP server until interrupted. Every response carries `Cache-Control: no-cache`, so a browser revalidates each file and shows a new build instead of cached pages of an earlier one. The default port is 8000; a port outside 1–65535 or not a number is a usage error. It never binds an address other than `127.0.0.1`.

#### Scenario: Site and search bundle are served
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> serve --port <free port>` in its own process group and waits for the `serving` line
- **THEN** HTTP GET requests to `/`, `/procedures/osdb-0001/`, `/pagefind/pagefind.js` and `/pagefind/pagefind-entry.json` on `127.0.0.1:<free port>` return status 200 with the header `Cache-Control: no-cache`
- **AND** the test then terminates the process group

#### Scenario: Port out of range
- **WHEN** a test runs `tools/orgsyndb -C <collection> serve --port 70000`
- **THEN** it exits 2, and the collection's `build/` was not created

### Requirement: pdf subcommand
`tools/orgsyndb pdf` SHALL run `build`, delete `pdf/`, and render the procedure pages through `pipeline.content_files`, `pipeline.pdf_jobs` and `pipeline.render_pdfs` on the collection's `build/export` and `md/procedures`. Rendering does the following:
- It renders one PDF per procedure content file. The output is `pdf/<content file stem>.pdf`, rendered from `public/procedures/<slug>/index.html`.
- It invokes `weasyprint --allowed-protocols file <html> <pdf>` with `PYTHONWARNINGS` set so that pyphen's `pkg_resources is deprecated` `UserWarning` is not shown.
- A job fails when WeasyPrint exits non-zero or writes a line beginning `ERROR:`. A failed job's output file is removed, and the remaining jobs still run.
- It prints one line per PDF, and exits 1 when any job failed.

`pipeline.pdf_jobs(files, public, pdf_dir)` computes the jobs from `(content path, front matter)` pairs, sorted by PDF name. When an HTML input is missing, it raises `ValueError` naming that path.

#### Scenario: Job naming
- **WHEN** a test calls `pdf_jobs` with `md/procedures/OSDB-0002-aspirin.md` and front matter `slug = "osdb-0002"`, with `public` and `pdf` as given directories
- **THEN** the single job's input is `<public>/procedures/osdb-0002/index.html` and its output is `<pdf>/OSDB-0002-aspirin.pdf`

#### Scenario: Missing page
- **WHEN** a test calls `pdf_jobs` with a content file whose page does not exist under `public`
- **THEN** it raises `ValueError`, whose message contains the expected HTML path

#### Scenario: One PDF per procedure, no stale files
- **WHEN** an integration test places `pdf/OSDB-0999-stale.pdf` in the collection copy and runs `tools/orgsyndb -C <collection> pdf`
- **THEN** it exits 0, `pdf/` holds exactly one file `<stem>.pdf` for each procedure content file `<stem>.md` in `build/export/` and `md/procedures/`, among them `OSDB-0001-salicylic-acid.pdf` and `OSDB-0002-aspirin.pdf`, and each file begins with `%PDF-`
- **AND** neither stdout nor stderr contains `pkg_resources`

#### Scenario: Remote stylesheet fails the job
- **WHEN** an integration test adds `<link rel="stylesheet" href="https://cdn.example.invalid/x.css">` to the application copy's procedure layout and runs `tools/orgsyndb -C <collection> pdf`
- **THEN** it exits 1, and stderr names the failing PDF

### Requirement: new subcommand
`tools/orgsyndb new [--md] [--ai-model ID] TITLE...` SHALL create one procedure stub in the collection, the same way as `tools/pipeline.py new --collection <collection> [--md] [--ai-model ID] TITLE`, and print the created file's path relative to the collection. The stub is created as follows:
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
- **WHEN** a test makes a temporary git repository holding a collection, commits `md/procedures/OSDB-0012-old.md`, deletes it in a second commit, and runs `pipeline.py new --collection <it> --md --now 2026-10-19T17:42:05+02:00 Test product`
- **THEN** the created file is `md/procedures/OSDB-0013-test-product.md`

#### Scenario: Collection in a subdirectory of a work tree
- **WHEN** a test makes a temporary git repository with a collection in its subdirectory `data/`, commits `data/md/procedures/OSDB-0012-old.md`, deletes it in a second commit, and runs `pipeline.py new --collection <repo>/data --md --now 2026-10-19T17:42:05+02:00 Test product`
- **THEN** the created file is `data/md/procedures/OSDB-0013-test-product.md`, and stderr contains no warning

#### Scenario: Shallow clone warns
- **WHEN** a test makes a temporary git repository holding a collection and two commits, clones it with `git clone --depth 1 file://…`, and runs `pipeline.py new --collection <clone> --md --now 2026-10-19T17:42:05+02:00 Test product`
- **THEN** it exits 0, creates the stub, and stderr contains `shallow`

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
- **WHEN** a test runs `pipeline.py new` as a subprocess with `LC_ALL=de_DE.UTF-8` and `LC_TIME=de_DE.UTF-8` and `--now 2026-10-19T17:42:05+02:00`
- **THEN** the created Org stub contains `#+CREATED: [2026-10-19 Mon 17:42:05]`

#### Scenario: Org stub
- **WHEN** a test runs `pipeline.py new --collection <temporary collection with empty trees> --now 2026-10-19T17:42:05+02:00 Salicylic acid`
- **THEN** the created file is `org/procedures/OSDB-0001-salicylic-acid.org`
- **AND** it contains `#+TITLE: Salicylic acid`, `#+CREATED: [2026-10-19 Mon 17:42:05]`, `#+LAST_MODIFIED: [2026-10-19 Mon 17:42:05]`, `#+AI_MODEL: none` and `#+HUGO_SLUG: osdb-0001`, and no `OSDB-0000` or `osdb-0000`
- **AND** `tools/validate.py --org-root` on its directory exits 0 and prints nothing to stdout

#### Scenario: Markdown stub with an AI model and a quoted title
- **WHEN** a test runs `pipeline.py new --md --ai-model example-model-1 --now 2026-10-19T17:42:05+02:00` with the title `Bob's "best" ester` in an empty temporary collection
- **THEN** the created file is `md/procedures/OSDB-0001-bob-s-best-ester.md`
- **AND** its front matter parses with `tomllib`, with `title` equal to `Bob's "best" ester`, `date` and `lastmod` equal to `2026-10-19T17:42:05+02:00`, `ai_model` equal to `example-model-1`, and `id` equal to `OSDB-0001`
- **AND** `tools/validate.py` on its directory exits 0 and prints nothing to stdout

#### Scenario: Human-authored Markdown stub
- **WHEN** a test runs `pipeline.py new --md --now 2026-10-19T17:42:05+02:00 Test product` in an empty temporary collection
- **THEN** the stub's front matter has no `ai_model` key

#### Scenario: Invalid AI model identifier
- **WHEN** a test runs `pipeline.py new --collection <empty temporary collection> --ai-model "two words" Test product`
- **THEN** it exits 2, stderr mentions `--ai-model`, and no file is created

### Requirement: clean subcommand
`tools/orgsyndb clean` SHALL remove the collection's `build/`, `public/` and `pdf/`. `clean --all` also removes the application's `.emacs-batch/` and `.tools/`. Both forms touch no other path, and both succeed when there is nothing to remove.

#### Scenario: Clean keeps sources and caches
- **WHEN** a test creates every one of those paths in a collection copy and an application copy and runs `tools/orgsyndb -C <collection> clean`
- **THEN** it exits 0, the collection's `build/`, `public/` and `pdf/` are gone, the application's `.emacs-batch/` and `.tools/` remain, and the collection's `org/`, `md/`, `static/` and `orgsyndb.toml` and the application's `site/` and `templates/` are unchanged

#### Scenario: Clean all, twice
- **WHEN** the same test then runs `tools/orgsyndb -C <collection> clean --all` twice
- **THEN** both runs exit 0, and the application's `.emacs-batch/` and `.tools/` are gone

### Requirement: check-deps subcommand
`tools/orgsyndb check-deps` SHALL run no external program other than the tools it probes. It reports the required tools `emacs`, `git`, `python3`, `hugo` and `weasyprint`, in that order, as follows:
- Each required tool gets a line beginning `ok ` or `missing `, followed by the tool's name.
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
- **THEN** it exits 0, and no line begins `missing ` or `sudo `

### Requirement: Pipeline helper module
`tools/pipeline.py` SHALL be an executable Python 3.14 file that uses only the standard library, besides importing `validate` from its own directory. It has a `#!/usr/bin/env python3` shebang and a PEP 723 block, and it annotates every callable. It exposes the functions `slugify`, `next_id`, `org_timestamp`, `rfc3339`, `export_instants`, `fill_template`, `recover_export`, `replace_export`, `pdf_jobs`, `install_pagefind` and `hugo_overlay`, the variable `PROG` naming the program in the messages the module prints (default `pipeline.py`), and the CLI subcommands `export-plan`, `recover-export`, `install-export`, `next-id`, `new`, `pdf` and `ensure-pagefind`. `next-id` and `new` take `--collection DIR`. The CLI exits 0 on success, 1 on failure and 2 on a usage error, and writes errors to stderr as `pipeline.py: error: <message>`.

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/pipeline.py` with `ast` and collects the top-level module names of every import
- **THEN** every name is in `sys.stdlib_module_names` or is `validate`

#### Scenario: Unknown CLI subcommand
- **WHEN** a test runs `tools/pipeline.py frobnicate`
- **THEN** it exits 2, and stderr is not empty

### Requirement: Optional pre-commit hook
`tools/hooks/pre-commit` SHALL be an executable POSIX `sh` script for a repository holding collections. It resolves its own path with `readlink -f`, so that it works both when `core.hooksPath` names `<app>/tools/hooks` and when it is symlinked into `.git/hooks/`. It runs `<app>/tools/orgsyndb -C <collection> validate` for the collection at the top level of the work tree, when `orgsyndb.toml` exists there, and for every directory whose `orgsyndb.toml` is in the index, each once, and exits with the status of the first that fails. When there is no such collection it prints a note to stderr and exits 0. No subcommand enables the hook or writes to `.git/hooks/` or `core.hooksPath`.

#### Scenario: Hook refuses an invalid commit
- **WHEN** an integration test makes the collection copy a git repository with `core.hooksPath` set to the application copy's absolute `tools/hooks`, adds `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` to `md/procedures/`, and runs `git commit`
- **THEN** the commit fails, and the new file is not committed

#### Scenario: Hook through a symlink accepts a valid commit
- **WHEN** an integration test makes the collection copy a git repository, symlinks `.git/hooks/pre-commit` to the application copy's hook, adds the demo procedures, and runs `git commit`
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

### Requirement: Caddyfile example
The file `deploy/Caddyfile.example` SHALL serve a copy of `public/` as static files with `file_server`, and sets the response header `Cache-Control: no-cache` with a `header` directive, explained in a comment. It uses a placeholder site address and a placeholder `root` path, explained in comments, and references no external resource and no user- or machine-specific identifier.

#### Scenario: Example is generic
- **WHEN** a test reads `deploy/Caddyfile.example`
- **THEN** it contains `file_server`, a `root` directive and the line `header Cache-Control "no-cache"`, and contains neither `/home/` nor a host name ending in `.local`, `.lan` or `.home.arpa`

#### Scenario: Example parses when Caddy is installed
- **WHEN** a test runs `caddy adapt --adapter caddyfile --config deploy/Caddyfile.example`, skipping when `caddy` is absent
- **THEN** it exits 0

### Requirement: Ignore rules
The application's `.gitignore` SHALL keep `__pycache__/` and `.pytest_cache/`, and it SHALL ignore `/.emacs-batch/` and `/.tools/`, anchored at the application root, and `/site/.hugo_build.lock` and `/site/resources/`, which builds before this change left behind. The demo collection's `.gitignore` ignores its `/build/`, `/public/` and `/pdf/`.

#### Scenario: Generated paths ignored, sources not
- **WHEN** a test runs `git check-ignore` in the application on `examples/demo/build/export/x.md`, `examples/demo/public/index.html`, `examples/demo/pdf/x.pdf`, `.emacs-batch/elpa`, `.tools/pagefind-1.5.2/pagefind`, `site/.hugo_build.lock` and `site/resources/_gen/x`, skipping when `git` is absent
- **THEN** each path is reported as ignored
- **AND** `examples/demo/org/procedures/OSDB-0001-salicylic-acid.org`, `examples/demo/md/procedures/OSDB-0002-aspirin.md`, `examples/demo/static/structures/osdb-0003.svg`, `site/hugo.toml` and `tests/fixtures/export/build/x` are not
