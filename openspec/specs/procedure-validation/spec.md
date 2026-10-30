# procedure-validation Specification

## Purpose
Define how `tools/validate.py` is invoked on Markdown content roots, what it reports and in which format, its exit statuses, and the fixture suite that proves each rejection.
## Requirements
### Requirement: Command-line interface
The validator SHALL be the executable file `tools/validate.py`, invoked as `validate.py [--vocabulary FILE] [--static-dir DIR] [--compounds DIR] [--sequences DIR] CONTENT_ROOT...`, and it SHALL use only the Python standard library.
- Each positional `CONTENT_ROOT` is a directory of procedure Markdown files with `+++` TOML front matter, such as an ox-hugo export directory or `md/procedures/`.
- At least one content root is required.
- `--sequences` names the directory of synthesis sequences (synthesis-sequences "Sequence files"). The validator checks every sequence in it against the procedures of the content roots and the compound registry.
- `--compounds` names the compound registry (compound-registry "Compound files"). The validator checks every compound file in it and resolves every compound key of the procedures against the compounds it defines.
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

### Requirement: Default paths resolve from the script location
When `--vocabulary` is omitted, the validator SHALL use `<app>/site/data/reaction_types.toml`, where `<app>` is the parent of the directory containing the resolved `validate.py`, independent of the working directory. When `--static-dir` is omitted, it SHALL use `static` in the working directory, the location of a collection's static files when run from the collection's root. A static directory that does not exist is not a configuration error; it only makes every `structure_image` unresolvable. When `--compounds` is omitted, it SHALL use `compounds` in the working directory, the location of a collection's registry when run from the collection's root. A registry directory that does not exist is not a configuration error either; it defines no compound, so every compound key is unknown. When `--sequences` is omitted, it SHALL use `md/sequences` in the working directory; a sequences directory that does not exist holds no sequence.

#### Scenario: Run from an unrelated working directory
- **WHEN** a test runs `<app>/tools/validate.py` as a subprocess, with `cwd` set to an empty temporary directory and without `--vocabulary`, on a temporary content root holding one procedure whose `reaction_types` is `["reductive-amination"]`, with `--compounds <app>/tests/fixtures/compounds` and `--static-dir <app>/tests/fixtures/static`
- **AND** `reductive-amination` is a key of the shipped vocabulary but not of `tests/fixtures/reaction_types.toml`
- **THEN** it reports no `reaction_types` problem and exits 0

#### Scenario: Default static and registry directories are the working directory's
- **WHEN** a test runs `<app>/tools/validate.py` without `--static-dir` and `--compounds`, with `cwd` set to a temporary directory holding `static/structures/ethyl-acetate.svg`, a `compounds/ethyl-acetate.toml` that sets `structure_image = "structures/ethyl-acetate.svg"`, and a content root whose one procedure is the baseline
- **THEN** it reports no problem and exits 0

#### Scenario: Missing registry
- **WHEN** a test runs the validator with `--compounds tests/fixtures/no-such-registry` on the content root `baseline`
- **THEN** it exits 1, and its one stdout line has field `products[1].compound` and contains `unknown compound "ethyl-acetate"`

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
- `<path>` is the root argument as given, joined with the entry name; for a compound file, the `--compounds` argument as given, joined with the file name; for a sequence, the `--sequences` argument as given, joined with the file name.
- `<field>` is the front-matter key, or `products[n].<key>` for a key inside the `n`-th product (procedure-schema "Products"), or `scope[n].<key>` and `scope[n].products[m].<key>` for a key inside the `n`-th scope entry and its `m`-th product (general-procedures "Scope entries"). For a compound file it is the key in the file; for a sequence, its front-matter key, or `steps[n].<key>` for a key inside its `n`-th step. Otherwise it is one of `file_name`, `front_matter`, `toml` or `body`.
- After the problem lines it prints one summary line to stderr: `validated <F> files: <E> errors, <W> warnings`, where `<F>` counts the Markdown procedure files, the compound files and the sequence files examined and excludes ignored or rejected entries.
- Entries are examined in sorted path order, and checks run in a fixed order within a file, so identical input yields identical output.

#### Scenario: Line shape
- **WHEN** a fixture run on `invalid/yield-out-of-range` completes
- **THEN** its single stdout line matches `^.+/OSDB-0110-yield-out-of-range\.md:products\[1\]\.yield_percent: error: .+$`

#### Scenario: Summary line
- **WHEN** the valid-set run completes
- **THEN** stderr contains `validated <F> files: 0 errors, 0 warnings`, where `<F>` is 4 plus the number of compound files in `tests/fixtures/compounds/`

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
- **WHEN** a test makes a fixture run on a temporary content root holding a copy of `valid/md/OSDB-0001-*.md`, an `_index.md` without front matter, and a `.gitkeep`
- **THEN** it exits 0, prints nothing to stdout, and stderr counts one procedure file besides the compound files

### Requirement: Front-matter parsing
The validator SHALL read each content file as UTF-8, tolerating a byte-order mark, and parse its front matter with `tomllib`. The front matter starts at a first line `+++` and ends at the next line `+++`; trailing whitespace and carriage returns are tolerated on both delimiter lines. The text after the closing delimiter is the body.
- A file that does not start with a `+++` line, lacks the closing delimiter, is not UTF-8 or fails to parse gets a single `front_matter` error.
- Such a file contributes no ID to the duplicate check, and gets no further checks.

#### Scenario: YAML front matter instead of TOML
- **WHEN** a variant run replaces both `+++` delimiter lines with `---` under the file name `OSDB-0100-no-front-matter.md`
- **THEN** it reports exactly one error, field `front_matter`, containing `must begin with a +++ line`

