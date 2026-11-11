# procedure-validation Specification

## Purpose
Define how `tools/validate.py` is invoked on Markdown content roots, what it reports and in which format, its exit statuses, and the fixture suite that proves each rejection.
## Requirements
### Requirement: Command-line interface
The validator SHALL be the executable file `tools/validate.py`, invoked as `validate.py [--settings FILE] [--static-dir DIR] [--registry FILE] [--sequences DIR] CONTENT_ROOT...`, and it SHALL use only the Python standard library.
- Each positional `CONTENT_ROOT` is a directory of procedure Markdown files with `+++` TOML front matter, such as an ox-hugo export directory or `md/procedures/`.
- At least one content root is required.
- `--sequences` names the directory of synthesis sequences (synthesis-sequences "Sequence files"). The validator checks every sequence in it against the procedures of the content roots and the registry.
- `--registry` names the collection's registry, a snapshot file (compound-registry "Registry checks"). The validator resolves every compound key of the procedures and sequences against its substances, and takes the reaction types and the vocabularies of procedure fields from it.
- `--settings` names the collection's settings file, its `orgsyndb.toml` (collection "Collection layout"). The validator applies the rules that requirement states for `format` and the top-level keys, reads only `fields` beyond them, checks the procedure declarations against the registry's vocabularies (procedure-fields "Procedure field declarations"), and checks every procedure of the content roots against the procedure fields (procedure-fields "Procedure field values"). The validator takes no option naming a vocabulary or a compound directory.
- It reads no Org source. An Org procedure reaches it only as its export, and the export checks the Org source itself (org-export "Org sources and their problems").
- The module also exposes `main(argv: Sequence[str] | None = None) -> int`, which returns the exit status.

#### Scenario: No roots given
- **WHEN** the validator runs with no `CONTENT_ROOT`
- **THEN** it exits 2 and prints an error to stderr

#### Scenario: Org root option is refused
- **WHEN** the validator runs with `--org-root tests/fixtures/valid/org tests/fixtures/valid/md`
- **THEN** it exits 2, stderr contains `--org-root`, and stdout is empty

#### Scenario: Vocabulary and compound options are refused
- **WHEN** the validator runs with `--vocabulary reaction-types.toml tests/fixtures/valid/md`, and separately with `--compounds tests/fixtures tests/fixtures/valid/md`
- **THEN** each exits 2, stderr contains `--vocabulary` and `--compounds` respectively, and stdout is empty

