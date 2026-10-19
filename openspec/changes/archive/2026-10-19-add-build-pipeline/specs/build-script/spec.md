## ADDED Requirements

<!-- "Integration test" is defined in the org-export spec. A "fish test"
runs tools/build.fish with the fish found on PATH and skips when fish is
absent. -->

### Requirement: Entry point conventions
`tools/build.fish` SHALL be an executable fish script, invoked as `build.fish <subcommand> [options] [arguments]`, with the subcommands `export`, `validate`, `build`, `serve`, `pdf`, `new`, `clean`, `check-deps` and `help`. It follows these conventions:
- It locates the repository from its own resolved path, following symlinks, so it works from any working directory. It refuses to run, with exit 1, unless `<repo>/tools/build.fish` and `<repo>/site/hugo.toml` exist.
- It exports `TZ=Europe/Berlin` and `LC_TIME=C` to every child process.
- It prints a line beginning `==> ` before each step, and writes errors to stderr as `build.fish: error: <message>`.
- It exits 0 on success, 1 on failure, and 2 on a usage error. A usage error is a missing or unknown subcommand, or an unknown option, and its usage text goes to stderr. `help`, `-h` and `--help` print the usage text to stdout and exit 0.
- It deletes nothing outside `build/`, `public/`, `pdf/`, `site/.hugo_build.lock`, `site/resources/`, `.emacs-batch/` and `.tools/` within the repository.
- It passes `fish --no-execute` and `fish_indent --check`.

#### Scenario: Unknown subcommand
- **WHEN** a fish test runs `tools/build.fish frobnicate` from a temporary working directory
- **THEN** it exits 2, and stderr contains `frobnicate` and the word `usage`

#### Scenario: No subcommand
- **WHEN** a fish test runs `tools/build.fish` with no arguments
- **THEN** it exits 2, and stderr contains the word `usage`

#### Scenario: Help
- **WHEN** a fish test runs `tools/build.fish help`
- **THEN** it exits 0, and stdout names every subcommand

#### Scenario: Syntax and formatting
- **WHEN** a fish test runs `fish --no-execute` and `fish_indent --check` on `tools/build.fish` and `tools/hooks/pre-commit`
- **THEN** every run exits 0

#### Scenario: Invoked through a symlink
- **WHEN** a fish test creates a symlink to `tools/build.fish` in a temporary directory and runs `<symlink> help` from that directory
- **THEN** it exits 0

### Requirement: Missing tools stop a subcommand before its first step
Each subcommand SHALL check, before its first step, every external tool it will need:
- `export`: `emacs`, `git` and `python3`. `git` is needed on every run, not only for the bootstrap, because every export checks the installed checkouts against their pins.
- `validate` without arguments: what `export` needs.
- `validate` with arguments: `python3` only.
- `build`: what `export` needs, plus `hugo`.
- `serve`: what `build` needs.
- `pdf`: what `build` needs, plus `weasyprint`.
- `new`: `python3`. `git` is optional; without it `new` warns and scans the directories alone.
- `clean`, `check-deps` and `help`: no external tool.

For a missing tool it prints `build.fish: error: <tool> not found; install it with: sudo dnf install <package>` and exits 1 without starting any step. It never invokes `sudo`.

#### Scenario: Hugo missing
- **WHEN** a fish test runs `tools/build.fish build` in a temporary repository copy with a `PATH` that holds `fish`, `python3`, `emacs`, `git` and a recording fake `sudo`, but not `hugo`
- **THEN** it exits 1, stderr contains `sudo dnf install hugo`, `build/` was not created, and the fake `sudo` was never invoked

#### Scenario: git missing although ox-hugo is installed
- **WHEN** a fish test runs `tools/build.fish export` in a temporary repository copy whose `.emacs-batch/` is linked from a bootstrapped repository, with a `PATH` that holds `fish`, `python3`, `emacs` and a recording fake `sudo`, but not `git`
- **THEN** it exits 1, stderr contains `sudo dnf install git`, `build/` was not created, and the fake `sudo` was never invoked

#### Scenario: validate with arguments needs only Python
- **WHEN** a fish test runs `tools/build.fish validate --vocabulary tests/fixtures/reaction_types.toml --static-dir tests/fixtures/static tests/fixtures/valid/md tests/fixtures/valid/export`, with the repository as working directory and a `PATH` that holds only `fish` and `python3`
- **THEN** it exits 0, and stderr contains no `not found`

