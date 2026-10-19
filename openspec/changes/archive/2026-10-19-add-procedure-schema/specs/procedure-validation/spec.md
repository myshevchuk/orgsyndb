## ADDED Requirements

<!-- "Fixture run", "variant run", "valid-set run" and "reports exactly one
error/warning" are defined in the "Fixture suite" requirement below and
used the same way in the procedure-schema spec. -->

### Requirement: Command-line interface
The validator SHALL be the executable file `tools/validate.py`, invoked as `validate.py [--org-root DIR]... [--vocabulary FILE] [--static-dir DIR] [CONTENT_ROOT ...]`, and it SHALL use only the Python standard library.
- Each positional `CONTENT_ROOT` is a directory of procedure Markdown files with `+++` TOML front matter, such as an ox-hugo export directory or `md/procedures/`.
- Each `--org-root` is a directory of Org procedure sources.
- At least one root of either kind is required.
- The module also exposes `main(argv: Sequence[str] | None = None) -> int`, which returns the exit status.

#### Scenario: No roots given
- **WHEN** the validator runs with no `CONTENT_ROOT` and no `--org-root`
- **THEN** it exits 2 and prints an error to stderr

#### Scenario: Root is not a directory
- **WHEN** the validator runs on the content root `tests/fixtures/does-not-exist`
- **THEN** it exits 2, and stderr contains `validate.py: error:` and `not a directory`

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/validate.py` with `ast` and collects the top-level module names of every `import` and `from ... import` statement
- **THEN** every name is in `sys.stdlib_module_names`

### Requirement: Default paths resolve from the script location
When `--vocabulary` or `--static-dir` is omitted, the validator SHALL use `<repo>/site/data/reaction_types.toml` and `<repo>/site/static` respectively, where `<repo>` is the parent of the directory containing the resolved `validate.py`, independent of the working directory. A static directory that does not exist is not a configuration error; it only makes every `structure_image` unresolvable.

#### Scenario: Run from an unrelated working directory
- **WHEN** a test runs `<repo>/tools/validate.py` as a subprocess, with `cwd` set to an empty temporary directory and without `--vocabulary`, on a temporary content root holding one procedure whose `reaction_types` is `["reductive-amination"]`
- **AND** `reductive-amination` is a key of the shipped vocabulary but not of `tests/fixtures/reaction_types.toml`
- **THEN** it reports no `reaction_types` problem and exits 0

### Requirement: Vocabulary file errors are configuration errors
The validator SHALL exit with status 2, writing `validate.py: error:` and a message to stderr, when any of these holds:
- the vocabulary file is missing;
- it is not valid TOML;
- it has a top-level key that is not a slug;
- it has an entry that is not a table with a non-empty string `label`;
- the `Europe/Berlin` time zone cannot be loaded.

#### Scenario: Entry without a label
- **WHEN** the validator runs with `--vocabulary tests/fixtures/bad-vocabulary.toml`, whose entry `[reduction]` has no `label`, on the content root `valid/md`
- **THEN** it exits 2, stderr contains `label`, and stdout is empty

#### Scenario: Missing vocabulary file
- **WHEN** the validator runs with `--vocabulary tests/fixtures/no-such-vocabulary.toml` on the content root `valid/md`
- **THEN** it exits 2, and stderr contains `validate.py: error:`

### Requirement: Problem report format
The validator SHALL print each problem to stdout as one line of the form `<path>:<field>: <severity>: <message>`, where `<severity>` is `error` or `warning`.
- `<path>` is the root argument as given, joined with the entry name.
- `<field>` is the front-matter key, dotted for keys inside `product`, or the keyword including `#+` for Org keyword lints. Otherwise it is one of `file_name`, `front_matter` or `body`.
- After the problem lines it prints one summary line to stderr: `validated <F> files: <E> errors, <W> warnings`, where `<F>` counts the procedure files examined (`.md` in content roots, `.org` in Org roots) and excludes ignored or rejected entries.
- Entries are examined in sorted path order, and checks run in a fixed order within a file, so identical input yields identical output.

#### Scenario: Line shape
- **WHEN** a fixture run on `invalid/yield-out-of-range` completes
- **THEN** its single stdout line matches `^.+/OSDB-0110-yield-out-of-range\.md:yield_percent: error: .+$`