#### Scenario: Root is not a directory
- **WHEN** the validator runs on the content root `tests/fixtures/does-not-exist`
- **THEN** it exits 2, and stderr contains `validate.py: error:` and `not a directory`

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/validate.py` with `ast` and collects the top-level module names of every `import` and `from ... import` statement
- **THEN** every name is in `sys.stdlib_module_names`

### Requirement: Problem report format
The validator SHALL print each problem to stdout as one line of the form `<path>:<field>: <severity>: <message>`, where `<severity>` is `error` or `warning`.
- `<path>` is the root argument as given, joined with the entry name; for the registry, the `--registry` argument as given; for a sequence, the `--sequences` argument as given, joined with the file name.
- `<field>` is the front-matter key, or `products[n].<key>` for a key inside the `n`-th product (procedure-schema "Products"), or `scope[n].<key>` and `scope[n].products[m].<key>` for a key inside the `n`-th scope entry and its `m`-th product (general-procedures "Scope entries"). For the registry it is `substances`; for a sequence, its front-matter key, or `steps[n].<key>` for a key inside its `n`-th step. Otherwise it is one of `file_name`, `front_matter`, `toml` or `body`.
- After the problem lines it prints one summary line to stderr: `validated <F> files: <E> errors, <W> warnings`, where `<F>` counts the Markdown procedure files and the sequence files examined and excludes ignored or rejected entries.
- Entries are examined in sorted path order, and checks run in a fixed order within a file, so identical input yields identical output.

#### Scenario: Line shape
- **WHEN** a fixture run on `invalid/yield-out-of-range` completes
- **THEN** its single stdout line matches `^.+/OSDB-0110-yield-out-of-range\.md:products\[1\]\.yield_percent: error: .+$`

#### Scenario: Summary line
- **WHEN** the valid-set run completes
- **THEN** stderr contains `validated 4 files: 0 errors, 0 warnings`

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
- **THEN** it exits 0, prints nothing to stdout, and stderr counts one file

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

#### Scenario: Malformed ID does not cascade
- **WHEN** a fixture run on `invalid/bad-id-format` examines `OSDB-0102-bad-id-format.md`, whose `id` is `"OSDB-102"` and whose `slug` is `"osdb-0102"`
- **THEN** stdout is exactly one line, it has field `id`, and there is no line for `slug` or `file_name`

### Requirement: Fixture suite
The repository SHALL ship validator fixtures under `tests/fixtures/` and a `unittest` suite under `tests/` that runs with `python3 -m pytest tests` and proves each scenario of both specs. Representative cases are committed fixture files; the remaining field variations are written by the tests as variants of a committed baseline. The scenarios of the procedure-schema spec that are stated as ERT tests are proved by the ERT suite of the org-export spec, which `python3 -m pytest tests` runs.

The terms used in the scenarios are defined as follows:
- **Fixture run.** A fixture run on roots R runs `tools/validate.py --settings tests/fixtures/settings/orgsyndb.toml --static-dir tests/fixtures/static --registry tests/fixtures/registry.json` with roots R, relative to `tests/fixtures/`. Its reaction types, the fixture reaction types, are those of the fixture registry, `tests/fixtures/registry.json`.
- **Valid-set run.** The valid-set run is a fixture run on `valid/md` and `valid/export`.
- **Variant run.** A variant run writes `tests/fixtures/baseline/OSDB-0100-baseline.md`, with the stated textual change applied and under the stated file name, as the only file of a fresh temporary content root, then makes a fixture run on that root.
- **Sequence fixture run.** A sequence fixture run on roots R is a fixture run on R and `general` with `--sequences` naming the stated directory, relative to `tests/fixtures/`.
- **Sequence variant run.** A sequence variant run copies `tests/fixtures/sequences/` to a fresh temporary directory, applies the stated change to the named sequence there, and makes a sequence fixture run on `valid/md` and `sequences-procedures` with that directory.
- **Registry variant run.** A registry variant run copies the fixture registry to a fresh temporary directory, applies the stated change to the copy, and makes a fixture run on `baseline` with `--registry` naming the copy. "Reports exactly one" then counts the stdout lines of the whole run, the registry and procedures together.
- **Settings variant run.** A settings variant run on roots R copies `tests/fixtures/settings/` to a fresh temporary directory, applies the stated change to the files there, and makes a fixture run on R with `--settings` naming the copy of `orgsyndb.toml`. "Reports exactly one" counts the stdout lines of the whole run.
- **"Reports exactly one error with field F containing T".** This means exit status 1 and exactly one stdout line, which has field F, severity `error`, and a message containing T. "Reports exactly one warning" means the same with severity `warning` and exit status 0.

The committed fixtures are these:
- `settings/`: a settings file `orgsyndb.toml` holding `format = 1` and nothing else, and no other file.
- `registry.json`: the fixture registry, a snapshot (lab-registry "Snapshot") holding a substance for every compound key that a committed fixture outside `invalid/` and `collection/` names, `ethyl-acetate` and `ethanol` among them, and no other; the reaction types `esterification` (`Esterification`) and `reduction` (`Reduction`) and no other; the projects `teaching` (`Teaching`, `Lehre`), `first-year-practical` (`First-year practical`, `Grundpraktikum`), filed under `teaching`, and `research` (`Research`, `Forschung`); the group `reagents` (`Reagents`) and the chemical class `organic-compounds` (`Organic compounds`), which every fixture substance has, and no other group or chemical class. No fixture substance has an article number or a short name.
- `static/structures/ethyl-acetate.svg`.
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

#### Scenario: The fixture settings match their description
- **WHEN** a test reads `tests/fixtures/settings/`
- **THEN** `orgsyndb.toml` parses to `{"format": 1}`, the directory holds no other file, the fixture registry's reaction types are exactly the two stated, and neither `tests/fixtures/compounds/` nor `tests/fixtures/fields/` exists

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

### Requirement: Default paths come from the working directory
When `--static-dir` is omitted, the validator SHALL use `static` in the working directory, the location of a collection's static files when run from the collection's root. A static directory that does not exist is not a configuration error; it only makes every image path a procedure names unresolvable. When `--registry` is omitted, it SHALL use `build/registry.json` in the working directory, where the collection's tools leave the registry they read (compound-registry "Reading the registry"); a registry file that does not exist is a configuration error (Registry errors are configuration errors). When `--sequences` is omitted, it SHALL use `md/sequences` in the working directory; a sequences directory that does not exist holds no sequence. When `--settings` is omitted, it SHALL use `orgsyndb.toml` in the working directory, the settings file of a collection when run from the collection's root. A settings file that does not exist declares no field when `--settings` is omitted; a settings file that `--settings` names and that does not exist is a configuration error (procedure-fields "Procedure declaration errors are configuration errors").

#### Scenario: Default static and registry directories are the working directory's
- **WHEN** a test runs `<app>/tools/validate.py` without `--static-dir` and `--registry`, with `cwd` set to a temporary directory holding `static/structures/ethyl-acetate.svg`, `build/registry.json`, a copy of the fixture registry, and a content root whose one procedure is the baseline
- **THEN** it reports no problem and exits 0

#### Scenario: Missing registry
- **WHEN** a fixture run on `baseline` names `--registry tests/fixtures/no-such-registry.json`
- **THEN** it exits 2, stdout is empty, and stderr contains `validate.py: error:` and `no-such-registry.json`

#### Scenario: Default settings file is the working directory's
- **WHEN** a test runs `<app>/tools/validate.py` without `--settings`, with `cwd` set to a temporary directory holding an `orgsyndb.toml` that declares the required procedure text field `notebook`, with `--registry <app>/tests/fixtures/registry.json` and `--static-dir <app>/tests/fixtures/static`, on the content root `<app>/tests/fixtures/baseline`
- **THEN** it exits 1, and its one stdout line has field `notebook` and contains `required field missing`

### Requirement: Registry errors are configuration errors
The validator SHALL exit with status 2, print nothing to stdout, and write `validate.py: error:` and a message to stderr, when any of these holds:
- the registry file it reads does not exist, cannot be read as UTF-8 JSON, or is not a snapshot (compound-registry "Reading the registry");
- the `Europe/Berlin` time zone cannot be loaded.

The message names the registry file.

#### Scenario: Not JSON
- **WHEN** a registry variant run appends the line `{` to the copy of the fixture registry
- **THEN** it exits 2, stdout is empty, and stderr contains `validate.py: error:` and `registry.json`

#### Scenario: No reaction types
- **WHEN** a registry variant run on `baseline` empties the reaction types of the copy
- **THEN** it exits 1, stderr does not contain `validate.py: error:`, and its one stdout line has field `reaction_types` and contains `unknown reaction type`