### Requirement: validate subcommand
`tools/build.fish validate` SHALL behave in one of two ways:
- **Without arguments,** it runs `export`, then `tools/validate.py --org-root org/procedures build/export md/procedures` with the repository as working directory. It prints the validator's stdout and stderr unchanged and exits with the validator's status.
- **With arguments,** it runs `tools/validate.py` with exactly those arguments, in the caller's working directory and without exporting.

#### Scenario: Seeds validate
- **WHEN** an integration test runs `tools/build.fish validate` on the seed procedures
- **THEN** it exits 0, and no validator problem line is printed

#### Scenario: Invalid Markdown procedure
- **WHEN** an integration test copies `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` into `md/procedures/` and runs `tools/build.fish validate`
- **THEN** it exits 1, and stdout contains a line beginning `md/procedures/OSDB-0101-missing-title.md:title: error:`

#### Scenario: Arguments pass through to the validator
- **WHEN** a fish test runs `tools/build.fish validate --vocabulary tests/fixtures/reaction_types.toml --static-dir tests/fixtures/static tests/fixtures/invalid/missing-title` with the repository as working directory
- **THEN** it exits 1, its stdout equals that of `tools/validate.py` run with the same arguments, and `build/export/` was not created or modified

### Requirement: build subcommand
`tools/build.fish build` SHALL perform these steps in order:
1. Run `export`.
2. Validate as `validate` does without arguments, stopping with exit 1 on any validation error while tolerating warnings.
3. Remove `public/`.
4. Run `hugo --source <repo>/site --minify`.
5. Obtain the Pagefind binary, and run it with `--site <repo>/public`.

A failing step stops the command with exit 1.

#### Scenario: Validation error stops the build before Hugo
- **WHEN** an integration test builds once, adds an invalid Markdown procedure to `md/procedures/`, and builds again
- **THEN** the second build exits 1, and `public/` still holds the first build's output

#### Scenario: Second build without changes
- **WHEN** an integration test runs `tools/build.fish build` twice without changing any source
- **THEN** both runs exit 0, and `build/export/` holds identical bytes after each

### Requirement: serve subcommand
`tools/build.fish serve [--port N]` SHALL run `build`, print the line `serving http://127.0.0.1:<N>/ (Ctrl-C to stop)`, and then serve `public/` with `python3 -m http.server --bind 127.0.0.1 --directory <repo>/public <N>` until interrupted. The default port is 8000. It never binds an address other than `127.0.0.1`.

#### Scenario: Site and search bundle are served
- **WHEN** an integration test runs `tools/build.fish serve --port <free port>` in its own process group and waits for the `serving` line
- **THEN** HTTP GET requests to `/`, `/procedures/osdb-0001/`, `/pagefind/pagefind.js` and `/pagefind/pagefind-entry.json` on `127.0.0.1:<free port>` return status 200
- **AND** the test then terminates the process group

### Requirement: pdf subcommand
`tools/build.fish pdf` SHALL run `build`, delete `pdf/`, and run `tools/pipeline.py pdf --public <repo>/public --pdf-dir <repo>/pdf build/export md/procedures`. That command does the following:
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
- **WHEN** an integration test places `pdf/OSDB-0999-stale.pdf` in the temporary repository and runs `tools/build.fish pdf`
- **THEN** it exits 0, `pdf/` holds exactly `OSDB-0001-salicylic-acid.pdf` and `OSDB-0002-aspirin.pdf`, and each file begins with `%PDF-`
- **AND** neither stdout nor stderr contains `pkg_resources`

#### Scenario: Remote stylesheet fails the job
- **WHEN** an integration test adds `<link rel="stylesheet" href="https://cdn.example.invalid/x.css">` to the temporary repository's procedure layout and runs `tools/build.fish pdf`
- **THEN** it exits 1, and stderr names the failing PDF

### Requirement: new subcommand
`tools/build.fish new [--md] [--ai-model ID] TITLE...` SHALL create one procedure stub by running `tools/pipeline.py new --repo <repo> [--md] [--ai-model ID] TITLE`, and print the created file's repo-relative path. The stub is created as follows:
- The title is the words of `TITLE...` joined by single spaces and trimmed. It must not be empty or contain a newline.
- The file is `org/procedures/<ID>-<slug>.org`, or `md/procedures/<ID>-<slug>.md` with `--md`. It is copied from `templates/procedure.org` or `templates/procedure.md` and filled by `pipeline.fill_template`.
- It is created with exclusive creation, so an existing file is never overwritten.
- `ID` is `pipeline.next_id` over the candidate names, and `slug` is `pipeline.slugify(title)`.
- The `--ai-model` value must match `^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$`.

