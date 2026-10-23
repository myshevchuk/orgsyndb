# org-export Specification

## Purpose
Define how `tools/export.el` turns Org procedure sources into Hugo content: an isolated, pinned batch Emacs, the front-matter mapping, body export options, and a complete, fresh and byte-identical export directory.
## Requirements
### Requirement: Isolated batch Emacs
`tools/export.el` SHALL run under `emacs -Q --batch`, invoked as `emacs -Q --batch -l tools/export.el PLAN_JSON STAGING_DIR`, and SHALL work with Emacs 30.2 and the Org 9.7.11 it bundles. Before loading package.el or Org it SHALL make these settings:
- `user-emacs-directory`, `package-user-dir` and `package-gnupghome-dir` point to directories inside the application's `.emacs-batch/`.
- `temporary-file-directory` and the `TMPDIR` environment variable point to `tmp/` in the parent directory of `STAGING_DIR`, which is the collection's `build/tmp/`, and which is created when missing.

The export writes nothing under `$HOME`, and nothing in the `TMPDIR` it inherited. It neither loads nor writes anything in `~/.emacs.d` or `~/.config/emacs`. git, which the bootstrap and the pin check run, may still read its own user configuration.

#### Scenario: Owner's directories and the inherited TMPDIR stay untouched
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` with `HOME` set to a temporary directory that contains only an empty `.config/emacs/`, and `TMPDIR` set to a separate, empty temporary directory with mode 0555
- **THEN** the export exits 0
- **AND** afterwards that `HOME` contains the empty `.config/emacs/` directory and nothing else, in particular no `.emacs.d`
- **AND** the `TMPDIR` directory is still empty

### Requirement: Pinned ox-hugo and tomelr
`tools/export.el` SHALL install tomelr and then ox-hugo into the application's `.emacs-batch/elpa/` with `package-vc-install`, each at its pinned commit and only when that package is not installed. No package archive is configured. The pins are:
- tomelr: `https://github.com/kaushalmodi/tomelr` at `670e0a08f625175fd80137cf69e799619bf8a381` (0.4.3).
- ox-hugo: `https://github.com/kaushalmodi/ox-hugo` at `b7dc44dc28911b9d8e3055a18deac16c3b560b03` (MELPA `20251206.1738`).

On every run, the export compares each installed checkout's `HEAD` with its pin. On a mismatch it exits non-zero, before exporting anything, with a message that names the package, both commits, and `tools/orgsyndb clean --all`.

#### Scenario: Installed checkouts are at the pins
- **WHEN** an integration test reads `git rev-parse HEAD` in `.emacs-batch/elpa/ox-hugo` and `.emacs-batch/elpa/tomelr` after an export
- **THEN** the values are `b7dc44dc28911b9d8e3055a18deac16c3b560b03` and `670e0a08f625175fd80137cf69e799619bf8a381`

#### Scenario: A checkout at another commit stops the export
- **WHEN** an integration test copies `.emacs-batch/` into the application copy instead of linking it, checks out ox-hugo's parent commit in the copy, and runs `tools/orgsyndb -C <collection> export`
- **THEN** the exit status is non-zero, and the output contains `ox-hugo`, `b7dc44dc28911b9d8e3055a18deac16c3b560b03`, the parent commit's hash, and `clean --all`
- **AND** `build/export/` is unchanged

### Requirement: Export plan
`tools/pipeline.py export-plan ORG_ROOT PLAN_JSON` SHALL plan exactly the entries that `validate.discover(ORG_ROOT, ".org")` returns with no problem attached, the files the validator examines as Org procedures. Every other entry, such as a dotfile like the Emacs lock symlink `.#OSDB-0001-x.org`, a subdirectory or a file not ending in `.org`, is left out of the plan and so produces no export. It lints each planned file with the validator's Org keyword lint and then acts as follows:
- If any file has a lint error, it prints the validator-format problem lines to stderr, writes no plan, and exits 1.
- Otherwise it writes `PLAN_JSON` as a JSON array sorted by file name. Each element has `source` (absolute path), `stem` (file name without `.org`), `date` and `lastmod` (RFC 3339 strings), and `ai_model` (the `#+AI_MODEL` value, or `null` when it is `none`).

A missing `ORG_ROOT` yields an empty array.

#### Scenario: Plan for a valid source
- **WHEN** a test runs `export-plan` on a temporary Org root holding a copy of `tests/fixtures/valid/org/OSDB-0003-*.org`
- **THEN** it exits 0, and the plan has one element whose `stem` is that file's stem, whose `date` is `2026-10-19T17:42:05+02:00`, and whose `ai_model` is `null`

#### Scenario: Entries the validator does not examine are not planned
- **WHEN** a test runs `export-plan` on a temporary Org root holding a copy of `tests/fixtures/valid/org/OSDB-0003-*.org`, a dangling symlink named `.#OSDB-0003-x.org`, a regular file `.OSDB-0005-hidden.org`, a subdirectory `nested.org/`, and `notes.txt`
- **THEN** it exits 0, and the plan has exactly one element, the `OSDB-0003` source

