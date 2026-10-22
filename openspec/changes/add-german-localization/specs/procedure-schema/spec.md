## MODIFIED Requirements

<!-- Reason: files carry a language code; IDs repeat across languages. -->

### Requirement: Unique identifiers across all source trees
Two procedure files of the same language SHALL NOT carry the same `id`, whichever content roots they come from. A duplicate is reported as one error on each file involved, naming the other file's path. Files of different languages with the same `id` are translations, as the localization spec defines.

#### Scenario: Same ID in two content roots
- **WHEN** a fixture run on the two roots `invalid/duplicate-id/a` and `invalid/duplicate-id/b` examines `a/OSDB-0104-first.md` and `b/OSDB-0104-second.md`, which both have `id = "OSDB-0104"`
- **THEN** the exit status is 1, and stdout is exactly two lines, both with field `id` and severity `error`
- **AND** the line for each file contains `duplicate id OSDB-0104` and the path of the other file

#### Scenario: Duplicate ID within one language
- **WHEN** a run examines two German files `OSDB-0100-baseline.de.md` and `OSDB-0100-copy.de.md` with the same `id`
- **THEN** it reports exactly two errors, field `id`, containing `duplicate id OSDB-0100`

### Requirement: Procedure file names
A procedure source file SHALL be named `OSDB-NNNN-short-slug.md` (content) or `OSDB-NNNN-short-slug.org` (Org source), with an optional language code before the suffix for a language other than English: `OSDB-NNNN-short-slug.de.md`, `OSDB-NNNN-short-slug.de.org`. The short slug matches `[a-z0-9]+(-[a-z0-9]+)*`, and the `OSDB-NNNN` prefix equals the file's `id` exactly. The code `.en` is an error (an English file has no code), and so is a code outside the site languages.

#### Scenario: Lowercase prefix is rejected
- **WHEN** a variant run leaves the baseline unchanged under the file name `osdb-0100-lowercase.md`
- **THEN** it reports exactly one error, field `file_name`, containing `must be named OSDB-NNNN-short-slug.md`

#### Scenario: File name disagrees with the ID
- **WHEN** a fixture run on `invalid/file-name-id-mismatch` examines `OSDB-0106-file-name-id-mismatch.md`, whose `id` is `"OSDB-0199"` and `slug` is `"osdb-0199"`
- **THEN** it reports exactly one error, field `file_name`, containing `does not match id OSDB-0199`

#### Scenario: Language code in a file name
- **WHEN** a run examines the baseline as `OSDB-0100-baseline.en.md`, and then as `OSDB-0100-baseline.fr.md`
- **THEN** each reports exactly one error, field `file_name`, containing `drop the language` and `unknown language code ".fr"` respectively

<!-- Reason: German text writes a decimal comma. -->

### Requirement: Scale with unit
The `scale` field SHALL be a string consisting of a number, whitespace, and a unit token, matching `^\d+([.,]\d+)?\s+\S+$` (e.g. `"25 mmol"` or `"2,5 mmol"`).

#### Scenario: Scale without a unit
- **WHEN** a variant run sets `scale = "25"` under the file name `OSDB-0100-bad-scale.md`
- **THEN** it reports exactly one error, field `scale`, containing `must be a number followed by a unit`

#### Scenario: Scale with a decimal comma
- **WHEN** a run examines the baseline with `scale = "2,5 mmol"`
- **THEN** it exits 0 and prints nothing

<!-- Reason: the vocabulary carries German labels. -->

### Requirement: Reaction-type vocabulary file
The file `site/data/reaction_types.toml` SHALL map each reaction-type slug, as a top-level key matching `^[a-z0-9]+(-[a-z0-9]+)*$`, to a table containing a non-empty string `label` and, for each site language other than English, a non-empty string `label_<language>` (`label_de`). Its entries include at least `acylation`, `aldol-condensation`, `cross-coupling`, `esterification`, `olefination`, `protection`, `reduction` and `reductive-amination`.

#### Scenario: Shipped vocabulary is well formed and complete
- **WHEN** a test loads `site/data/reaction_types.toml` with `tomllib`
- **THEN** every top-level key matches the slug pattern and maps to a table whose `label` and `label_de` are non-empty strings
- **AND** the keys include `acylation`, `aldol-condensation`, `cross-coupling`, `esterification`, `olefination`, `protection`, `reduction` and `reductive-amination`

#### Scenario: Validator accepts the shipped vocabulary
- **WHEN** the validator runs with its default vocabulary on an empty temporary content root
- **THEN** it exits 0 and prints nothing to stdout

<!-- Reason: German procedures have German section names. -->

### Requirement: Body sections
Every procedure body SHALL contain these eight level-2 sections, in this order; a German procedure uses the German names that the localization spec gives instead:
1. Summary
2. Reagents
3. Procedure
4. Workup and Purification
5. Characterization
6. Notes
7. Hazards and Waste Disposal
8. References

The rules for headings are:
- A heading is a line `## <text>` outside fenced code blocks. The text is taken after removing a trailing `{...}` attribute block and any closing `#` sequence, and compared case-insensitively after trimming and collapsing whitespace.
- Each missing section is a `body` warning containing `missing section "<name>"`.
- Canonical sections that appear out of canonical order give one `body` warning per file containing `sections out of order`.
- Other `##` headings, and headings of other levels, are allowed.
- In Org sources the same eight sections are top-level (`*`) headings.

#### Scenario: Missing Notes section
- **WHEN** a fixture run on `warn/missing-section` examines `OSDB-0151-missing-section.md`, which has every section except `## Notes`
- **THEN** it reports exactly one warning, field `body`, containing `missing section "Notes"`

#### Scenario: Sections out of order
- **WHEN** a variant run moves the `## Workup and Purification` section, with its content, before `## Procedure` under the file name `OSDB-0100-section-order.md`
- **THEN** it reports exactly one warning, field `body`, containing `sections out of order`

#### Scenario: Heading inside a code fence does not count
- **WHEN** a variant run wraps the `## Notes` heading line in a fenced code block (```` ``` ```` lines before and after it) under the file name `OSDB-0100-heading-in-code.md`
- **THEN** it reports exactly one warning, field `body`, containing `missing section "Notes"`

#### Scenario: ox-hugo anchors and case differences are accepted
- **WHEN** the valid-set run examines `valid/export/OSDB-0003-*.md`, whose headings carry ox-hugo anchors (`## Summary {#summary}`), and `valid/md/OSDB-0002-*.md`, which writes `## Workup and purification` and adds an extra `## Discussion` section
- **THEN** no `body` line is printed for either file