The candidate names for `next_id` are:
- the top-level entry names of `org/procedures/`, `md/procedures/` and `build/export/`;
- the base names of every path that `git log --all --no-renames --format= --name-only -- org/procedures md/procedures` reports.

When `git` is unavailable or the repository is not a git work tree, `new` prints a warning to stderr and uses the directories alone. When the repository is a shallow clone, `new` still scans the history it has, and prints a warning to stderr containing `shallow`, because IDs deleted before the shallow boundary cannot be seen.

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
- **WHEN** a test makes a temporary git repository with the repo layout, commits `md/procedures/OSDB-0012-old.md`, deletes it in a second commit, and runs `pipeline.py new --repo <it> --md --now 2026-10-19T17:42:05+02:00 Test product`
- **THEN** the created file is `md/procedures/OSDB-0013-test-product.md`

#### Scenario: Shallow clone warns
- **WHEN** a test makes a temporary git repository with the repo layout and two commits, clones it with `git clone --depth 1 file://…`, and runs `pipeline.py new --repo <clone> --md --now 2026-10-19T17:42:05+02:00 Test product`
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
- **WHEN** a test runs `pipeline.py new --repo <temporary repo with templates and empty trees> --now 2026-10-19T17:42:05+02:00 Salicylic acid`
- **THEN** the created file is `org/procedures/OSDB-0001-salicylic-acid.org`
- **AND** it contains `#+TITLE: Salicylic acid`, `#+CREATED: [2026-10-19 Mon 17:42:05]`, `#+LAST_MODIFIED: [2026-10-19 Mon 17:42:05]`, `#+AI_MODEL: none` and `#+HUGO_SLUG: osdb-0001`, and no `OSDB-0000` or `osdb-0000`
- **AND** `tools/validate.py --org-root` on its directory exits 0 and prints nothing to stdout

#### Scenario: Markdown stub with an AI model and a quoted title
- **WHEN** a test runs `pipeline.py new --md --ai-model example-model-1 --now 2026-10-19T17:42:05+02:00` with the title `Bob's "best" ester` in an empty temporary repository
- **THEN** the created file is `md/procedures/OSDB-0001-bob-s-best-ester.md`
- **AND** its front matter parses with `tomllib`, with `title` equal to `Bob's "best" ester`, `date` and `lastmod` equal to `2026-10-19T17:42:05+02:00`, `ai_model` equal to `example-model-1`, and `id` equal to `OSDB-0001`
- **AND** `tools/validate.py` on its directory exits 0 and prints nothing to stdout

#### Scenario: Human-authored Markdown stub
- **WHEN** a test runs `pipeline.py new --md --now 2026-10-19T17:42:05+02:00 Test product` in an empty temporary repository
- **THEN** the stub's front matter has no `ai_model` key

#### Scenario: Invalid AI model identifier
- **WHEN** a test runs `pipeline.py new --repo <empty temporary repository> --ai-model "two words" Test product`
- **THEN** it exits 2, stderr mentions `--ai-model`, and no file is created

### Requirement: clean subcommand
`tools/build.fish clean` SHALL remove `build/`, `public/`, `pdf/`, `site/.hugo_build.lock` and `site/resources/` from the repository. `clean --all` also removes `.emacs-batch/` and `.tools/`. Both forms touch no other path, and both succeed when there is nothing to remove.

#### Scenario: Clean keeps sources and caches
- **WHEN** a fish test creates every one of those paths in a temporary repository copy and runs `tools/build.fish clean`
- **THEN** it exits 0, `build/`, `public/`, `pdf/`, `site/.hugo_build.lock` and `site/resources/` are gone, `.emacs-batch/` and `.tools/` remain, and `org/`, `md/`, `site/hugo.toml` and `templates/` are unchanged

#### Scenario: Clean all, twice
- **WHEN** the same test then runs `tools/build.fish clean --all` twice
- **THEN** both runs exit 0, and `.emacs-batch/` and `.tools/` are gone

### Requirement: check-deps subcommand
`tools/build.fish check-deps` SHALL use only fish builtins and the tools it probes. It reports the required tools `emacs`, `git`, `python3`, `hugo` and `weasyprint`, in that order, as follows:
- Each required tool gets a line beginning `ok ` or `missing `, followed by the tool's name.
- A line beginning `optional ` reports `caddy`.
- Lines beginning `auto ` report Pagefind 1.5.2 and ox-hugo/tomelr, each saying whether it is cached or will be fetched on first use.
- When any required tool is missing, the last line is exactly `sudo dnf install <packages>`, listing the Fedora packages of the missing tools in that order (`emacs`, `git`, `python3`, `hugo`, `weasyprint`), and the exit status is 1. Otherwise the exit status is 0.

