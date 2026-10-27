# org-export Specification

## Purpose
Define how `tools/export.el` turns Org procedure sources into Hugo content: an isolated, pinned batch Emacs, the front-matter mapping, body export options, and a complete, fresh and byte-identical export directory.
## Requirements
### Requirement: Isolated batch Emacs
`tools/export.el` SHALL run under `emacs -Q --batch`, invoked as `emacs -Q --batch -l tools/export.el ORG_ROOT STAGING_DIR`, and SHALL work with Emacs 29.1 or later and the Org it bundles. `ORG_ROOT` is the directory of Org sources, and `tools/orgsyndb` passes `org/procedures` with the collection as working directory. It loads neither package.el nor any package archive. Before loading Org or `tools/osdb-org.el` it SHALL make these settings:
- `user-emacs-directory` points to the application's `.emacs-batch/`.
- `temporary-file-directory` and the `TMPDIR` environment variable point to `tmp/` in the parent directory of `STAGING_DIR`, which is the collection's `build/tmp/`, and which is created when missing.

Under an Emacs older than 29.1 it exits 1 before installing or exporting anything, printing `export.el: error: Emacs 29.1 or later is required; this is Emacs <version>`.

The export writes nothing under `$HOME`, and nothing in the `TMPDIR` it inherited. It neither loads nor writes anything in `~/.emacs.d` or `~/.config/emacs`. git, which the bootstrap and the pin check run, may still read its own user configuration.

#### Scenario: Owner's directories and the inherited TMPDIR stay untouched
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` with `HOME` set to a temporary directory that contains only an empty `.config/emacs/`, and `TMPDIR` set to a separate, empty temporary directory with mode 0555
- **THEN** the export exits 0
- **AND** afterwards that `HOME` contains the empty `.config/emacs/` directory and nothing else, in particular no `.emacs.d`
- **AND** the `TMPDIR` directory is still empty

#### Scenario: An old Emacs is refused
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` with an `emacs` on `PATH` that runs the real Emacs with `emacs-version` set to `28.2` before `tools/export.el` loads
- **THEN** the export exits 1, the output contains `Emacs 29.1 or later is required; this is Emacs 28.2`, and `build/export/` is unchanged

### Requirement: Pinned ox-hugo and tomelr
`tools/export.el` SHALL install tomelr and then ox-hugo, each only when its directory `.emacs-batch/elpa/<package>/` in the application does not exist, by cloning the package's upstream repository with git into that directory and checking out its pinned commit. When the clone or the checkout fails, it removes the directory and exits non-zero with a message naming the package. It then adds both directories to `load-path`. The pins are:
- tomelr: `https://github.com/kaushalmodi/tomelr` at `670e0a08f625175fd80137cf69e799619bf8a381` (0.4.3).
- ox-hugo: `https://github.com/kaushalmodi/ox-hugo` at `b7dc44dc28911b9d8e3055a18deac16c3b560b03` (MELPA `20251206.1738`).

On every run that goes on to export, that is, every run whose Org sources have no error and include at least one Org source, the export compares each installed checkout's `HEAD` with its pin. On a mismatch it exits non-zero, before exporting anything, with a message that names the package, both commits, and `tools/orgsyndb clean --all`.

#### Scenario: Installed checkouts are at the pins
- **WHEN** an integration test reads `git rev-parse HEAD` in `.emacs-batch/elpa/ox-hugo` and `.emacs-batch/elpa/tomelr` after an export
- **THEN** the values are `b7dc44dc28911b9d8e3055a18deac16c3b560b03` and `670e0a08f625175fd80137cf69e799619bf8a381`

#### Scenario: A checkout at another commit stops the export
- **WHEN** an integration test copies `.emacs-batch/` into the application copy instead of linking it, checks out ox-hugo's parent commit in the copy, and runs `tools/orgsyndb -C <collection> export`
- **THEN** the exit status is non-zero, and the output contains `ox-hugo`, `b7dc44dc28911b9d8e3055a18deac16c3b560b03`, the parent commit's hash, and `clean --all`
- **AND** `build/export/` is unchanged

#### Scenario: No package.el
- **WHEN** a test reads `tools/export.el` and `tools/osdb-org.el`
- **THEN** neither contains `package-vc` or `(require 'package)`

### Requirement: Exported timestamps
The export SHALL write `date` and `lastmod` with the wall-clock time of `#+CREATED` and `#+LAST_MODIFIED`, seconds included, and a Europe/Berlin UTC offset in force at that instant. Where a time in the autumn fall-back hour names two instants, the choice is made as follows:
- `date` is the earliest instant of `#+CREATED`.
- `lastmod` is the earliest instant of `#+LAST_MODIFIED` that is not earlier than `date`, or the latest instant of `#+LAST_MODIFIED` when there is no such instant.

