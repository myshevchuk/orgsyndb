## MODIFIED Requirements

### Requirement: Demo collection
The sample procedures SHALL form the demo collection `examples/demo/` of the application, a complete collection as the `collection` capability defines it, with the structure images in `examples/demo/static/structures/`, the compound registry in `examples/demo/compounds/` and the sequences in `examples/demo/md/sequences/`. The registry holds a file for every compound a sample names, as product or substrate, and no other file, and every compound sets `name_de`. Every path that this capability names under `org/procedures/` or `md/procedures/` is relative to `examples/demo/`. The application's own root holds no `org/`, `md/` or `site/static/` directory.

The demo declares compound fields of every type (compound-fields "Field declarations"):
- **Declarations.** `examples/demo/orgsyndb.toml` declares, in this order, `item_number` (`text`, `required`, `unique`, `pattern = 'CH-\d{4}'`, `column`), `short_name` (`text`), `chemical_class` (`choice`, `required`, `multiple`, `column`, `vocabulary = "chemical-classes"`), `stock` (`number`, `unit = "g"`, `min = 0`) and `in_house` (`boolean`), each with a `label` and a `label_de`.
- **Vocabulary.** `examples/demo/vocabularies/chemical-classes.toml` is the demo's only vocabulary. Every value has a `label_de`, and some value has two ancestors.
- **Values.** Every compound sets `item_number` and `chemical_class`. At least one compound sets two chemical classes, and at least one a class with two ancestors. Some compounds set `short_name` and `stock` and some do not, and at least one `stock` is not a whole number. `in_house` is `true` for at least one compound, `false` for at least one, and unset for at least one.

#### Scenario: Samples live in the demo collection
- **WHEN** a test inspects the application
- **THEN** `examples/demo/orgsyndb.toml` exists, `examples/demo/org/procedures/OSDB-0001-salicylic-acid.org` and `examples/demo/md/procedures/OSDB-0002-aspirin.md` exist, the demo registry's file names are exactly the keys the samples name, each with `.toml`, and neither `org/`, `md/` nor `site/static/` exists at the application root

#### Scenario: The demo declares its fields
- **WHEN** a test reads `examples/demo/orgsyndb.toml`, `examples/demo/vocabularies/` and the demo registry
- **THEN** the declarations, the vocabulary and the compounds' values meet the rules above

### Requirement: Test collection
The repository SHALL ship the test collection `tests/fixtures/collection/`, a complete collection as the `collection` capability defines it that holds every sample procedure of the demo collection, in either language, as a Markdown procedure, and that has no `org/` directory. The paths in this requirement are written out in full. The test collection meets all of the following:
- **Copies.** `tests/fixtures/collection/orgsyndb.toml`, `tests/fixtures/collection/.gitignore` and every file under `tests/fixtures/collection/static/`, `tests/fixtures/collection/compounds/`, `tests/fixtures/collection/vocabularies/` and `tests/fixtures/collection/md/sequences/` are byte-identical to the demo collection's files at the same relative paths, and the test collection's `static/`, `compounds/`, `vocabularies/` and `md/sequences/` hold no other file.
- **File names.** `tests/fixtures/collection/md/procedures/` holds exactly one file for each sample procedure file of the demo collection, `examples/demo/org/procedures/<stem>.org` or `examples/demo/md/procedures/<stem>.md`, named `<stem>.md`, and no other file.
- **Markdown samples.** The file for a Markdown sample is byte-identical to it.
- **Converted samples.** The file for an Org sample is a hand-written Markdown procedure, in the form of the demo's Markdown samples, that agrees with its Org source as follows:
  - Its front matter has exactly the keys of the Org source's custom-front-matter lines, with equal values, `title`, `slug`, `tags`, `date` and `lastmod`, and `ai_model` exactly when `#+AI_MODEL` names a model. `title`, `slug` and `ai_model` equal `#+TITLE`, `#+HUGO_SLUG` and `#+AI_MODEL`, and `tags` lists the words of `#+HUGO_TAGS` in their order.
  - `date` and `lastmod` are offset datetimes whose local date and time equal `#+CREATED` and `#+LAST_MODIFIED`, with a Europe/Berlin offset in force at that time; where a time in the autumn fall-back hour names two instants, the offsets are those of the instants the export chooses (org-export "Exported timestamps").
  - Its body holds no text before its first heading, and its `##` headings are the Org source's top-level headings, in the same order.
  - Its Reagents table has the same rows as the Org source's, header included, each row compared as its list of stripped cells, with separator lines left out.
  - Each section's text, with its table lines left out, equals the text of the Org section of the same name once both are normalised: every run of whitespace is replaced by one space, leading and trailing whitespace is dropped, and every emphasis span is replaced by its inner text `x`. In the Org text an emphasis span is `/x/`, `*x*`, `=x=`, `~x~`, `+x+` or `_x_` as Org's emphasis syntax defines it: the opening marker follows the start of the text, whitespace or one of `-('"{`, `x` neither begins nor ends with whitespace, and the closing marker precedes the end of the text, whitespace or one of `-.,:!?;'")}\[`. In the Markdown text it is `**x**`, `*x*`, `` `x` `` or `_x_`, where `x` neither begins nor ends with whitespace and neither underscore of `_x_` is inside a word. Every other character is kept, such as the `=` of `C=O` and the `/` of `E/Z`.