#### Scenario: Lint error stops the plan
- **WHEN** a test runs `export-plan` on `tests/fixtures/org-invalid/missing-seconds/org`
- **THEN** it exits 1, stderr contains a line with field `#+CREATED` containing `must have the form [YYYY-MM-DD Day hh:mm:ss]`, and no plan file exists

### Requirement: Exported timestamps
The export SHALL write `date` and `lastmod` with the wall-clock time of `#+CREATED` and `#+LAST_MODIFIED`, seconds included, and a Europe/Berlin UTC offset in force at that instant. Where a time in the autumn fall-back hour names two instants, the choice is made as follows:
- `date` is the earliest instant of `#+CREATED`.
- `lastmod` is the earliest instant of `#+LAST_MODIFIED` that is not earlier than `date`, or the latest instant of `#+LAST_MODIFIED` when there is no such instant.

`pipeline.export_instants(created, last_modified)` implements this choice, and `pipeline.rfc3339(moment)` formats an instant as `YYYY-MM-DDThh:mm:ss+HH:MM` in Europe/Berlin.

#### Scenario: Summer time
- **WHEN** `#+CREATED` is `[2026-10-19 Mon 17:42:05]`
- **THEN** the planned `date` is `2026-10-19T17:42:05+02:00`

#### Scenario: Winter time, last second before the spring change
- **WHEN** `#+CREATED` is `[2026-03-29 Sun 01:59:59]`
- **THEN** the planned `date` is `2026-03-29T01:59:59+01:00`

#### Scenario: Fall-back hour out of wall-clock order
- **WHEN** `#+CREATED` is `[2026-10-25 Sun 02:50:00]` and `#+LAST_MODIFIED` is `[2026-10-25 Sun 02:10:00]`
- **THEN** the planned `date` is `2026-10-25T02:50:00+02:00` and `lastmod` is `2026-10-25T02:10:00+01:00`

#### Scenario: Equal times in the fall-back hour
- **WHEN** `#+CREATED` and `#+LAST_MODIFIED` are both `[2026-10-25 Sun 02:30:00]`
- **THEN** the planned `date` and `lastmod` are both `2026-10-25T02:30:00+02:00`

### Requirement: Exported front matter
The export of each planned Org source `<stem>.org` SHALL be a file `<stem>.md` with `+++` TOML front matter that meets all of the following:
- `date`, `lastmod`, `ai_model`, `slug` and the absence of `author` follow the procedure-schema mapping.
- Every key whose value is a table is written after all other keys, whatever its position among the source's `#+HUGO_CUSTOM_FRONT_MATTER:` lines.
- Every other front-matter key and value is ox-hugo's own output.

Before exporting, the export checks that `org-hugo--gen-front-matter` and `tomelr-toml-table-p` are defined. If either is not, it exits non-zero with a message naming the missing function.

#### Scenario: Seed export validates cleanly
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> export` and then `tools/validate.py --org-root org/procedures build/export md/procedures` in the collection copy
- **THEN** the validator exits 0 and prints nothing to stdout

#### Scenario: Table written first in the source is emitted last
- **WHEN** an integration test exports `tests/fixtures/export/OSDB-0901-table-first.org`, whose first `#+HUGO_CUSTOM_FRONT_MATTER:` line sets `:product` and whose later lines set `:scale`, `:yield_percent`, `:hazards` and `:precursors`
- **THEN** `tomllib` parses its export with `scale`, `yield_percent`, `hazards` and `precursors` as top-level keys
- **AND** the `product` table holds exactly the keys the source's `:product` map gives

#### Scenario: AI model mapping
- **WHEN** an integration test exports one source whose `#+AI_MODEL` is `none` and one whose `#+AI_MODEL` is `example-model-1`
- **THEN** the first export has no `ai_model` key, and the second has `ai_model = "example-model-1"`
- **AND** neither export has an `author` key

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
`tools/orgsyndb export` SHALL leave `build/export/` holding exactly one `<stem>.md` for each planned Org source of `org/procedures/`, and no other file. It uses the sibling directories `build/.export-staging/` and `build/.export-previous/` in these steps:
1. **Recover.** `pipeline.recover_export(build)` runs first, through `pipeline.py recover-export`:
   - If `.export-previous/` exists and `export/` does not, it renames `.export-previous/` to `export/`.
   - If both exist, it deletes `.export-previous/`.
   - It deletes any `.export-staging/`, and empties `build/tmp/`.
2. **Stage.** The export writes into a new, empty `.export-staging/`.
3. **Install.** `pipeline.replace_export(build, rename, remove)` runs, through `pipeline.py install-export`. `rename` defaults to `os.rename` and `remove` to `shutil.rmtree`; both are injectable so that tests can make a step fail:
   1. It checks that the staging directory holds exactly the planned files.
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