`osdb-org-local-instants` returns the instants that a Europe/Berlin wall-clock time names, earliest first. `osdb-org-export-instants` implements the choice. `osdb-org-rfc3339` formats an instant as `YYYY-MM-DDThh:mm:ss+HH:MM` in Europe/Berlin.

In the scenarios, "the exported `date`" is the `date` of the source that `osdb-org-examine` returns. The ERT test examines a temporary directory holding a copy of `tests/fixtures/valid/org/OSDB-0003-propyl-acetate.org`, or of `OSDB-0004-ambiguous-hour.org` for the fall-back hour, with the stated keyword lines replaced.

#### Scenario: Summer time
- **WHEN** an ERT test examines a source whose `#+CREATED` is `[2026-10-19 Mon 17:42:05]`
- **THEN** the exported `date` is `2026-10-19T17:42:05+02:00`

#### Scenario: Winter time, last second before the spring change
- **WHEN** an ERT test examines a source whose `#+CREATED` is `[2026-03-29 Sun 01:59:59]` and `#+LAST_MODIFIED` is `[2026-03-29 Sun 03:00:00]`
- **THEN** the exported `date` is `2026-03-29T01:59:59+01:00` and `lastmod` is `2026-03-29T03:00:00+02:00`

#### Scenario: Fall-back hour out of wall-clock order
- **WHEN** an ERT test examines a source whose `#+CREATED` is `[2026-10-25 Sun 02:50:00]` and `#+LAST_MODIFIED` is `[2026-10-25 Sun 02:10:00]`
- **THEN** the exported `date` is `2026-10-25T02:50:00+02:00` and `lastmod` is `2026-10-25T02:10:00+01:00`

#### Scenario: Equal times in the fall-back hour
- **WHEN** an ERT test examines a source whose `#+CREATED` and `#+LAST_MODIFIED` are both `[2026-10-25 Sun 02:30:00]`
- **THEN** the exported `date` and `lastmod` are both `2026-10-25T02:30:00+02:00`

#### Scenario: Instants of a wall-clock time
- **WHEN** an ERT test calls `osdb-org-local-instants` for 2026-10-19 17:42:05, 2026-10-25 02:30:00 and 2026-03-29 02:30:00, and formats each instant with `osdb-org-rfc3339`
- **THEN** the first gives exactly `2026-10-19T17:42:05+02:00`, the second exactly `2026-10-25T02:30:00+02:00` then `2026-10-25T02:30:00+01:00`, and the third no instant

#### Scenario: Choice among fall-back instants
- **WHEN** an ERT test calls `osdb-org-export-instants` with the instants of 2026-10-25 02:50:00 as `created` and those of 2026-10-25 02:10:00 as `last-modified`
- **THEN** `osdb-org-rfc3339` gives `2026-10-25T02:50:00+02:00` for the chosen `date` and `2026-10-25T02:10:00+01:00` for the chosen `lastmod`

### Requirement: Exported front matter
The export of each Org source `<stem>.org` SHALL be a file `<stem>.md` with `+++` TOML front matter that meets all of the following:
- `date`, `lastmod`, `ai_model`, `slug` and the absence of `author` follow the procedure-schema mapping.
- Every key whose value is a table is written after all other keys, whatever its position among the source's `#+HUGO_CUSTOM_FRONT_MATTER:` lines.
- Every other front-matter key and value is ox-hugo's own output.

The export adds its own `#+DATE`, `#+HUGO_LASTMOD`, `#+EXPORT_FILE_NAME` and, for a source whose `#+AI_MODEL` names a model, `#+HUGO_CUSTOM_FRONT_MATTER: :ai_model` lines at the top of an in-memory copy of the source. It exports with point at the beginning of that buffer, so that no heading's `CLOSED` timestamp is taken as the date. The source itself can set none of these values (procedure-schema "Exported values come only from the file-level keywords").

Before exporting, the export checks that `org-hugo--gen-front-matter` and `tomelr-toml-table-p` are defined. If either is not, it exits non-zero with a message naming the missing function.

