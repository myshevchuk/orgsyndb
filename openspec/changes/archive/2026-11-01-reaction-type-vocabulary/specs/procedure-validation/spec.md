## RENAMED Requirements

- FROM: `### Requirement: Default paths resolve from the script location`
- TO: `### Requirement: Default paths come from the working directory`

## MODIFIED Requirements

### Requirement: Command-line interface
The validator SHALL be the executable file `tools/validate.py`, invoked as `validate.py [--settings FILE] [--static-dir DIR] [--compounds DIR] [--sequences DIR] CONTENT_ROOT...`, and it SHALL use only the Python standard library.
- Each positional `CONTENT_ROOT` is a directory of procedure Markdown files with `+++` TOML front matter, such as an ox-hugo export directory or `md/procedures/`.
- At least one content root is required.
- `--sequences` names the directory of synthesis sequences (synthesis-sequences "Sequence files"). The validator checks every sequence in it against the procedures of the content roots and the compound registry.
- `--compounds` names the compound registry (compound-registry "Compound files"). The validator checks every compound file in it and resolves every compound key of the procedures against the compounds it defines.
- `--settings` names the collection's settings file, its `orgsyndb.toml` (collection "Collection layout"). The validator applies the rules that requirement states for `format` and the top-level keys, reads only `fields` beyond them, checks the declarations and the vocabularies they name (compound-fields "Field declarations" and "Vocabularies", procedure-fields "Procedure field declarations") and the reaction-type vocabulary (reaction-types "Reaction-type vocabulary"), and checks every compound file against the compound fields (compound-fields "Field values") and every procedure of the content roots against the procedure fields (procedure-fields "Procedure field values"). Vocabularies, the reaction types among them, resolve against the directory of the settings file, whether or not that file exists. The validator takes no option naming a vocabulary.
- It reads no Org source. An Org procedure reaches it only as its export, and the export checks the Org source itself (org-export "Org sources and their problems").
- The module also exposes `main(argv: Sequence[str] | None = None) -> int`, which returns the exit status.

#### Scenario: No roots given
- **WHEN** the validator runs with no `CONTENT_ROOT`
- **THEN** it exits 2 and prints an error to stderr

#### Scenario: Org root option is refused
- **WHEN** the validator runs with `--org-root tests/fixtures/valid/org tests/fixtures/valid/md`
- **THEN** it exits 2, stderr contains `--org-root`, and stdout is empty

#### Scenario: Vocabulary option is refused
- **WHEN** the validator runs with `--vocabulary tests/fixtures/settings/vocabularies/reaction-types.toml tests/fixtures/valid/md`
- **THEN** it exits 2, stderr contains `--vocabulary`, and stdout is empty