It never installs anything and never invokes `sudo`.

#### Scenario: Two tools missing
- **WHEN** a fish test runs `tools/build.fish check-deps` with a `PATH` that holds only `fish`, `python3`, `emacs`, `git` and a recording fake `sudo`
- **THEN** it exits 1, stdout has a line beginning `missing hugo` and one beginning `missing weasyprint`, and the last line is exactly `sudo dnf install hugo weasyprint`
- **AND** the fake `sudo` was never invoked

#### Scenario: Nothing missing
- **WHEN** a fish test runs `tools/build.fish check-deps` with a `PATH` holding all five required tools (real or stub executables)
- **THEN** it exits 0, and no line begins `missing ` or `sudo `

### Requirement: Pipeline helper module
`tools/pipeline.py` SHALL be an executable Python 3.14 file that uses only the standard library, besides importing `validate` from its own directory. It has a `#!/usr/bin/env python3` shebang and a PEP 723 block, and it annotates every callable. It exposes the functions `slugify`, `next_id`, `org_timestamp`, `rfc3339`, `export_instants`, `fill_template`, `recover_export`, `replace_export`, `pdf_jobs` and `install_pagefind`, and the CLI subcommands `export-plan`, `recover-export`, `install-export`, `next-id`, `new`, `pdf` and `ensure-pagefind`. The CLI exits 0 on success, 1 on failure and 2 on a usage error, and writes errors to stderr as `pipeline.py: error: <message>`.

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/pipeline.py` with `ast` and collects the top-level module names of every import
- **THEN** every name is in `sys.stdlib_module_names` or is `validate`

#### Scenario: Unknown CLI subcommand
- **WHEN** a test runs `tools/pipeline.py frobnicate`
- **THEN** it exits 2, and stderr is not empty

### Requirement: Optional pre-commit hook
`tools/hooks/pre-commit` SHALL be an executable fish script that changes to the top level of the work tree and runs `tools/build.fish validate`, exiting with its status. No subcommand enables the hook or writes to `.git/hooks/` or `core.hooksPath`.

#### Scenario: Hook refuses an invalid commit
- **WHEN** an integration test makes the temporary repository a git repository with `core.hooksPath` set to `tools/hooks`, adds `tests/fixtures/invalid/missing-title/OSDB-0101-missing-title.md` to `md/procedures/`, and runs `git commit`
- **THEN** the commit fails, and the new file is not committed

#### Scenario: Nothing enables the hook
- **WHEN** a test searches `tools/build.fish` and `tools/pipeline.py` for `hooksPath` and `.git/hooks`
- **THEN** neither string is found

### Requirement: Caddyfile example
The file `deploy/Caddyfile.example` SHALL serve a copy of `public/` as static files with `file_server`. It uses a placeholder site address and a placeholder `root` path, explained in comments, and references no external resource and no user- or machine-specific identifier.

#### Scenario: Example is generic
- **WHEN** a test reads `deploy/Caddyfile.example`
- **THEN** it contains `file_server` and a `root` directive, and contains neither `/home/` nor a host name ending in `.local`, `.lan` or `.home.arpa`

#### Scenario: Example parses when Caddy is installed
- **WHEN** a test runs `caddy adapt --adapter caddyfile --config deploy/Caddyfile.example`, skipping when `caddy` is absent
- **THEN** it exits 0

### Requirement: Ignore rules
The file `.gitignore` SHALL keep `__pycache__/` and `.pytest_cache/`, and it SHALL ignore `/build/`, `/public/`, `/pdf/`, `/.emacs-batch/`, `/.tools/`, `/site/.hugo_build.lock` and `/site/resources/`, anchored at the repository root.

#### Scenario: Generated paths ignored, sources not
- **WHEN** a test runs `git check-ignore` in the repository on `build/export/x.md`, `public/index.html`, `pdf/x.pdf`, `.emacs-batch/elpa`, `.tools/pagefind-1.5.2/pagefind`, `site/.hugo_build.lock` and `site/resources/_gen/x`, skipping when `git` is absent
- **THEN** each path is reported as ignored
- **AND** `org/procedures/OSDB-0001-salicylic-acid.org`, `md/procedures/OSDB-0002-aspirin.md`, `site/hugo.toml` and `tests/fixtures/export/build/x` are not