#### Scenario: Seed export validates cleanly
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` and then `tools/validate.py build/export md/procedures` in the collection copy
- **THEN** the validator exits 0 and prints nothing to stdout

#### Scenario: Table written first in the source is emitted last
- **WHEN** an integration test exports `tests/fixtures/export/OSDB-0901-table-first.org`, whose first `#+HUGO_CUSTOM_FRONT_MATTER:` line sets `:product` and whose later lines set `:scale`, `:yield_percent`, `:hazards` and `:precursors`
- **THEN** `tomllib` parses its export with `scale`, `yield_percent`, `hazards` and `precursors` as top-level keys
- **AND** the `product` table holds exactly the keys the source's `:product` map gives

#### Scenario: AI model mapping
- **WHEN** an integration test exports one source whose `#+AI_MODEL` is `none`, one without `#+AI_MODEL` and one whose `#+AI_MODEL` is `example-model-1`
- **THEN** the first two exports have no `ai_model` key, and the third has `ai_model = "example-model-1"`
- **AND** no export has an `author` key

#### Scenario: Seconds survive
- **WHEN** an integration test exports a source whose `#+LAST_MODIFIED` is `[2026-10-19 Mon 21:00:07]`
- **THEN** its export's `lastmod` parses with `tomllib` to an offset datetime equal to `2026-10-19T21:00:07+02:00`

### Requirement: Body export options
The export SHALL use the following body options, whatever the Org defaults are:
- LaTeX fragments are exported verbatim (`org-html-with-latex` is `verbatim`).
- Only braced sub- and superscripts are interpreted (`org-export-with-sub-superscripts` is `{}`).
- No source block is evaluated (`org-export-use-babel` is nil).
- File-local variables are ignored.

No math renderer is configured or loaded anywhere in the site.

#### Scenario: Dollar signs and LaTeX stay literal
- **WHEN** an integration test exports `tests/fixtures/export/OSDB-0902-literal-text.org`, whose Summary contains `Costs $5 and $10, $x$ and \(y^2\).`
- **THEN** the exported body contains `$5`, `$10` and `$x$`, and does not contain `\\(x\\)`

#### Scenario: Only braced subscripts are interpreted
- **WHEN** the same Summary also contains `H_{2}O, CO_2 and yield_percent`
- **THEN** the exported body contains `H<sub>2</sub>O`, `CO_2` and `yield_percent`

#### Scenario: Source blocks are not evaluated
- **WHEN** the same source contains an `emacs-lisp` source block with `:exports results` whose code would create a marker file named by the test
- **THEN** the export exits 0 and the marker file does not exist

### Requirement: Complete and fresh export directory
`tools/orgsyndb export` SHALL leave `build/export/` holding exactly one `<stem>.md` for each Org source `<stem>.org` of `org/procedures/`, and no other file. The Org sources here are the entries that `validate.discover("org/procedures", ".org")` returns with no problem attached, and `pipeline.org_stems(org_root)` returns their stems, sorted. It uses the sibling directories `build/.export-staging/` and `build/.export-previous/` in these steps:
1. **Recover.** `pipeline.recover_export(build)` runs first:
   - If `.export-previous/` exists and `export/` does not, it renames `.export-previous/` to `export/`.
   - If both exist, it deletes `.export-previous/`.
   - It deletes any `.export-staging/`, and empties `build/tmp/`.
2. **Stage.** The export writes into a new, empty `.export-staging/`.
3. **Install.** `pipeline.check_staging(build, stems)` and then `pipeline.replace_export(build, rename, remove)` run. `rename` defaults to `os.rename` and `remove` to `shutil.rmtree`; both are injectable so that tests can make a step fail:
   1. It checks that the staging directory holds exactly `<stem>.md` for each of `stems`.
   2. It renames an existing `export/` to `.export-previous/`.
   3. It renames `.export-staging/` to `export/`. When that rename fails, it renames `.export-previous/` back to `export/` before failing.
   4. It deletes `.export-previous/`. A failure of this delete is a warning only.

When there are no Org sources, `build/export/` exists and is empty. When any step fails, the command exits 1, and `build/export/` holds its previous contents, either directly or after the next run's recovery step.

#### Scenario: Deleted source leaves no orphan
- **WHEN** an integration test exports, deletes one Org source, and exports again
- **THEN** that source's `.md` is absent from `build/export/`, and every other export is still present

#### Scenario: Failed export keeps the previous directory
- **WHEN** an integration test exports successfully, then changes one source's `#+CREATED` to `[2026-10-19 Mon 17:42]` and exports again
- **THEN** the second export exits 1, and `build/export/` holds the same files with the same bytes as after the first export