#### Scenario: Root is not a directory
- **WHEN** the validator runs on the content root `tests/fixtures/does-not-exist`
- **THEN** it exits 2, and stderr contains `validate.py: error:` and `not a directory`

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/validate.py` with `ast` and collects the top-level module names of every `import` and `from ... import` statement
- **THEN** every name is in `sys.stdlib_module_names`

### Requirement: Default paths come from the working directory
When `--static-dir` is omitted, the validator SHALL use `static` in the working directory, the location of a collection's static files when run from the collection's root. A static directory that does not exist is not a configuration error; it only makes every `structure_image` unresolvable. When `--compounds` is omitted, it SHALL use `compounds` in the working directory, the location of a collection's registry when run from the collection's root. A registry directory that does not exist is not a configuration error either; it defines no compound, so every compound key is unknown. When `--sequences` is omitted, it SHALL use `md/sequences` in the working directory; a sequences directory that does not exist holds no sequence. When `--settings` is omitted, it SHALL use `orgsyndb.toml` in the working directory, the settings file of a collection when run from the collection's root. A settings file that does not exist declares no field when `--settings` is omitted; a settings file that `--settings` names and that does not exist is a configuration error (compound-fields "Declaration errors are configuration errors"). So without `--settings`, the reaction types are those of `vocabularies/reaction-types.toml` in the working directory (reaction-types "Reaction-type vocabulary").

#### Scenario: Default static and registry directories are the working directory's
- **WHEN** a test runs `<app>/tools/validate.py` without `--static-dir` and `--compounds`, with `cwd` set to a temporary directory holding `static/structures/ethyl-acetate.svg`, a `compounds/ethyl-acetate.toml` that sets `structure_image = "structures/ethyl-acetate.svg"`, `vocabularies/reaction-types.toml`, a copy of the fixture reaction types, and a content root whose one procedure is the baseline
- **THEN** it reports no problem and exits 0

#### Scenario: Missing registry
- **WHEN** a fixture run on `baseline` names `--compounds tests/fixtures/no-such-registry`
- **THEN** it exits 1, and its one stdout line has field `products[1].compound` and contains `unknown compound "ethyl-acetate"`

#### Scenario: Default settings file is the working directory's
- **WHEN** a test runs `<app>/tools/validate.py` without `--settings`, with `cwd` set to a temporary directory holding an `orgsyndb.toml` that declares the required text field `item_number` and `vocabularies/reaction-types.toml`, a copy of the fixture reaction types, with `--compounds <app>/tests/fixtures/compounds` and `--static-dir <app>/tests/fixtures/static`, on the content root `<app>/tests/fixtures/baseline`
- **THEN** it exits 1, and every stdout line has field `item_number` and contains `required field missing`, one for each compound file of the fixture registry

### Requirement: Vocabulary file errors are configuration errors
The validator SHALL exit with status 2, print nothing to stdout, and write `validate.py: error:` and a message to stderr, when any of these holds:
- the reaction-type vocabulary it reads (reaction-types "Reaction-type vocabulary") exists but cannot be read as UTF-8 TOML;
- that vocabulary breaks a rule of compound-fields "Vocabularies": a top-level key that is not a slug, an entry that is not a table with a non-empty string `label`, an empty or non-string `label_de`, an entry key other than `label` and `label_de`, or no value;
- a value of that vocabulary takes `parent`;
- the `Europe/Berlin` time zone cannot be loaded.

The message names the vocabulary file and, where there is one, the offending value and key. A reaction-type vocabulary that does not exist is no configuration error (reaction-types "Reaction-type vocabulary"), unless a declaration names it (compound-fields "Declaration errors are configuration errors").

#### Scenario: Entry without a label
- **WHEN** a settings variant run on `valid/md` replaces the `label` line of the value `reduction` of `vocabularies/reaction-types.toml` with `note = "no label"`
- **THEN** it exits 2, stdout is empty, and stderr contains `reaction-types.toml`, `reduction` and `label`

#### Scenario: Missing vocabulary file
- **WHEN** a settings variant run on `valid/md` deletes `vocabularies/reaction-types.toml`
- **THEN** it exits 1, stderr does not contain `validate.py: error:`, and every stdout line has field `reaction_types` and contains `unknown reaction type`, one for each file of `valid/md`

#### Scenario: Not TOML
- **WHEN** a settings variant run on `valid/md` appends the line `[reduction` to `vocabularies/reaction-types.toml`
- **THEN** it exits 2, stdout is empty, and stderr contains `validate.py: error:` and `reaction-types.toml`

### Requirement: Fixture suite
The repository SHALL ship validator fixtures under `tests/fixtures/` and a `unittest` suite under `tests/` that runs with `python3 -m pytest tests` and proves each scenario of both specs. Representative cases are committed fixture files; the remaining field variations are written by the tests as variants of a committed baseline. The scenarios of the procedure-schema spec that are stated as ERT tests are proved by the ERT suite of the org-export spec, which `python3 -m pytest tests` runs.

The terms used in the scenarios are defined as follows:
- **Fixture run.** A fixture run on roots R runs `tools/validate.py --settings tests/fixtures/settings/orgsyndb.toml --static-dir tests/fixtures/static --compounds tests/fixtures/compounds` with roots R, relative to `tests/fixtures/`. Its reaction types, the fixture reaction types, are those of `tests/fixtures/settings/vocabularies/reaction-types.toml`.
- **Valid-set run.** The valid-set run is a fixture run on `valid/md` and `valid/export`.
- **Variant run.** A variant run writes `tests/fixtures/baseline/OSDB-0100-baseline.md`, with the stated textual change applied and under the stated file name, as the only file of a fresh temporary content root, then makes a fixture run on that root.
- **Sequence fixture run.** A sequence fixture run on roots R is a fixture run on R and `general` with `--sequences` naming the stated directory, relative to `tests/fixtures/`.
- **Sequence variant run.** A sequence variant run copies `tests/fixtures/sequences/` to a fresh temporary directory, applies the stated change to the named sequence there, and makes a sequence fixture run on `valid/md` and `sequences-procedures` with that directory.
- **Registry variant run.** A registry variant run copies `tests/fixtures/compounds/` to a fresh temporary directory, applies the stated change to the files there, and makes a fixture run on `baseline` with `--compounds` set to that directory. "Reports exactly one" then counts the stdout lines of the whole run, compound files and procedures together.
- **Settings variant run.** A settings variant run on roots R copies `tests/fixtures/settings/` to a fresh temporary directory, applies the stated change to the files there, and makes a fixture run on R with `--settings` naming the copy of `orgsyndb.toml`. "Reports exactly one" counts the stdout lines of the whole run.
- **Field-declaration run.** A field-declaration run copies `tests/fixtures/fields/` and `tests/fixtures/compounds/` to a fresh temporary directory, copies the fixture reaction types into the fields copy's `vocabularies/`, applies the stated change to the files there (a compound file named alone is one of the registry copy, `vocabularies/` that of the fields copy), and makes a fixture run on `baseline` with `--compounds` set to the registry copy and `--settings` naming the copy of `orgsyndb.toml`. "Reports exactly one" counts as for a registry variant run.
- **"Reports exactly one error with field F containing T".** This means exit status 1 and exactly one stdout line, which has field F, severity `error`, and a message containing T. "Reports exactly one warning" means the same with severity `warning` and exit status 0.

The committed fixtures are these:
- `settings/`: a settings file `orgsyndb.toml` holding `format = 1` and nothing else, and `vocabularies/reaction-types.toml`, holding the values `esterification` (`Esterification`) and `reduction` (`Reduction`) and no other; `settings/vocabularies/` holds no other file.
- `static/structures/ethyl-acetate.svg`.
- `compounds/`: the fixture registry, holding a valid file for every compound key that a committed fixture outside `invalid/` and `collection/` names, `ethyl-acetate` and `ethanol` among them, and no other file. `ethyl-acetate.toml` sets every optional key, `structure_image = "structures/ethyl-acetate.svg"` included. No fixture compound sets a declared field.
- `fields/`: a settings file `orgsyndb.toml` holding `format = 1` and, in this order, the declarations of `item_number` (`text`, labelled `Item no.` and `Artikelnr.`, `pattern = 'CH-\d{4}'`, `unique`, `column`), `short_name` (`text`, labelled `Short name`, with no `label_de`), `stock` (`number`, labelled `Stock` and `Bestand`, `unit = "g"`, `min = 0`), `in_house` (`boolean`, labelled `Made in house` and `Eigene Herstellung`), `chemical_class` (`choice`, labelled `Chemical class` and `Stoffklasse`, `vocabulary = "chemical-classes"`, `multiple`, `column`) and `storage` (`choice`, labelled `Storage` and `Lagerung`, `vocabulary = "storage"`), none of them `required`; `vocabularies/chemical-classes.toml`, with the values `carbonyl-compounds` (`Carbonyl compounds`, `Carbonylverbindungen`), `ketones` (`Ketones`, `Ketone`) and `esters` (`Esters`, `Ester`), both filed under `carbonyl-compounds`, and `alcohols` (`Alcohols`, `Alkohole`); and `vocabularies/storage.toml`, with `cabinet` (`Cabinet`, `Schrank`) and `fridge` (`Fridge`, `Kühlschrank`).
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
- **THEN** `orgsyndb.toml` parses to `{"format": 1}`, `vocabularies/reaction-types.toml` parses to exactly the two values stated, `vocabularies/` holds no other file, and neither `tests/fixtures/reaction_types.toml` nor `tests/fixtures/bad-vocabulary.toml` exists

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