Integration tests that build, validate, serve or print a collection and do not exercise the Org export SHALL work on a copy of the test collection. Integration tests that exercise the Org export work on a copy of the demo collection, and those among them that need Emacs skip when `emacs` is absent, with a reason that names it.

#### Scenario: The test collection mirrors the demo
- **WHEN** a test lists `tests/fixtures/collection/` and compares it with `examples/demo/`
- **THEN** `orgsyndb.toml`, `.gitignore` and every file under `static/`, `compounds/` and `vocabularies/` are byte-identical to the demo's, `static/structures/isopentyl-acetate.svg`, `compounds/salicylic-acid.toml` and `vocabularies/chemical-classes.toml` among them, and no `org/` directory exists
- **AND** `md/procedures/` holds exactly the 18 file names derived from the demo's sample procedure files, and the file for each of the ten Markdown sample files is byte-identical to it

#### Scenario: Converted samples agree with their Org sources
- **WHEN** a test reads each of the eight Org samples of the demo collection, in either language, and its file in `tests/fixtures/collection/md/procedures/`
- **THEN** front matter, `date` and `lastmod`, headings, Reagents rows and section texts agree as stated above

#### Scenario: The agreement check (checker)
- **WHEN** a test gives the agreement check an Org source and a Markdown procedure that agree except that the Markdown text is wrapped at other columns and writes the Org source's `/italic/` as `*italic*`, then the same Markdown procedure with, in turn, one word of a section changed, `C=O` in a section written `CO`, `E/Z` in a section written `EZ`, one Reagents cell changed, one heading renamed, `lastmod` one minute later, the `+02:00` offset of a summer `date` written `+01:00`, and an extra front-matter key
- **THEN** it accepts the first and rejects each of the others

#### Scenario: The agreement check (checker, no AI model)
- **WHEN** a test gives the agreement check that Org source without its `#+AI_MODEL` line, first with the agreeing Markdown procedure without its `ai_model` line, then with the agreeing Markdown procedure unchanged
- **THEN** it accepts the first and rejects the second

#### Scenario: The suite runs without Emacs
- **WHEN** the orchestrator runs `python3 -m pytest tests` with a `PATH` that holds no `emacs` but every other tool the suite uses, with the ox-hugo and Pagefind caches present (manual verification, tasks.md section 5)
- **THEN** the suite passes, and every skipped test exercises the Org export and skips with a reason that names `emacs`