#### Scenario: Org stems
- **WHEN** a test calls `org_stems` on a temporary directory holding `OSDB-0002-b.org`, `OSDB-0001-a.de.org`, `.#OSDB-0001-a.org`, `notes.txt` and a subdirectory `nested/`, and on a directory that does not exist
- **THEN** it returns `["OSDB-0001-a.de", "OSDB-0002-b"]` for the first and `[]` for the second

#### Scenario: Staging check
- **WHEN** a unit test calls `check_staging` with the stems `A` and `B` on a `build/.export-staging/` that holds `A.md` and `C.md`
- **THEN** it raises `pipeline.ExportError` naming `B.md` as missing and `C.md` as unexpected

#### Scenario: Second rename fails
- **WHEN** a unit test builds `build/export/` (one file `A.md`) and `build/.export-staging/` (one file `B.md`), and calls `replace_export` with a `rename` that fails on its second call
- **THEN** `replace_export` raises, `build/export/` holds exactly `A.md` with its original bytes, and `build/.export-previous/` does not exist

#### Scenario: Restore fails too
- **WHEN** the same test uses a `rename` that fails on its second and third calls
- **THEN** `replace_export` raises with a message saying that the next export will recover
- **AND** a following call of `recover_export` leaves `build/export/` holding exactly `A.md`, with no `.export-previous/` and no `.export-staging/`

#### Scenario: Backup deletion fails after a successful swap
- **WHEN** the same test lets both renames succeed but passes a `remove` that raises `OSError`
- **THEN** `replace_export` returns normally, `build/export/` holds exactly `B.md`, and a following call of `recover_export` removes `.export-previous/`

#### Scenario: Leftovers from a crashed run
- **WHEN** an integration test leaves `build/.export-previous/` holding a complete earlier export with no `build/export/`, plus a partial `build/.export-staging/`, and then runs `tools/orgsyndb -C <collection> export`
- **THEN** the export exits 0, `build/export/` holds exactly the current exports, and neither `.export-previous/` nor `.export-staging/` remains

#### Scenario: No Org sources
- **WHEN** an integration test removes every file from `org/procedures/` and exports
- **THEN** the export exits 0, and `build/export/` exists and is empty

### Requirement: Idempotent export
Exporting unchanged sources SHALL produce byte-identical files.

#### Scenario: Re-export without changes
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` twice without changing any source
- **THEN** `build/export/` holds the same file names after both runs, and each file has identical bytes

#### Scenario: Re-export of a named paragraph
- **WHEN** an integration test adds `tests/fixtures/export/OSDB-0903-named-paragraph.org`, which holds paragraphs preceded by `#+name: observation` and `#+name: second`, and exports twice
- **THEN** its export contains anchors of the form `id="org` followed by seven hexadecimal digits
- **AND** both runs produce identical bytes for it

### Requirement: Deterministic reference IDs
The export SHALL seed Emacs's random number generator with `(random "<stem>")` immediately before exporting each source. Org's generated reference IDs, and so ox-hugo's `org…` anchors, are then determined by the source's stem and its own content, independent of the other sources and of their order.

#### Scenario: Other sources do not change a file's anchors
- **WHEN** an integration test exports with `OSDB-0903-named-paragraph.org` as the only Org source, then adds `OSDB-0902-literal-text.org` and the seeds and exports again
- **THEN** the export of `OSDB-0903-named-paragraph.org` has identical bytes in both runs

### Requirement: Export checked on Emacs 29
The repository SHALL ship `.github/workflows/emacs-29.yml`, a GitHub Actions workflow that checks the export and the ERT suite on the oldest supported Emacs:
- **Triggers.** It runs on a push to `main`, on pull requests and on manual dispatch (`workflow_dispatch`).
- **Permissions.** Its permissions are `contents: read`.
- **Job.** A job named `export` runs on `ubuntu-24.04`. It installs `emacs-nox` and `git` with `apt-get install --no-install-recommends`, sets up Python 3.14 with `actions/setup-python`, and installs pytest with pip. It runs `tools/orgsyndb -C examples/demo export`, and then `python -m pytest tests/test_export_integration.py tests/test_elisp.py`.

#### Scenario: Workflow is wired
- **WHEN** a test reads `.github/workflows/emacs-29.yml` as text
- **THEN** its triggers name `push` with branch `main`, `pull_request` and `workflow_dispatch`, and its permissions are `contents: read`
- **AND** the `export` job runs on `ubuntu-24.04`, names an `apt-get install` with `--no-install-recommends` of `emacs-nox` and `git`, `actions/setup-python` with Python `3.14`, and the commands `tools/orgsyndb -C examples/demo export` and `python -m pytest tests/test_export_integration.py tests/test_elisp.py`, in that order

