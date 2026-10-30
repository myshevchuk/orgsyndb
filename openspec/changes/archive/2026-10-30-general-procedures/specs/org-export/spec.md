## MODIFIED Requirements

### Requirement: Exported front matter
The export of each Org source `<stem>.org` SHALL be a file `<stem>.md` with `+++` TOML front matter that meets all of the following:
- `date`, `lastmod`, `ai_model`, `slug` and the absence of `author` follow the procedure-schema mapping.
- Every key whose value is a table or an array of tables, such as `products`, is written after all other keys, whatever its position among the source's `#+HUGO_CUSTOM_FRONT_MATTER:` lines.
- `scope`, for a source with a table named `scope`, as general-procedures "Org scope table" states.
- Every other front-matter key and value is ox-hugo's own output.

The export adds its own `#+DATE`, `#+HUGO_LASTMOD`, `#+EXPORT_FILE_NAME` and, for a source whose `#+AI_MODEL` names a model, `#+HUGO_CUSTOM_FRONT_MATTER: :ai_model` lines at the top of an in-memory copy of the source. It exports with point at the beginning of that buffer, so that no heading's `CLOSED` timestamp is taken as the date. The source itself can set none of these values (procedure-schema "Exported values come only from the file-level keywords").

Before exporting, the export checks that `org-hugo--gen-front-matter`, `tomelr-toml-table-p` and `tomelr-toml-table-array-p` are defined. If one is not, it exits non-zero with a message naming the missing function.

#### Scenario: Seed export validates cleanly
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` and then `tools/validate.py build/export md/procedures` in the collection copy
- **THEN** the validator exits 0 and prints nothing to stdout

#### Scenario: Table written first in the source is emitted last
- **WHEN** an integration test exports `tests/fixtures/export/OSDB-0901-table-first.org`, whose first `#+HUGO_CUSTOM_FRONT_MATTER:` line sets `:products` to two products and whose later lines set `:scale`, `:hazards` and `:substrates`
- **THEN** `tomllib` parses its export with `scale`, `hazards` and `substrates` as top-level keys
- **AND** `products` is an array of two tables holding exactly the keys and values the source's `:products` list gives, in its order

#### Scenario: AI model mapping
- **WHEN** an integration test exports one source whose `#+AI_MODEL` is `none`, one without `#+AI_MODEL` and one whose `#+AI_MODEL` is `example-model-1`
- **THEN** the first two exports have no `ai_model` key, and the third has `ai_model = "example-model-1"`
- **AND** no export has an `author` key

#### Scenario: Seconds survive
- **WHEN** an integration test exports a source whose `#+LAST_MODIFIED` is `[2026-10-19 Mon 21:00:07]`
- **THEN** its export's `lastmod` parses with `tomllib` to an offset datetime equal to `2026-10-19T21:00:07+02:00`

### Requirement: Org sources and their problems
`tools/export.el` SHALL examine the top-level entries of `ORG_ROOT` before it installs, checks or loads any package, and SHALL export nothing when it finds an error. The rules are:
- **Time zone.** First it checks that the system's tz database knows Europe/Berlin, by checking that the zone's UTC offsets at 2026-01-15T12:00:00Z and 2026-07-15T12:00:00Z are `+01:00` and `+02:00`. An unknown zone name otherwise passes silently as UTC. When the check fails, it exits 1, printing `export.el: error: time zone Europe/Berlin is not available; install the tz database (tzdata)`.
- **Root.** An `ORG_ROOT` that is not a directory makes it exit 1, printing `export.el: error: <ORG_ROOT> is not a directory`.
- **Discovery.** A subdirectory of `ORG_ROOT`, whatever its name, is a `file_name` error with the message `subdirectories are not supported; move its files to the top level`, and its contents are not read. A non-directory entry whose name begins with `.`, or a file named `_index.md`, is skipped silently. Every other entry whose name ends in `.org` is an Org source. Any other entry is a `file_name` warning with the message `not a procedure file; ignored`.
- **Reading.** Each Org source is read as UTF-8, tolerating a byte-order mark. Lines end at LF, and a CR before the LF is not part of the line. A source that is not valid UTF-8 gets the single `front_matter` error `file is not valid UTF-8`. A source that cannot be read gets the single `front_matter` error `cannot read file: <reason>`, where `<reason>` is the operating system's message for the failure, such as `Permission denied`. Such a source gets no further checks, not even of its file name.
- **Checks.** Each source that was read is checked in this order:
  1. its file name, against procedure-schema "Procedure file names", except that the `OSDB-NNNN` prefix is not compared with an `id`;
  2. the keywords `#+CREATED`, `#+LAST_MODIFIED` and `#+AI_MODEL`, and the ordering of the two timestamps, against procedure-schema "Org file-level keywords";
  3. the routes that procedure-schema "Exported values come only from the file-level keywords" forbids;
  4. the table named `scope`, against general-procedures "Org scope table".

  A file name that breaks the pattern gives the error `must be named OSDB-NNNN-short-slug.org, e.g. OSDB-0001-ethyl-acetate.org, or OSDB-0001-ethyl-acetate.de.org with a language`. A code other than `de` or `en` gives the error `unknown language code ".<code>"; use de or en, or none`.
- **Report.** Each problem is one line on stdout of the form `<path>:<field>: <severity>: <message>`. `<path>` is `ORG_ROOT` as given, joined with the entry name by a single `/`. `<field>` is `file_name`, `front_matter`, `scope`, a keyword including `#+`, or a property or drawer name including its colons, such as `:EXPORT_DATE:`. `<severity>` is `error` or `warning`. Lines are sorted by path and, within one path, follow the check order. Emacs's stdout holds exactly these lines, each ended by a newline, and nothing else. Every other message, including Org's and ox-hugo's, goes to stderr.
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