#### Scenario: Summary line
- **WHEN** the valid-set run completes
- **THEN** stderr contains `validated 6 files: 0 errors, 0 warnings`

#### Scenario: Deterministic output
- **WHEN** the same fixture run on all `invalid/*` roots at once is executed twice
- **THEN** both runs produce byte-identical stdout

### Requirement: Exit status
The validator SHALL exit with status 0 when it found no errors, even if it printed warnings. It exits with status 1 when it found at least one error, and with status 2 on a usage or configuration error.

#### Scenario: Warnings alone do not fail
- **WHEN** a fixture run on `warn/missing-section` completes
- **THEN** the exit status is 0, although stdout contains one warning

#### Scenario: Any error fails
- **WHEN** a fixture run on `invalid/unknown-reaction-type` completes
- **THEN** the exit status is 1

### Requirement: File discovery
The validator SHALL examine only the top-level entries of each root, and it SHALL report every subdirectory of a root as an error. Hugo publishes nested content, so a subdirectory would otherwise carry unvalidated pages onto the site.
- A subdirectory, whatever its name, is a `file_name` error on the subdirectory's path, containing `subdirectories are not supported`. Its contents are not read.
- A non-directory entry whose name begins with `.`, or a file named `_index.md`, is skipped silently.
- Every other `*.md` file in a content root, and every other `*.org` file in an Org root, is a procedure.
- Any other file is a `file_name` warning containing `not a procedure file; ignored`.

#### Scenario: Subdirectory in a content root
- **WHEN** a fixture run on `invalid/subdirectory` examines a root whose only entry is the directory `nested/`, holding `OSDB-0135-nested.md`
- **THEN** it reports exactly one error, on the path ending `nested`, field `file_name`, containing `subdirectories are not supported`

#### Scenario: Subdirectory in an Org root
- **WHEN** the validator runs with only `--org-root org-invalid/subdirectory/org`, whose only entry is the directory `nested/`, holding `OSDB-0215-nested.org`
- **THEN** it reports exactly one error, on the path ending `nested`, field `file_name`, containing `subdirectories are not supported`

#### Scenario: Stray file in a content root
- **WHEN** a fixture run on `warn/stray-file` examines a root holding the valid `OSDB-0156-stray-file.md` and a file `notes.txt`
- **THEN** it reports exactly one warning, on the path ending `notes.txt`, field `file_name`, containing `not a procedure file; ignored`

#### Scenario: Hugo section index and dotfiles are skipped
- **WHEN** a test makes a fixture run on a temporary content root holding a copy of `valid/md/OSDB-0001-*.md` (which lists no precursors), an `_index.md` without front matter, and a `.gitkeep`
- **THEN** it exits 0, prints nothing to stdout, and stderr contains `validated 1 files`

### Requirement: Front-matter parsing
The validator SHALL read each content file as UTF-8, tolerating a byte-order mark, and parse its front matter with `tomllib`. The front matter starts at a first line `+++` and ends at the next line `+++`; trailing whitespace and carriage returns are tolerated on both delimiter lines. The text after the closing delimiter is the body.
- A file that does not start with a `+++` line, lacks the closing delimiter, is not UTF-8 or fails to parse gets a single `front_matter` error.
- Such a file contributes no ID to the duplicate and precursor checks, and gets no further checks.

#### Scenario: YAML front matter instead of TOML
- **WHEN** a variant run replaces both `+++` delimiter lines with `---` under the file name `OSDB-0100-no-front-matter.md`
- **THEN** it reports exactly one error, field `front_matter`, containing `must begin with a +++ line`

#### Scenario: Unparseable TOML
- **WHEN** a fixture run on `invalid/invalid-toml` examines `OSDB-0134-invalid-toml.md`, whose front matter contains an unterminated string
- **THEN** it reports exactly one error, field `front_matter`, containing `invalid TOML`

### Requirement: Dependent checks are suppressed
The validator SHALL skip every check that depends on a value whose own check failed, so that one fault yields one error.
- A missing or malformed `id` skips the file-name/ID agreement, the `slug` equality and the duplicate check.
- A `date` or `lastmod` that is not an offset datetime skips the ordering check, the offset warning and the Org cross-check for that field.
- A `product` that is not a table skips its sub-field checks.
- A `precursors` entry that is not an ID skips its existence check.
- A `structure_image` with the wrong suffix or prefix skips the existence check.
- An Org timestamp that is malformed or not a valid date skips its weekday, existence, ordering and cross-checks.