### Requirement: Export without Org sources
When the collection has no Org sources, as the build-script spec defines them, `tools/orgsyndb export` SHALL start no Emacs. It prints the step line `==> export: no Org sources; Emacs is not needed` in place of the Emacs step, and otherwise runs the recover, stage and install steps of "Complete and fresh export directory", so that `build/export/` exists and is empty.

#### Scenario: Export with neither Emacs nor git
- **WHEN** an integration test removes every file from `org/procedures/` and runs `tools/orgsyndb -C <collection> export` with a `PATH` that holds `python3` but neither `emacs` nor `git`
- **THEN** it exits 0, stdout contains `==> export: no Org sources; Emacs is not needed`, and `build/export/` exists and is empty

### Requirement: Org sources and their problems
`tools/export.el` SHALL examine the top-level entries of `ORG_ROOT` before it installs, checks or loads any package, and SHALL export nothing when it finds an error. The rules are:
- **Time zone.** First it checks that the system's tz database knows Europe/Berlin, by checking that the zone's UTC offsets at 2026-01-15T12:00:00Z and 2026-07-15T12:00:00Z are `+01:00` and `+02:00`. An unknown zone name otherwise passes silently as UTC. When the check fails, it exits 1, printing `export.el: error: time zone Europe/Berlin is not available; install the tz database (tzdata)`.
- **Root.** An `ORG_ROOT` that is not a directory makes it exit 1, printing `export.el: error: <ORG_ROOT> is not a directory`.
- **Discovery.** A subdirectory of `ORG_ROOT`, whatever its name, is a `file_name` error with the message `subdirectories are not supported; move its files to the top level`, and its contents are not read. A non-directory entry whose name begins with `.`, or a file named `_index.md`, is skipped silently. Every other entry whose name ends in `.org` is an Org source. Any other entry is a `file_name` warning with the message `not a procedure file; ignored`.
- **Reading.** Each Org source is read as UTF-8, tolerating a byte-order mark. Lines end at LF, and a CR before the LF is not part of the line. A source that is not valid UTF-8 gets the single `front_matter` error `file is not valid UTF-8`. A source that cannot be read gets the single `front_matter` error `cannot read file: <reason>`, where `<reason>` is the operating system's message for the failure, such as `Permission denied`. Such a source gets no further checks, not even of its file name.
- **Checks.** Each source that was read is checked in this order:
  1. its file name, against procedure-schema "Procedure file names", except that the `OSDB-NNNN` prefix is not compared with an `id`;
  2. the keywords `#+CREATED`, `#+LAST_MODIFIED` and `#+AI_MODEL`, and the ordering of the two timestamps, against procedure-schema "Org file-level keywords";
  3. the routes that procedure-schema "Exported values come only from the file-level keywords" forbids.

  A file name that breaks the pattern gives the error `must be named OSDB-NNNN-short-slug.org, e.g. OSDB-0001-ethyl-acetate.org, or OSDB-0001-ethyl-acetate.de.org with a language`. A code other than `de` or `en` gives the error `unknown language code ".<code>"; use de or en, or none`.
- **Report.** Each problem is one line on stdout of the form `<path>:<field>: <severity>: <message>`. `<path>` is `ORG_ROOT` as given, joined with the entry name by a single `/`. `<field>` is `file_name`, `front_matter`, a keyword including `#+`, or a property or drawer name including its colons, such as `:EXPORT_DATE:`. `<severity>` is `error` or `warning`. Lines are sorted by path and, within one path, follow the check order. Emacs's stdout holds exactly these lines, each ended by a newline, and nothing else. Every other message, including Org's and ox-hugo's, goes to stderr.
- **Outcome.** When any line is an error, it exits 1 after printing every line, having installed, checked and loaded no package and written nothing into `STAGING_DIR`. Warnings alone do not stop the export. When `ORG_ROOT` holds no Org source, it exits 0 after printing its lines, without installing or loading any package.

`tools/orgsyndb export` handles `org/procedures` as follows:
- **Not a directory.** After the recovery step and before staging, it fails with `orgsyndb: error: org/procedures is not a directory` when `org/procedures` exists but is not a directory. No Emacs starts, and `build/export/` is unchanged.
- **Streams.** It writes Emacs's stdout and stderr to `build/export.log`, and prints Emacs's stdout on its own stdout, unchanged, whether the export succeeds or fails.
- **Failure.** A line's severity is read after its path, which is `org/procedures/` joined with the name of an entry that `validate.discover("org/procedures", ".org")` returns, the longest such path when several fit, and after its field; `pipeline.org_error_reported(report, paths)` makes this test. When Emacs exits non-zero and its stdout holds a line with severity `error`, `orgsyndb` fails with `orgsyndb: error: the Org sources have errors; build/export/ is unchanged`, without printing the log. When Emacs exits non-zero otherwise, `orgsyndb` prints the log to stderr and fails with `orgsyndb: error: export failed; Emacs output is in build/export.log`.

