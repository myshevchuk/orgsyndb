## ADDED Requirements

### Requirement: Test collection
The repository SHALL ship the test collection `tests/fixtures/collection/`, a complete collection as the `collection` capability defines it that holds every sample procedure of the demo collection, in either language, as a Markdown procedure, and that has no `org/` directory. The paths in this requirement are written out in full. The test collection meets all of the following:
- **Copies.** `tests/fixtures/collection/orgsyndb.toml`, `tests/fixtures/collection/.gitignore` and every file under `tests/fixtures/collection/static/` are byte-identical to the demo collection's files at the same relative paths, and the test collection's `static/` holds no other file.
- **File names.** `tests/fixtures/collection/md/procedures/` holds exactly one file for each sample procedure file of the demo collection, `examples/demo/org/procedures/<stem>.org` or `examples/demo/md/procedures/<stem>.md`, named `<stem>.md`, and no other file.
- **Markdown samples.** The file for a Markdown sample is byte-identical to it.
- **Converted samples.** The file for an Org sample is a hand-written Markdown procedure, in the form of the demo's Markdown samples, that agrees with its Org source as follows:
  - Its front matter has exactly the keys of the Org source's custom-front-matter lines, with equal values, and `title`, `slug`, `tags`, `ai_model`, `date` and `lastmod`. `title`, `slug` and `ai_model` equal `#+TITLE`, `#+HUGO_SLUG` and `#+AI_MODEL`, and `tags` lists the words of `#+HUGO_TAGS` in their order.
  - `date` and `lastmod` are offset datetimes whose local date and time equal `#+CREATED` and `#+LAST_MODIFIED`, with a Europe/Berlin offset in force at that time; where a time in the autumn fall-back hour names two instants, the offsets are those of the instants the export chooses (org-export "Exported timestamps").
  - Its body holds no text before its first heading, and its `##` headings are the Org source's top-level headings, in the same order.
  - Its Reagents table has the same rows as the Org source's, header included, each row compared as its list of stripped cells, with separator lines left out.
  - Each section's text, with its table lines left out, equals the text of the Org section of the same name once both are normalised: every run of whitespace is replaced by one space, leading and trailing whitespace is dropped, and every emphasis span is replaced by its inner text `x`. In the Org text an emphasis span is `/x/`, `*x*`, `=x=`, `~x~`, `+x+` or `_x_` as Org's emphasis syntax defines it: the opening marker follows the start of the text, whitespace or one of `-('"{`, `x` neither begins nor ends with whitespace, and the closing marker precedes the end of the text, whitespace or one of `-.,:!?;'")}\[`. In the Markdown text it is `**x**`, `*x*`, `` `x` `` or `_x_`, where `x` neither begins nor ends with whitespace and neither underscore of `_x_` is inside a word. Every other character is kept, such as the `=` of `C=O` and the `/` of `E/Z`.

Integration tests that build, validate, serve or print a collection and do not exercise the Org export SHALL work on a copy of the test collection. Integration tests that exercise the Org export work on a copy of the demo collection, and those among them that need Emacs skip when `emacs` is absent, with a reason that names it.

#### Scenario: The test collection mirrors the demo
- **WHEN** a test lists `tests/fixtures/collection/` and compares it with `examples/demo/`
- **THEN** `orgsyndb.toml`, `.gitignore` and every file under `static/` are byte-identical to the demo's, `static/structures/osdb-0003.svg` among them, and no `org/` directory exists
- **AND** `md/procedures/` holds exactly the 16 file names derived from the demo's sample procedure files, and the file for each of the eight Markdown samples is byte-identical to it

#### Scenario: Converted samples agree with their Org sources
- **WHEN** a test reads each of the eight Org samples of the demo collection, in either language, and its file in `tests/fixtures/collection/md/procedures/`
- **THEN** front matter, `date` and `lastmod`, headings, Reagents rows and section texts agree as stated above

#### Scenario: The agreement check (checker)
- **WHEN** a test gives the agreement check an Org source and a Markdown procedure that agree except that the Markdown text is wrapped at other columns and writes the Org source's `/italic/` as `*italic*`, then the same Markdown procedure with, in turn, one word of a section changed, `C=O` in a section written `CO`, `E/Z` in a section written `EZ`, one Reagents cell changed, one heading renamed, `lastmod` one minute later, the `+02:00` offset of a summer `date` written `+01:00`, and an extra front-matter key
- **THEN** it accepts the first and rejects each of the others

#### Scenario: The suite runs without Emacs
- **WHEN** the orchestrator runs `python3 -m pytest tests` with a `PATH` that holds no `emacs` but every other tool the suite uses, with the ox-hugo and Pagefind caches present (manual verification, tasks.md section 5)
- **THEN** the suite passes, and every skipped test exercises the Org export and skips with a reason that names `emacs`