#### Scenario: Unparseable TOML
- **WHEN** a fixture run on `invalid/invalid-toml` examines `OSDB-0134-invalid-toml.md`, whose front matter contains an unterminated string
- **THEN** it reports exactly one error, field `front_matter`, containing `invalid TOML`

### Requirement: Dependent checks are suppressed
The validator SHALL skip every check that depends on a value whose own check failed, so that one fault yields one error.
- A missing or malformed `id` skips the file-name/ID agreement, the `slug` equality and the duplicate check.
- A `date` or `lastmod` that is not an offset datetime skips the ordering check and the offset warning for that field.
- A `products` entry that is not a table skips its sub-field checks, and a `compound` that is not a string skips its registry lookup.
- A compound's `structure_image` with the wrong suffix or prefix skips the existence check.

#### Scenario: Malformed ID does not cascade
- **WHEN** a fixture run on `invalid/bad-id-format` examines `OSDB-0102-bad-id-format.md`, whose `id` is `"OSDB-102"` and whose `slug` is `"osdb-0102"`
- **THEN** stdout is exactly one line, it has field `id`, and there is no line for `slug` or `file_name`

### Requirement: Fixture suite
The repository SHALL ship validator fixtures under `tests/fixtures/` and a `unittest` suite under `tests/` that runs with `python3 -m pytest tests` and proves each scenario of both specs. Representative cases are committed fixture files; the remaining field variations are written by the tests as variants of a committed baseline. The scenarios of the procedure-schema spec that are stated as ERT tests are proved by the ERT suite of the org-export spec, which `python3 -m pytest tests` runs.

The terms used in the scenarios are defined as follows:
- **Fixture run.** A fixture run on roots R runs `tools/validate.py --vocabulary tests/fixtures/reaction_types.toml --static-dir tests/fixtures/static --compounds tests/fixtures/compounds` with roots R, relative to `tests/fixtures/`.
- **Valid-set run.** The valid-set run is a fixture run on `valid/md` and `valid/export`.
- **Variant run.** A variant run writes `tests/fixtures/baseline/OSDB-0100-baseline.md`, with the stated textual change applied and under the stated file name, as the only file of a fresh temporary content root, then makes a fixture run on that root.
- **Sequence fixture run.** A sequence fixture run on roots R is a fixture run on R and `general` with `--sequences` naming the stated directory, relative to `tests/fixtures/`.
- **Sequence variant run.** A sequence variant run copies `tests/fixtures/sequences/` to a fresh temporary directory, applies the stated change to the named sequence there, and makes a sequence fixture run on `valid/md` and `sequences-procedures` with that directory.
- **Registry variant run.** A registry variant run copies `tests/fixtures/compounds/` to a fresh temporary directory, applies the stated change to the files there, and makes a fixture run on `baseline` with `--compounds` set to that directory. "Reports exactly one" then counts the stdout lines of the whole run, compound files and procedures together.
- **"Reports exactly one error with field F containing T".** This means exit status 1 and exactly one stdout line, which has field F, severity `error`, and a message containing T. "Reports exactly one warning" means the same with severity `warning` and exit status 0.

The committed fixtures are these:
- `reaction_types.toml` (holding at least `esterification` and `reduction`, and not `reductive-amination`), `bad-vocabulary.toml` and `static/structures/ethyl-acetate.svg`.
- `compounds/`: the fixture registry, holding a valid file for every compound key that a committed fixture outside `invalid/` and `collection/` names, `ethyl-acetate` and `ethanol` among them, and no other file. `ethyl-acetate.toml` sets every optional key, `structure_image = "structures/ethyl-acetate.svg"` included.
- `baseline/OSDB-0100-baseline.md`: required fields only, `reaction_types = ["esterification"]`, `products = [{ compound = "ethyl-acetate", yield_percent = 85 }]`, all eight sections, and one front-matter key per line.
- `valid/md/` holds `OSDB-0001-*.md` and `OSDB-0002-*.md`. `valid/org/` holds `OSDB-0003-*.org` and `OSDB-0004-ambiguous-hour.org`, which the ERT suite and the export tests read. `valid/export/` holds their exports in ox-hugo's form, with the same stems.
- `invalid/`: one directory per case. The cases are `invalid-toml`, `bad-id-format`, `file-name-id-mismatch`, `slug-mismatch`, `missing-title`, `unknown-reaction-type`, `yield-out-of-range`, `date-as-string`, `unknown-compound`, `unknown-substrate`, `author-key`, `subdirectory`, and `duplicate-id` (two roots, `a/` and `b/`).
- `warn/`: `missing-section`, `offset` and `stray-file`.
- `sequences/`: valid sequences over the procedures of `valid/md`, `sequences-procedures/` and `general/`, one of them with a step naming entry 2 of the general baseline; `sequences-procedures/`: the procedures that make the committed sequences chain; `sequences-invalid/file-name/`: `SEQ-0002-mismatch.md`, whose `id` is `SEQ-0003`.
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
- **AND** the valid set covers every optional field, a procedure with two products, a `date` with a `+01:00` offset in winter and one with `+02:00` in summer, and the ambiguous autumn hour

#### Scenario: Baseline is valid
- **WHEN** a fixture run on `baseline` completes
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Each committed invalid fixture fails for one reason
- **WHEN** each directory under `tests/fixtures/invalid/` except `duplicate-id` is used as the single root of its own fixture run
- **THEN** each run reports exactly one error, with the field and message given by its scenario
- **AND** there are at least five such directories