In each failure case `build/export/` is unchanged, and no later step of the subcommand runs.

#### Scenario: Severity is read after the entry path
- **WHEN** a test calls `org_error_reported` with the paths `org/procedures/x:file_name: error: y` and `org/procedures/OSDB-0001-a.org`, and in turn the report `org/procedures/x:file_name: error: y:file_name: warning: not a procedure file; ignored`, that report followed by the line `org/procedures/OSDB-0001-a.org:#+CREATED: error: keyword missing`, the line `other/OSDB-0001-a.org:#+CREATED: error: keyword missing`, and an empty report
- **THEN** it returns false, true, false and false
#### Scenario: Entries of the Org root
- **WHEN** an ERT test calls `osdb-org-examine` on a temporary directory `R` holding a copy of `tests/fixtures/valid/org/OSDB-0003-propyl-acetate.org`, a dangling symlink named `.#OSDB-0003-x.org`, a regular file `.OSDB-0005-hidden.org`, a file `_index.md`, a subdirectory `nested.org/` and a file `notes.txt`
- **THEN** the sources are exactly the `OSDB-0003` source, with its absolute path, stem `OSDB-0003-propyl-acetate`, `date` `2026-10-19T17:42:05+02:00`, `lastmod` `2026-10-19T18:30:00+02:00` and no AI model
- **AND** the problem lines are exactly `R/nested.org:file_name: error: subdirectories are not supported; move its files to the top level` and `R/notes.txt:file_name: warning: not a procedure file; ignored`, in that order

#### Scenario: Subdirectory in the Org root
- **WHEN** an ERT test calls `osdb-org-examine` on `tests/fixtures/org-invalid/subdirectory/org`, whose only entry is the directory `nested/`, holding `OSDB-0215-nested.org`
- **THEN** it returns no source and exactly one problem: an error on the path ending `nested`, field `file_name`, containing `subdirectories are not supported`

#### Scenario: Problem line format
- **WHEN** an ERT test calls `osdb-org-examine` on the directory `R` of `tests/fixtures/org-invalid/wrong-weekday/org`, given once without and once with a trailing `/`, and formats each problem with `osdb-org-problem-line`
- **THEN** each call gives exactly the one line `R/OSDB-0206-wrong-weekday.org:#+CREATED: error: weekday "Tue" does not match 2026-10-19 (Mon)`

#### Scenario: Problems in path order
- **WHEN** an ERT test calls `osdb-org-examine` on a temporary directory holding copies of `tests/fixtures/org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org` and `tests/fixtures/org-invalid/missing-created/org/OSDB-0201-missing-created.org`
- **THEN** it returns exactly two problems, the `OSDB-0201` problem first and the `OSDB-0206` problem second

#### Scenario: File name and keywords together
- **WHEN** an ERT test examines a temporary directory `R` holding a copy of `org-invalid/missing-created/org/OSDB-0201-missing-created.org` named `osdb-0201-missing-created.org`
- **THEN** the problem lines are exactly `R/osdb-0201-missing-created.org:file_name: error: must be named OSDB-NNNN-short-slug.org, e.g. OSDB-0001-ethyl-acetate.org, or OSDB-0001-ethyl-acetate.de.org with a language` and `R/osdb-0201-missing-created.org:#+CREATED: error: keyword missing`, in that order

#### Scenario: Language code in an Org file name
- **WHEN** an ERT test calls `osdb-org-check-file-name` on `OSDB-0100-baseline.en.org` and on `OSDB-0100-baseline.fr.org`
- **THEN** the first returns no problem, and the second exactly one error, field `file_name`, with the message `unknown language code ".fr"; use de or en, or none`

#### Scenario: Invalid UTF-8 suppresses every other check
- **WHEN** an ERT test examines a temporary directory `R` holding `osdb-0100-bad-bytes.org`, a copy of `valid/org/OSDB-0003-propyl-acetate.org` without its `#+CREATED` line and with the byte `0xFF` added to its title
- **THEN** the problem lines are exactly `R/osdb-0100-bad-bytes.org:front_matter: error: file is not valid UTF-8`