#### Scenario: Malformed ID does not cascade
- **WHEN** a fixture run on `invalid/bad-id-format` examines `OSDB-0102-bad-id-format.md`, whose `id` is `"OSDB-102"` and whose `slug` is `"osdb-0102"`
- **THEN** stdout is exactly one line, it has field `id`, and there is no line for `slug` or `file_name`

#### Scenario: Invalid date does not cascade
- **WHEN** the validator runs with `--org-root org-invalid/invalid-date/org` on `OSDB-0205-invalid-date.org`, whose `#+CREATED` is `[2026-02-30 Mon 10:00:00]`
- **THEN** stdout is exactly one line, and it contains neither `weekday` nor `earlier than`

### Requirement: Org sources are cross-checked against their export
When at least one content root and at least one Org root are given, the validator SHALL pair each Org source `X.org` with the content file `X.md` of the same stem in any content root, and apply the mapping rules of the procedure-schema spec to the pair.
- An Org source with no such content file gets a `file_name` error containing `no exported content file`.
- The cross-check detects only a missing export and a mismatch in `date`, `lastmod` or `ai_model`. It does not detect an export that is out of date in other fields, or an export whose Org source has been deleted.
- Problems found by the cross-check are reported on the Org source's path.
- When only Org roots are given, the cross-check does not run.

#### Scenario: Export missing
- **WHEN** a fixture run on `org-invalid/missing-export/export`, which holds only a `.gitkeep`, with `--org-root org-invalid/missing-export/org`, examines `OSDB-0214-missing-export.org`
- **THEN** it reports exactly one error, on the `.org` path, field `file_name`, containing `no exported content file`

#### Scenario: Lint-only run skips the cross-check
- **WHEN** the validator runs with only `--org-root valid/org`
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Fixture suite
The repository SHALL ship validator fixtures under `tests/fixtures/` and a `unittest` suite under `tests/` that runs with `python3 -m pytest tests` and proves each scenario of both specs. Representative cases are committed fixture files; the remaining field variations are written by the tests as variants of a committed baseline.

The terms used in the scenarios are defined as follows:
- **Fixture run.** A fixture run on roots R runs `tools/validate.py --vocabulary tests/fixtures/reaction_types.toml --static-dir tests/fixtures/static` with roots R, relative to `tests/fixtures/`.
- **Valid-set run.** The valid-set run is a fixture run on `valid/md` and `valid/export` with `--org-root valid/org`.
- **Variant run.** A variant run writes `tests/fixtures/baseline/OSDB-0100-baseline.md`, with the stated textual change applied and under the stated file name, as the only file of a fresh temporary content root, then makes a fixture run on that root.
- **"Reports exactly one error with field F containing T".** This means exit status 1 and exactly one stdout line, which has field F, severity `error`, and a message containing T. "Reports exactly one warning" means the same with severity `warning` and exit status 0.

The committed fixtures are these:
- `reaction_types.toml` (holding at least `esterification` and `reduction`, and not `reductive-amination`), `bad-vocabulary.toml` and `static/structures/osdb-0001.svg`.
- `baseline/OSDB-0100-baseline.md`: required fields only, `reaction_types = ["esterification"]`, all eight sections, one front-matter key per line, and `[product]` as the last table.
- `valid/md/` holds `OSDB-0001-*.md` and `OSDB-0002-*.md`. `valid/org/` holds `OSDB-0003-*.org` and `OSDB-0004-ambiguous-hour.org`. `valid/export/` holds their ox-hugo-shaped exports, with the same stems.
- `invalid/`: one directory per case. The cases are `invalid-toml`, `bad-id-format`, `file-name-id-mismatch`, `slug-mismatch`, `missing-title`, `unknown-reaction-type`, `yield-out-of-range`, `date-as-string`, `missing-precursor`, `missing-structure-image`, `author-key`, `subdirectory`, and `duplicate-id` (two roots, `a/` and `b/`).
- `warn/`: `missing-section`, `offset` and `stray-file`.
- `org-invalid/`: every Org lint and cross-check case named in either spec, including `subdirectory`.

Procedure IDs are unique across the committed fixtures. The exceptions are the duplicate-ID case and an Org source paired with its own export. Names are fictitious, and no user or machine identifier appears.

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
