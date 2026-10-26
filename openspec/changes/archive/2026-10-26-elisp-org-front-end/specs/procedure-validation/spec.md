## MODIFIED Requirements

### Requirement: Command-line interface
The validator SHALL be the executable file `tools/validate.py`, invoked as `validate.py [--vocabulary FILE] [--static-dir DIR] CONTENT_ROOT...`, and it SHALL use only the Python standard library.
- Each positional `CONTENT_ROOT` is a directory of procedure Markdown files with `+++` TOML front matter, such as an ox-hugo export directory or `md/procedures/`.
- At least one content root is required.
- It reads no Org source. An Org procedure reaches it only as its export, and the export checks the Org source itself (org-export "Org sources and their problems").
- The module also exposes `main(argv: Sequence[str] | None = None) -> int`, which returns the exit status.

#### Scenario: No roots given
- **WHEN** the validator runs with no `CONTENT_ROOT`
- **THEN** it exits 2 and prints an error to stderr

#### Scenario: Org root option is refused
- **WHEN** the validator runs with `--org-root tests/fixtures/valid/org tests/fixtures/valid/md`
- **THEN** it exits 2, stderr contains `--org-root`, and stdout is empty

#### Scenario: Root is not a directory
- **WHEN** the validator runs on the content root `tests/fixtures/does-not-exist`
- **THEN** it exits 2, and stderr contains `validate.py: error:` and `not a directory`

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/validate.py` with `ast` and collects the top-level module names of every `import` and `from ... import` statement
- **THEN** every name is in `sys.stdlib_module_names`

### Requirement: Problem report format
The validator SHALL print each problem to stdout as one line of the form `<path>:<field>: <severity>: <message>`, where `<severity>` is `error` or `warning`.
- `<path>` is the root argument as given, joined with the entry name.
- `<field>` is the front-matter key, dotted for keys inside `product`. Otherwise it is one of `file_name`, `front_matter` or `body`.
- After the problem lines it prints one summary line to stderr: `validated <F> files: <E> errors, <W> warnings`, where `<F>` counts the Markdown procedure files examined and excludes ignored or rejected entries.
- Entries are examined in sorted path order, and checks run in a fixed order within a file, so identical input yields identical output.

#### Scenario: Line shape
- **WHEN** a fixture run on `invalid/yield-out-of-range` completes
- **THEN** its single stdout line matches `^.+/OSDB-0110-yield-out-of-range\.md:yield_percent: error: .+$`

#### Scenario: Summary line
- **WHEN** the valid-set run completes
- **THEN** stderr contains `validated 4 files: 0 errors, 0 warnings`

#### Scenario: Deterministic output
- **WHEN** the same fixture run on all `invalid/*` roots at once is executed twice
- **THEN** both runs produce byte-identical stdout

### Requirement: File discovery
The validator SHALL examine only the top-level entries of each content root, and it SHALL report every subdirectory of a content root as an error. Hugo publishes nested content, so a subdirectory would otherwise carry unvalidated pages onto the site.
- A subdirectory, whatever its name, is a `file_name` error on the subdirectory's path, containing `subdirectories are not supported`. Its contents are not read.
- A non-directory entry whose name begins with `.`, or a file named `_index.md`, is skipped silently.
- Every other `*.md` file is a procedure.
- Any other file is a `file_name` warning containing `not a procedure file; ignored`.

#### Scenario: Subdirectory in a content root
- **WHEN** a fixture run on `invalid/subdirectory` examines a root whose only entry is the directory `nested/`, holding `OSDB-0135-nested.md`
- **THEN** it reports exactly one error, on the path ending `nested`, field `file_name`, containing `subdirectories are not supported`

#### Scenario: Stray file in a content root
- **WHEN** a fixture run on `warn/stray-file` examines a root holding the valid `OSDB-0156-stray-file.md` and a file `notes.txt`
- **THEN** it reports exactly one warning, on the path ending `notes.txt`, field `file_name`, containing `not a procedure file; ignored`

#### Scenario: Hugo section index and dotfiles are skipped
- **WHEN** a test makes a fixture run on a temporary content root holding a copy of `valid/md/OSDB-0001-*.md` (which lists no precursors), an `_index.md` without front matter, and a `.gitkeep`
- **THEN** it exits 0, prints nothing to stdout, and stderr contains `validated 1 files`

### Requirement: Dependent checks are suppressed
The validator SHALL skip every check that depends on a value whose own check failed, so that one fault yields one error.
- A missing or malformed `id` skips the file-name/ID agreement, the `slug` equality and the duplicate check.
- A `date` or `lastmod` that is not an offset datetime skips the ordering check and the offset warning for that field.
- A `product` that is not a table skips its sub-field checks.
- A `precursors` entry that is not an ID skips its existence check.
- A `structure_image` with the wrong suffix or prefix skips the existence check.

#### Scenario: Malformed ID does not cascade
- **WHEN** a fixture run on `invalid/bad-id-format` examines `OSDB-0102-bad-id-format.md`, whose `id` is `"OSDB-102"` and whose `slug` is `"osdb-0102"`
- **THEN** stdout is exactly one line, it has field `id`, and there is no line for `slug` or `file_name`

### Requirement: Fixture suite
The repository SHALL ship validator fixtures under `tests/fixtures/` and a `unittest` suite under `tests/` that runs with `python3 -m pytest tests` and proves each scenario of both specs. Representative cases are committed fixture files; the remaining field variations are written by the tests as variants of a committed baseline. The scenarios of the procedure-schema spec that are stated as ERT tests are proved by the ERT suite of the org-export spec, which `python3 -m pytest tests` runs.

The terms used in the scenarios are defined as follows:
- **Fixture run.** A fixture run on roots R runs `tools/validate.py --vocabulary tests/fixtures/reaction_types.toml --static-dir tests/fixtures/static` with roots R, relative to `tests/fixtures/`.
- **Valid-set run.** The valid-set run is a fixture run on `valid/md` and `valid/export`.
- **Variant run.** A variant run writes `tests/fixtures/baseline/OSDB-0100-baseline.md`, with the stated textual change applied and under the stated file name, as the only file of a fresh temporary content root, then makes a fixture run on that root.
- **"Reports exactly one error with field F containing T".** This means exit status 1 and exactly one stdout line, which has field F, severity `error`, and a message containing T. "Reports exactly one warning" means the same with severity `warning` and exit status 0.

The committed fixtures are these:
- `reaction_types.toml` (holding at least `esterification` and `reduction`, and not `reductive-amination`), `bad-vocabulary.toml` and `static/structures/osdb-0001.svg`.
- `baseline/OSDB-0100-baseline.md`: required fields only, `reaction_types = ["esterification"]`, all eight sections, one front-matter key per line, and `[product]` as the last table.
- `valid/md/` holds `OSDB-0001-*.md` and `OSDB-0002-*.md`. `valid/org/` holds `OSDB-0003-*.org` and `OSDB-0004-ambiguous-hour.org`, which the ERT suite and the export tests read. `valid/export/` holds their exports in ox-hugo's form, with the same stems.
- `invalid/`: one directory per case. The cases are `invalid-toml`, `bad-id-format`, `file-name-id-mismatch`, `slug-mismatch`, `missing-title`, `unknown-reaction-type`, `yield-out-of-range`, `date-as-string`, `missing-precursor`, `missing-structure-image`, `author-key`, `subdirectory`, and `duplicate-id` (two roots, `a/` and `b/`).
- `warn/`: `missing-section`, `offset` and `stray-file`.
- `org-invalid/`: one directory per Org-source case that the procedure-schema and org-export specs name with a committed fixture, `subdirectory` included, each holding the case's Org directory `org/`.

Procedure IDs are unique across the committed fixtures outside `collection/`, the test collection that the sample-procedures spec defines, whose procedures carry the demo collection's IDs. The exceptions are the duplicate-ID case and an Org source of `valid/org/` paired with its export in `valid/export/`. Names are fictitious, and no committed fixture file contains a user or machine identifier. The identifier check reads every file under `tests/fixtures/` except those under `collection/build/`, `collection/public/` and `collection/pdf/`, which a run of `tools/orgsyndb` on the test collection in place would generate.

#### Scenario: Committed IDs are unique
- **WHEN** a test reads the `id` of every Markdown file under `tests/fixtures/` outside `invalid/duplicate-id/` and `collection/`
- **THEN** no `id` occurs twice

#### Scenario: Committed fixtures carry no identifiers
- **WHEN** a test reads every file under `tests/fixtures/` outside `collection/build/`, `collection/public/` and `collection/pdf/` as UTF-8
- **THEN** none contains `/home/`, an `@` followed by a dotted host name, `.local` or `.lan`

#### Scenario: Valid set passes cleanly
- **WHEN** the valid-set run completes
- **THEN** it exits 0 and prints nothing to stdout
- **AND** the valid set covers every optional field, a `date` with a `+01:00` offset in winter and one with `+02:00` in summer, and the ambiguous autumn hour

#### Scenario: Baseline is valid
- **WHEN** a fixture run on `baseline` completes
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Each committed invalid fixture fails for one reason
- **WHEN** each directory under `tests/fixtures/invalid/` except `duplicate-id` is used as the single root of its own fixture run
- **THEN** each run reports exactly one error, with the field and message given by its scenario
- **AND** there are at least five such directories

## REMOVED Requirements

### Requirement: Org sources are cross-checked against their export
**Reason**: The cross-check guarded against an export whose `date`, `lastmod` or `ai_model` differed from its Org source's keywords. That can no longer happen. Emacs computes the three values from `#+CREATED`, `#+LAST_MODIFIED` and `#+AI_MODEL` and writes them into the export in the same run. It also refuses, before exporting, every source that could set them, or the export's file name, by another route that ox-hugo reads (procedure-schema "Exported values come only from the file-level keywords"). The export step checks that the staging directory holds exactly one `<stem>.md` per Org source (org-export "Complete and fresh export directory"), which covers a missing export. The validator reads no Org source.