#### Scenario: Unreadable source
- **WHEN** an ERT test examines a temporary directory `R` holding `osdb-0100-unreadable.org`, a copy of `valid/org/OSDB-0003-propyl-acetate.org` with mode 000, skipping when the file can still be read, as it can for root
- **THEN** the problem lines are exactly `R/osdb-0100-unreadable.org:front_matter: error: cannot read file: Permission denied`

#### Scenario: Byte-order mark and CRLF line ends
- **WHEN** an ERT test examines a temporary directory holding a copy of `valid/org/OSDB-0003-propyl-acetate.org` that begins with a UTF-8 byte-order mark and ends every line with CR LF
- **THEN** it returns no problem, and the source's `date` is `2026-10-19T17:42:05+02:00` and its `lastmod` `2026-10-19T18:30:00+02:00`

#### Scenario: Missing time zone
- **WHEN** an ERT test calls `osdb-org-zone-available-p` with `Europe/Berlin` and with `Nowhere/Nothing`
- **THEN** the first call returns non-nil and the second nil

#### Scenario: Emacs's stdout holds only problem lines
- **WHEN** a test runs `emacs -Q --batch -l tools/export.el <R> <S>` directly, where `R` is a temporary directory holding a copy of `tests/fixtures/org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org` and a file `notes.txt`, and `S` an empty temporary directory, skipping when `emacs` is absent
- **THEN** it exits 1, and its stdout is exactly the two lines `<R>/OSDB-0206-wrong-weekday.org:#+CREATED: error: weekday "Tue" does not match 2026-10-19 (Mon)` and `<R>/notes.txt:file_name: warning: not a procedure file; ignored`, each ended by a newline
- **AND** `S` is still empty

#### Scenario: Org errors stop validate before any package is installed
- **WHEN** an integration test copies `tests/fixtures/org-invalid/missing-seconds/org/OSDB-0204-missing-seconds.org` into `org/procedures/` of a copy of the test collection `tests/fixtures/collection/`, in an application copy without `.emacs-batch/`, and runs `tools/orgsyndb -C <collection> validate`, skipping when `emacs` or `git` is absent
- **THEN** it exits 1, and the lines of stdout that do not begin with `==> ` are exactly `org/procedures/OSDB-0204-missing-seconds.org:#+CREATED: error: "[2026-10-19 Mon 17:42]" must have the form [YYYY-MM-DD Day hh:mm:ss]`
- **AND** stderr contains `the Org sources have errors; build/export/ is unchanged`, the application copy has no `.emacs-batch/`, and the collection has no `build/export/`

#### Scenario: Conflicting front matter stops the export
- **WHEN** an integration test copies `tests/fixtures/org-invalid/custom-ai-model/org/OSDB-0216-custom-ai-model.org`, whose `#+AI_MODEL` is `none` and which has the line `#+HUGO_CUSTOM_FRONT_MATTER: :ai_model "example-model-1"`, into `org/procedures/` of a copy of the test collection, in an application copy without `.emacs-batch/`, and runs `tools/orgsyndb -C <collection> export`, skipping when `emacs` or `git` is absent
- **THEN** it exits 1, the lines of stdout that do not begin with `==> ` are exactly `org/procedures/OSDB-0216-custom-ai-model.org:#+HUGO_CUSTOM_FRONT_MATTER: error: must not set :ai_model; the export writes it from #+AI_MODEL`, stderr contains `the Org sources have errors`, and the collection has no `build/export/`

#### Scenario: Warnings alone do not stop the export
- **WHEN** an integration test adds a file `org/procedures/notes.txt` to a copy of the demo collection and runs `tools/orgsyndb -C <collection> export`
- **THEN** it exits 0, the lines of stdout that do not begin with `==> ` are exactly `org/procedures/notes.txt:file_name: warning: not a procedure file; ignored`, and `build/export/` holds one `<stem>.md` for each `<stem>.org` in `org/procedures/`

#### Scenario: Warnings followed by an export failure
- **WHEN** an integration test adds a file `org/procedures/notes.txt` to a copy of the demo collection, copies `.emacs-batch/` into the application copy instead of linking it, checks out ox-hugo's parent commit in the copy, and runs `tools/orgsyndb -C <collection> export`
- **THEN** it exits 1, the lines of stdout that do not begin with `==> ` are exactly `org/procedures/notes.txt:file_name: warning: not a procedure file; ignored`
- **AND** stderr contains the log, which names `clean --all`, and `export failed; Emacs output is in build/export.log`, and does not contain `the Org sources have errors`
- **AND** `build/export/` is unchanged

