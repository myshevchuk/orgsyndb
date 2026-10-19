## ADDED Requirements

<!-- Scenario conventions (normative copy: procedure-validation, "Fixture
suite"). A "fixture run on R" runs tools/validate.py with --vocabulary
tests/fixtures/reaction_types.toml and --static-dir tests/fixtures/static
on the root(s) R, relative to tests/fixtures/. A "variant run" writes the
baseline procedure tests/fixtures/baseline/OSDB-0100-baseline.md, with the
stated change and under the stated file name, as the only file of a fresh
temporary content root, then makes a fixture run on that root. "Reports
exactly one error <field> containing <text>" means exit status 1 and
exactly one stdout line, <path>:<field>: error: <message>, whose message
contains <text>; "exactly one warning" is the same with severity warning
and exit status 0. -->

### Requirement: Procedure identifier
Every procedure SHALL carry a front-matter `id` string matching `OSDB-NNNN`: the literal `OSDB-` followed by exactly four digits whose value lies between 1 and 9999. `OSDB-0000` is reserved as the template placeholder and is never a valid ID.

#### Scenario: Malformed ID is rejected
- **WHEN** a fixture run on `invalid/bad-id-format` examines `OSDB-0102-bad-id-format.md`, whose `id` is `"OSDB-102"`
- **THEN** it reports exactly one error, field `id`, containing `must match OSDB-NNNN`

#### Scenario: Placeholder ID is rejected
- **WHEN** a variant run uses `id = "OSDB-0000"` and `slug = "osdb-0000"` under the file name `OSDB-0000-id-zero.md`
- **THEN** it reports exactly one error, field `id`, containing `must be between OSDB-0001 and OSDB-9999`

### Requirement: Unique identifiers across all source trees
Two procedure files SHALL NOT carry the same `id`, whichever content roots they come from. A duplicate is reported as one error on each file involved, naming the other file's path.

#### Scenario: Same ID in two content roots
- **WHEN** a fixture run on the two roots `invalid/duplicate-id/a` and `invalid/duplicate-id/b` examines `a/OSDB-0104-first.md` and `b/OSDB-0104-second.md`, which both have `id = "OSDB-0104"`
- **THEN** the exit status is 1, and stdout is exactly two lines, both with field `id` and severity `error`
- **AND** the line for each file contains `duplicate id OSDB-0104` and the path of the other file

### Requirement: Procedure file names
A procedure source file SHALL be named `OSDB-NNNN-short-slug.md` (content) or `OSDB-NNNN-short-slug.org` (Org source). The short slug matches `[a-z0-9]+(-[a-z0-9]+)*`, and the `OSDB-NNNN` prefix equals the file's `id` exactly.

#### Scenario: Lowercase prefix is rejected
- **WHEN** a variant run leaves the baseline unchanged under the file name `osdb-0100-lowercase.md`
- **THEN** it reports exactly one error, field `file_name`, containing `must be named OSDB-NNNN-short-slug.md`

#### Scenario: File name disagrees with the ID
- **WHEN** a fixture run on `invalid/file-name-id-mismatch` examines `OSDB-0106-file-name-id-mismatch.md`, whose `id` is `"OSDB-0199"` and `slug` is `"osdb-0199"`
- **THEN** it reports exactly one error, field `file_name`, containing `does not match id OSDB-0199`

### Requirement: Slug determines the URL
Every procedure SHALL carry a front-matter `slug` string equal to its `id` lowercased (`OSDB-0001` gives `osdb-0001`). A Hugo permalink of `/procedures/:slug/` then serves the procedure at `/procedures/osdb-0001/`. The error message states the exact expected value.

#### Scenario: Slug differs from the lowercased ID
- **WHEN** a fixture run on `invalid/slug-mismatch` examines `OSDB-0107-slug-mismatch.md`, whose `slug` is `"osdb-0107-x"`
- **THEN** it reports exactly one error, field `slug`, containing `must be "osdb-0107" (the lowercased id)`

#### Scenario: Slug is missing
- **WHEN** a variant run removes the `slug` key under the file name `OSDB-0100-missing-slug.md`
- **THEN** it reports exactly one error, field `slug`, containing `required field missing`

### Requirement: Required front-matter fields
Every procedure SHALL carry, in its TOML front matter, each of the following keys with the stated type. A missing key is an error containing `required field missing`, and a value of the wrong TOML type is an error.
- `id`: string
- `slug`: string
- `title`: non-empty string, the product name as shown in the heading
- `date`: offset datetime
- `lastmod`: offset datetime
- `authors`: non-empty list of non-empty strings
- `status`: string
- `reaction_types`: list of strings
- `tags`: non-empty list of strings
- `product`: table
- `scale`: string
- `yield_percent`: number (TOML integer or float; never boolean)
- `hazards`: non-empty list of non-empty strings

#### Scenario: Missing title
- **WHEN** a fixture run on `invalid/missing-title` examines `OSDB-0101-missing-title.md`, which has no `title` key
- **THEN** it reports exactly one error, field `title`, containing `required field missing`

#### Scenario: Yield given as a string
- **WHEN** a variant run sets `yield_percent = "85"` under the file name `OSDB-0100-yield-not-number.md`
- **THEN** it reports exactly one error, field `yield_percent`, containing `must be a number`

#### Scenario: Empty hazards list
- **WHEN** a variant run sets `hazards = []` under the file name `OSDB-0100-empty-hazards.md`
- **THEN** it reports exactly one error, field `hazards`, containing `must not be empty`

#### Scenario: Empty tags list
- **WHEN** a variant run sets `tags = []` under the file name `OSDB-0100-empty-tags.md`
- **THEN** it reports exactly one error, field `tags`, containing `must not be empty`

### Requirement: Status vocabulary
The `status` field SHALL be exactly one of `draft`, `checked` or `retired`. Hugo's `draft` key is never used for workflow status.

#### Scenario: Unknown status
- **WHEN** a variant run sets `status = "approved"` under the file name `OSDB-0100-bad-status.md`
- **THEN** it reports exactly one error, field `status`, containing `must be one of draft, checked, retired`

### Requirement: Controlled reaction type
The `reaction_types` field SHALL be a list of exactly one string, and that string SHALL be a key of the reaction-type vocabulary file.

#### Scenario: Reaction type outside the vocabulary
- **WHEN** a fixture run on `invalid/unknown-reaction-type` examines `OSDB-0111-unknown-reaction-type.md`, whose `reaction_types` is `["esterfication"]`
- **THEN** it reports exactly one error, field `reaction_types`, containing `unknown reaction type "esterfication"`

#### Scenario: Two reaction types
- **WHEN** a variant run sets `reaction_types = ["esterification", "reduction"]`, both in the fixture vocabulary, under the file name `OSDB-0100-two-reaction-types.md`
- **THEN** it reports exactly one error, field `reaction_types`, containing `must contain exactly one reaction type`

### Requirement: Tag format
Every entry of `tags` SHALL be lowercase and hyphenated, matching `^[a-z0-9]+(-[a-z0-9]+)*$`.

#### Scenario: Tag with capitals and a space
- **WHEN** a variant run sets `tags = ["Sample Data"]` under the file name `OSDB-0100-bad-tag.md`
- **THEN** it reports exactly one error, field `tags`, containing `must be lowercase and hyphenated`

### Requirement: Yield range
The `yield_percent` field SHALL be a finite number from 0 to 100 inclusive.

#### Scenario: Yield above 100
- **WHEN** a fixture run on `invalid/yield-out-of-range` examines `OSDB-0110-yield-out-of-range.md`, whose `yield_percent` is `104.5`
- **THEN** it reports exactly one error, field `yield_percent`, containing `must be between 0 and 100`

### Requirement: Scale with unit
The `scale` field SHALL be a string consisting of a number, whitespace, and a unit token, matching `^\d+(\.\d+)?\s+\S+$` (e.g. `"25 mmol"`).

#### Scenario: Scale without a unit
- **WHEN** a variant run sets `scale = "25"` under the file name `OSDB-0100-bad-scale.md`
- **THEN** it reports exactly one error, field `scale`, containing `must be a number followed by a unit`

### Requirement: Product table
The `product` table SHALL contain these keys:
- `name`: non-empty string
- `formula`: non-empty string
- `mw`: finite number greater than 0, in g/mol
- `smiles`: non-empty string
- `cas`: optional string matching `^\d{2,7}-\d{2}-\d$` whose final check digit verifies

Problems inside the table are reported under the dotted field name (`product.mw`). Any other key in the table is a warning containing `unknown field`.

#### Scenario: Missing molecular weight
- **WHEN** a variant run removes `mw` from the `product` table under the file name `OSDB-0100-product-missing-mw.md`
- **THEN** it reports exactly one error, field `product.mw`, containing `required field missing`

#### Scenario: CAS number with a wrong check digit
- **WHEN** a variant run sets `cas = "64-17-4"` in the `product` table (the valid number is `64-17-5`) under the file name `OSDB-0100-bad-cas-check-digit.md`
- **THEN** it reports exactly one error, field `product.cas`, containing `check digit`

### Requirement: Timestamps are offset datetimes in order
The `date` and `lastmod` fields SHALL be TOML offset datetimes, and `lastmod` SHALL NOT be earlier than `date` when compared as instants. This comparison of exported instants is the authoritative ordering check. An offset that differs from the Europe/Berlin UTC offset in force at that instant is a warning, not an error.

#### Scenario: Date written as a quoted string
- **WHEN** a fixture run on `invalid/date-as-string` examines `OSDB-0120-date-as-string.md`, whose `date` is the string `"2026-10-19T17:42:05+02:00"`
- **THEN** it reports exactly one error, field `date`, containing `must be a TOML offset datetime`

#### Scenario: Date without an offset
- **WHEN** a variant run sets `date = 2026-10-19T17:42:05` (a local datetime) under the file name `OSDB-0100-date-without-offset.md`
- **THEN** it reports exactly one error, field `date`, containing `must be a TOML offset datetime`

#### Scenario: Last modification before creation
- **WHEN** a variant run sets `date = 2026-10-19T17:42:05+02:00` and `lastmod = 2026-10-18T09:00:00+02:00` under the file name `OSDB-0100-lastmod-before-date.md`
- **THEN** it reports exactly one error, field `lastmod`, containing `is earlier than date`

#### Scenario: Winter offset in summer
- **WHEN** a fixture run on `warn/offset` examines `OSDB-0155-offset.md`, whose `date` is `2026-07-01T10:00:00+01:00` and `lastmod` is `2026-07-02T10:00:00+02:00`
- **THEN** it reports exactly one warning, field `date`, containing `is not the Europe/Berlin offset`

### Requirement: Precursors refer to existing procedures
The optional `precursors` field SHALL be a list of procedure IDs. Each ID matches the identifier format, belongs to some procedure among the validated content roots, and is not the procedure's own `id`.

#### Scenario: Precursor that does not exist
- **WHEN** a fixture run on `invalid/missing-precursor` examines `OSDB-0123-missing-precursor.md`, whose `precursors` is `["OSDB-0999"]`
- **THEN** it reports exactly one error, field `precursors`, containing `OSDB-0999 not found`

#### Scenario: Procedure lists itself
- **WHEN** a variant run sets `precursors = ["OSDB-0100"]` under the file name `OSDB-0100-self-precursor.md`
- **THEN** it reports exactly one error, field `precursors`, containing `lists the procedure itself`

#### Scenario: Precursor in another content root
- **WHEN** the valid-set run examines `valid/md/OSDB-0002-*.md`, whose `precursors` is `["OSDB-0003"]`, where `OSDB-0003` is defined only in `valid/export`
- **THEN** no line is printed for `precursors`

### Requirement: Structure image path
The optional `structure_image` field SHALL be a relative path beginning with `structures/` and ending in `.svg` or `.png`, with no `..` component, naming a file that exists under the static directory.

#### Scenario: Image file missing
- **WHEN** a fixture run on `invalid/missing-structure-image` examines `OSDB-0125-missing-structure-image.md`, whose `structure_image` is `"structures/osdb-0125.svg"`, absent from `tests/fixtures/static`
- **THEN** it reports exactly one error, field `structure_image`, containing `not found`

#### Scenario: Unsupported image type
- **WHEN** a variant run sets `structure_image = "structures/osdb-0001.jpg"` under the file name `OSDB-0100-structure-image-wrong-type.md`
- **THEN** it reports exactly one error, field `structure_image`, containing `must end in .svg or .png`

#### Scenario: Image outside the structures directory
- **WHEN** a variant run sets `structure_image = "osdb-0001.svg"` under the file name `OSDB-0100-structure-image-outside-structures.md`
- **THEN** it reports exactly one error, field `structure_image`, containing `must be a relative path under structures/`

### Requirement: Other optional fields
The optional fields SHALL have these shapes when present:
- `checked_by`: list of non-empty strings
- `references`: list of non-empty strings
- `ai_model`: non-empty string other than `none`; the key is omitted when no AI assisted

#### Scenario: Checked-by given as a bare string
- **WHEN** a variant run sets `checked_by = "B. Example"` under the file name `OSDB-0100-checked-by-not-list.md`
- **THEN** it reports exactly one error, field `checked_by`, containing `must be a list of strings`

#### Scenario: AI model recorded as none
- **WHEN** a variant run sets `ai_model = "none"` under the file name `OSDB-0100-ai-model-none.md`
- **THEN** it reports exactly one error, field `ai_model`, containing `omit ai_model`

### Requirement: Keys outside the schema
Front-matter keys outside the schema SHALL be handled as follows:
- **Tolerated silently, subject to type:** `draft` (boolean `false` only), `description` (string), `aliases` (list of strings), `weight` (integer).
- **Errors:** `draft = true`, `author` and `url`.
- **Warnings:** any other key, with a message containing `unknown field`.

#### Scenario: Draft set to true
- **WHEN** a variant run sets `draft = true` under the file name `OSDB-0100-draft-true.md`
- **THEN** it reports exactly one error, field `draft`, containing `use status, not draft`

#### Scenario: Singular author key
- **WHEN** a fixture run on `invalid/author-key` examines `OSDB-0129-author-key.md`, which has `author = ["A. Example"]` as well as a valid `authors`
- **THEN** it reports exactly one error, field `author`, containing `use authors`

#### Scenario: Explicit URL
- **WHEN** a variant run sets `url = "/procedures/osdb-0100/"` under the file name `OSDB-0100-url-key.md`
- **THEN** it reports exactly one error, field `url`, containing `derived from slug`

#### Scenario: Misspelt optional key
- **WHEN** a variant run sets `checkedby = ["B. Example"]` under the file name `OSDB-0100-unknown-key.md`
- **THEN** it reports exactly one warning, field `checkedby`, containing `unknown field`

#### Scenario: ox-hugo draft key passes
- **WHEN** the valid-set run examines `valid/export/OSDB-0003-*.md`, which has `draft = false` as ox-hugo emits it
- **THEN** no line is printed for that file

### Requirement: Reaction-type vocabulary file
The file `site/data/reaction_types.toml` SHALL map each reaction-type slug, as a top-level key matching `^[a-z0-9]+(-[a-z0-9]+)*$`, to a table containing a non-empty string `label`. Its entries include at least `acylation`, `aldol-condensation`, `cross-coupling`, `esterification`, `olefination`, `protection`, `reduction` and `reductive-amination`.

#### Scenario: Shipped vocabulary is well formed and complete
- **WHEN** a test loads `site/data/reaction_types.toml` with `tomllib`
- **THEN** every top-level key matches the slug pattern and maps to a table whose `label` is a non-empty string
- **AND** the keys include `acylation`, `aldol-condensation`, `cross-coupling`, `esterification`, `olefination`, `protection`, `reduction` and `reductive-amination`

#### Scenario: Validator accepts the shipped vocabulary
- **WHEN** the validator runs with its default vocabulary on an empty temporary content root
- **THEN** it exits 0 and prints nothing to stdout

### Requirement: Org file-level keywords
Every Org procedure source SHALL carry each of the file-level keywords `#+CREATED`, `#+LAST_MODIFIED` and `#+AI_MODEL` exactly once. Keyword names are matched case-insensitively. The following rules apply to the values:
- Each timestamp is an Org inactive timestamp of the exact form `[YYYY-MM-DD Day hh:mm:ss]`.
- Its date and time are valid, and `Day` is the English three-letter abbreviation (`Mon` … `Sun`) of that date.
- It is Europe/Berlin local wall-clock time, carrying no offset, and names a time that exists in Europe/Berlin.
- `#+LAST_MODIFIED` is not earlier than `#+CREATED`, compared as follows. A wall-clock time in the autumn fall-back hour maps to two instants, so the earliest possible instant of `#+CREATED` is compared with the latest possible instant of `#+LAST_MODIFIED`. The check passes when the first is not later than the second, that is, when some choice of Berlin offsets puts the two in order. The exported `lastmod >= date` comparison remains the authoritative ordering check.
- `#+AI_MODEL` is `none` for human-authored files, or otherwise a single model identifier matching `^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$`.

#### Scenario: Missing creation keyword
- **WHEN** the validator runs with `--org-root org-invalid/missing-created/org` on `OSDB-0201-missing-created.org`, which has no `#+CREATED` line
- **THEN** it reports exactly one error, field `#+CREATED`, containing `keyword missing`

#### Scenario: Keyword given twice
- **WHEN** the validator runs with `--org-root org-invalid/duplicate-created/org` on `OSDB-0202-duplicate-created.org`, which has two `#+CREATED` lines
- **THEN** it reports exactly one error, field `#+CREATED`, containing `appears more than once`

#### Scenario: Active timestamp
- **WHEN** the validator runs with `--org-root org-invalid/active-timestamp/org` on `OSDB-0203-active-timestamp.org`, whose `#+LAST_MODIFIED` is `<2026-10-19 Mon 17:42:05>`
- **THEN** it reports exactly one error, field `#+LAST_MODIFIED`, containing `must be an inactive timestamp`

#### Scenario: Timestamp without seconds
- **WHEN** the validator runs with `--org-root org-invalid/missing-seconds/org` on `OSDB-0204-missing-seconds.org`, whose `#+CREATED` is `[2026-10-19 Mon 17:42]`
- **THEN** it reports exactly one error, field `#+CREATED`, containing `must have the form [YYYY-MM-DD Day hh:mm:ss]`

#### Scenario: Impossible calendar date
- **WHEN** the validator runs with `--org-root org-invalid/invalid-date/org` on `OSDB-0205-invalid-date.org`, whose `#+CREATED` is `[2026-02-30 Mon 10:00:00]`
- **THEN** it reports exactly one error, field `#+CREATED`, containing `is not a valid date`

#### Scenario: Weekday does not match the date
- **WHEN** the validator runs with `--org-root org-invalid/wrong-weekday/org` on `OSDB-0206-wrong-weekday.org`, whose `#+CREATED` is `[2026-10-19 Tue 17:42:05]`
- **THEN** it reports exactly one error, field `#+CREATED`, containing `weekday "Tue" does not match 2026-10-19 (Mon)`

#### Scenario: Local time skipped by the spring clock change
- **WHEN** the validator runs with `--org-root org-invalid/nonexistent-local-time/org` on `OSDB-0207-nonexistent-local-time.org`, whose `#+CREATED` is `[2026-03-29 Sun 02:30:00]` and `#+LAST_MODIFIED` is `[2026-03-29 Sun 04:00:00]`
- **THEN** it reports exactly one error, field `#+CREATED`, containing `does not exist in Europe/Berlin`

#### Scenario: Modification before creation
- **WHEN** the validator runs with `--org-root org-invalid/last-modified-before-created/org` on `OSDB-0208-last-modified-before-created.org`, whose `#+CREATED` is `[2026-10-19 Mon 17:42:05]` and `#+LAST_MODIFIED` is `[2026-10-18 Sun 09:00:00]`
- **THEN** it reports exactly one error, field `#+LAST_MODIFIED`, containing `is earlier than #+CREATED`

#### Scenario: Ambiguous fall-back hour can be in order
- **WHEN** the validator runs with only `--org-root valid/org` on `OSDB-0004-ambiguous-hour.org`, whose `#+CREATED` is `[2026-10-25 Sun 02:50:00]` and `#+LAST_MODIFIED` is `[2026-10-25 Sun 02:10:00]` (02:50 at +02:00 precedes 02:10 at +01:00)
- **THEN** no line is printed for that file, and the exit status is 0

#### Scenario: Empty AI model
- **WHEN** the validator runs with `--org-root org-invalid/bad-ai-model/org` on `OSDB-0209-bad-ai-model.org`, whose `#+AI_MODEL:` line has no value
- **THEN** it reports exactly one error, field `#+AI_MODEL`, containing `must be a model identifier or none`

#### Scenario: Org file name breaks the naming rule
- **WHEN** the validator runs with `--org-root org-invalid/bad-org-file-name/org` on `osdb-0210-lowercase.org`, whose keywords are otherwise valid
- **THEN** it reports exactly one error, field `file_name`, containing `must be named OSDB-NNNN-short-slug.org`

### Requirement: Org keywords map to exported front matter
The export of an Org procedure SHALL carry front matter as follows:
- `date` equal to `#+CREATED` and `lastmod` equal to `#+LAST_MODIFIED`. Each is read as Europe/Berlin local time and written as a TOML offset datetime with the same wall-clock time and the Europe/Berlin offset in force at that instant (`+01:00` or `+02:00`).
- `ai_model` equal to `#+AI_MODEL`, or no `ai_model` key at all when `#+AI_MODEL` is `none`.
- `slug` from `#+HUGO_SLUG`.
- No `author` key.

#### Scenario: Matching export passes
- **WHEN** the valid-set run checks `valid/org/OSDB-0003-*.org`, whose `#+CREATED` is `[2026-10-19 Mon 17:42:05]`, against its export, whose `date` is `2026-10-19T17:42:05+02:00`
- **THEN** no line is printed for either file

#### Scenario: Ambiguous hour exported in order
- **WHEN** the valid-set run checks `valid/org/OSDB-0004-ambiguous-hour.org` against `valid/export/OSDB-0004-ambiguous-hour.md`, whose `date` is `2026-10-25T02:50:00+02:00` and `lastmod` is `2026-10-25T02:10:00+01:00`
- **THEN** no line is printed for either file

#### Scenario: Exported instants decide the ordering
- **WHEN** a test copies `valid/org/OSDB-0004-ambiguous-hour.org` and `valid/export/OSDB-0004-ambiguous-hour.md` into temporary Org and content roots, changes the export's `lastmod` to `2026-10-25T02:10:00+02:00`, and makes a fixture run on the content root with the Org root as `--org-root`
- **THEN** it reports exactly one error, on the `.md` path, field `lastmod`, containing `is earlier than date`

#### Scenario: Exported date disagrees
- **WHEN** a fixture run on `org-invalid/export-date-mismatch/export` with `--org-root org-invalid/export-date-mismatch/org` checks `OSDB-0211-export-date-mismatch.org`, whose `#+CREATED` is `[2026-10-19 Mon 17:42:05]`, against its export, whose `date` is `2026-10-19T17:40:00+02:00`
- **THEN** it reports exactly one error, on the `.org` path, field `#+CREATED`, containing `does not match exported date`

#### Scenario: Exported offset is not the Berlin offset
- **WHEN** a fixture run on `org-invalid/export-offset-mismatch/export` with `--org-root org-invalid/export-offset-mismatch/org` checks `OSDB-0212-export-offset-mismatch.org`, whose `#+CREATED` is `[2026-10-19 Mon 17:42:05]`, against its export, whose `date` is `2026-10-19T17:42:05+01:00`
- **THEN** the exit status is 1, and stdout is exactly two lines
- **AND** one line is the error on the `.org` path, field `#+CREATED`, containing `does not match exported date`
- **AND** the other is a warning on the exported `.md` path, field `date`, containing `is not the Europe/Berlin offset`

#### Scenario: AI model recorded as none but exported
- **WHEN** a fixture run on `org-invalid/export-ai-model-mismatch/export` with `--org-root org-invalid/export-ai-model-mismatch/org` checks `OSDB-0213-export-ai-model-mismatch.org`, whose `#+AI_MODEL` is `none`, against its export, which has `ai_model = "example-model-1"`
- **THEN** it reports exactly one error, on the `.org` path, field `#+AI_MODEL`, containing `does not match exported ai_model`

### Requirement: Body sections
Every procedure body SHALL contain these eight level-2 sections, in this order:
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

### Requirement: Markdown template
The file `templates/procedure.md` SHALL be a complete procedure using the placeholder ID `OSDB-0000` and slug `osdb-0000`. It satisfies the following:
- Its front matter explains every field in TOML comments and shows the optional fields commented out.
- Its body has the eight sections, a Reagents table with the header `Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv`, and numbered lists under Procedure and Notes.
- Once `OSDB-0000` is replaced by a real ID and `osdb-0000` by its lowercase form, it validates against the shipped vocabulary with no errors and no warnings.

#### Scenario: Substituted Markdown template is clean
- **WHEN** a test copies `templates/procedure.md` to a temporary directory as `OSDB-0001-template.md`, replacing every `OSDB-0000` with `OSDB-0001` and every `osdb-0000` with `osdb-0001`, and runs the validator on that directory with the default vocabulary
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Unsubstituted Markdown template is rejected
- **WHEN** a test copies `templates/procedure.md` unchanged to a temporary directory as `OSDB-0000-template.md` and runs the validator on it
- **THEN** the exit status is 1, and stdout contains an error with field `id` containing `must be between OSDB-0001 and OSDB-9999`

### Requirement: Org template
The file `templates/procedure.org` SHALL be a complete Org procedure that satisfies the following:
- It carries `#+CREATED`, `#+LAST_MODIFIED` and `#+AI_MODEL` in the required format, with `#+AI_MODEL` naming the exact identifier of the model that wrote it, never `none`.
- It sets `#+HUGO_SLUG: osdb-0000` and `#+HUGO_TAGS`.
- It sets the keys `id` (as `OSDB-0000`), `authors`, `status`, `reaction_types`, `product`, `scale`, `yield_percent` and `hazards` on repeated `#+HUGO_CUSTOM_FRONT_MATTER:` lines.
- It sets `product` alone on the last `#+HUGO_CUSTOM_FRONT_MATTER:` line, because tomelr emits keys in order and every key after a `[product]` table header would parse as a member of that table.
- It has the eight body sections as top-level headings, in order.
- It does not set `#+DATE`, `#+HUGO_LASTMOD`, `#+HUGO_AUTO_SET_LASTMOD`, `#+HUGO_DRAFT`, `#+HUGO_BASE_DIR` or `#+HUGO_SECTION`.

#### Scenario: Org template passes the Org lint
- **WHEN** a test copies `templates/procedure.org` to a temporary directory as `OSDB-0001-template.org`, replacing `OSDB-0000` and `osdb-0000` as for the Markdown template, and runs the validator with only `--org-root` set to that directory
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Org template names its writing model
- **WHEN** a test reads the `#+AI_MODEL:` value of `templates/procedure.org`
- **THEN** the value is non-empty and is not `none`

#### Scenario: Org template carries the schema keywords and sections
- **WHEN** a test reads `templates/procedure.org`
- **THEN** it contains the line `#+HUGO_SLUG: osdb-0000` and a `#+HUGO_TAGS:` line
- **AND** the `#+HUGO_CUSTOM_FRONT_MATTER:` lines together contain `:id`, `:authors`, `:status`, `:reaction_types`, `:product`, `:scale`, `:yield_percent` and `:hazards`
- **AND** the last `#+HUGO_CUSTOM_FRONT_MATTER:` line contains `:product` and no other `:key`, and no earlier such line contains `:product`
- **AND** its top-level headings, in order, include `* Summary`, `* Reagents`, `* Procedure`, `* Workup and Purification`, `* Characterization`, `* Notes`, `* Hazards and Waste Disposal` and `* References`
- **AND** no line begins, case-insensitively, with `#+DATE:`, `#+HUGO_LASTMOD:`, `#+HUGO_AUTO_SET_LASTMOD:`, `#+HUGO_DRAFT:`, `#+HUGO_BASE_DIR:` or `#+HUGO_SECTION:`