#### Scenario: Org root that is not a directory
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` on a copy of the test collection, adds `build/export/keep.md`, creates `org/` holding a regular file named `procedures`, and runs `export` again with a `PATH` that holds `python3` but neither `emacs` nor `git`
- **THEN** the second run exits 1, stderr contains `orgsyndb: error: org/procedures is not a directory`, and `build/export/` holds exactly `keep.md` with its bytes unchanged

#### Scenario: ORG_ROOT that is not a directory
- **WHEN** a test runs `emacs -Q --batch -l tools/export.el <missing directory> <empty temporary directory>`, skipping when `emacs` is absent
- **THEN** it exits 1, and its output contains `export.el: error:` and `is not a directory`

#### Scenario: Stubs from new pass the Org checks
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> new Test product` and `tools/orgsyndb -C <collection> new --lang de Prüfprodukt` on a copy of the demo collection, and then `tools/orgsyndb -C <collection> export`
- **THEN** the export exits 0, prints no line of the form `<path>:<field>: <severity>: <message>`, and `build/export/` holds `<stem>.md` for the stem of each new stub

### Requirement: Org front-end library
`tools/osdb-org.el` SHALL hold every function of the export that reads Org text or Org file names, together with the timestamp arithmetic, and loading it SHALL have no effect beyond defining its functions and constants. It loads neither Org nor ox-hugo nor tomelr. It reads no command-line argument, starts no export and never calls `kill-emacs`. It provides the feature `osdb-org`, and `tools/export.el` loads it from its own directory after making the settings of "Isolated batch Emacs". It defines at least the functions that the ERT scenarios of this capability, procedure-schema and localization call: `osdb-org-examine`, `osdb-org-problem-line`, `osdb-org-check-file-name`, `osdb-org-local-instants`, `osdb-org-export-instants`, `osdb-org-rfc3339` and `osdb-org-zone-available-p`.

`osdb-org-examine` takes a directory and returns a pair of the sources and the problems, as follows:
- The sources are the Org sources without any problem, in name order. Each carries its absolute path, its stem (the file name without `.org`), its `date` and `lastmod` as `YYYY-MM-DDThh:mm:ss+HH:MM` strings, and its AI model, or none when `#+AI_MODEL` is absent or `none`.
- The problems are path and problem pairs, in report order. Each problem has a field, a severity and a message.

#### Scenario: Library loads alone
- **WHEN** an ERT test, running in the suite's `emacs -Q --batch` after it loaded `tools/osdb-org.el`, checks which features are present
- **THEN** `osdb-org` is a feature, and `org`, `ox-hugo` and `tomelr` are not

### Requirement: ERT suite
The repository SHALL ship an ERT suite, `tests/el/osdb-org-tests.el`, that proves every scenario stated as an ERT test in this capability, procedure-schema and localization. Each test names its scenario in its docstring. The suite has these properties:
- It runs with `emacs -Q --batch -l <repo>/tests/el/osdb-org-tests.el -f ert-run-tests-batch-and-exit` from any working directory.
- It loads `tools/osdb-org.el` relative to its own location.
- It needs neither ox-hugo nor tomelr nor network access.
- It reads its fixtures from `tests/fixtures/`.

In ERT scenarios, an Org fixture path such as `org-invalid/missing-created/org/OSDB-0201-missing-created.org` is relative to `tests/fixtures/`. "Examines F" means calling `osdb-org-examine` on the directory holding F. "Reports exactly one error with field F containing T" means that the call returns exactly one problem, and that problem has field F, severity `error` and a message containing T. "The problem lines are exactly L" means that formatting every returned problem with `osdb-org-problem-line` gives the lines L and no others, in that order, where `R` stands for the directory as it was given to `osdb-org-examine`. These comparisons are of whole lines.

`tests/test_elisp.py` runs that command under pytest. It passes when the command exits 0, shows the command's output when it does not, and skips with a reason that names `emacs` when `emacs` is absent, so that `python3 -m pytest tests` stays the single entry point.

#### Scenario: ERT suite under pytest
- **WHEN** `python3 -m pytest tests/test_elisp.py` runs with `emacs` on `PATH`
- **THEN** it passes, having run the ERT suite with no failed or skipped ERT test

#### Scenario: ERT suite without Emacs
- **WHEN** `python3 -m pytest -rs tests/test_elisp.py` runs with a `PATH` that holds `python3` but no `emacs`
- **THEN** its test is skipped with a reason that names `emacs`

