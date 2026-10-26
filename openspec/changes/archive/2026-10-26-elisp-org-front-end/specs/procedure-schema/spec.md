## ADDED Requirements

### Requirement: Exported values come only from the file-level keywords
An Org procedure source SHALL NOT set the exported `date`, `lastmod` or `ai_model`, or the name or location of its export, by any route other than `#+CREATED`, `#+LAST_MODIFIED`, `#+AI_MODEL` and its file name. These are the inputs from which the pinned ox-hugo would take those values instead of, or besides, the export's own. The export reports each of them as an error, after the checks of "Org file-level keywords", using that requirement's definition of a keyword line. In the messages below, `M` stands for `the export sets date, lastmod, ai_model and the export file name itself`. The rules are:
- **Keywords.** Each of `#+DATE`, `#+HUGO_LASTMOD`, `#+HUGO_AUTO_SET_LASTMOD`, `#+HUGO_FRONT_MATTER_KEY_REPLACE`, `#+EXPORT_FILE_NAME`, `#+HUGO_BASE_DIR`, `#+HUGO_BASE_CONTENT_FOLDER`, `#+HUGO_SECTION`, `#+HUGO_BUNDLE`, `#+SETUPFILE` and `#+INCLUDE` that occurs at least once gives one error. The field is that keyword, written as here, and the message is `must not be used; M`. The errors follow the order of this list.
- **Custom front matter.** The values of all `#+HUGO_CUSTOM_FRONT_MATTER` keyword lines, joined by single spaces, are split into keys as ox-hugo splits them. A key is a `:` that begins the text or follows a space or tab, outside double-quoted strings and parenthesised lists, together with the characters after it up to the next space, tab or end of text. Each of the keys `date`, `lastmod` and `ai_model`, compared case-insensitively, that occurs gives one error with field `#+HUGO_CUSTOM_FRONT_MATTER`. The messages are `must not set :date; the export writes it from #+CREATED`, `must not set :lastmod; the export writes it from #+LAST_MODIFIED` and `must not set :ai_model; the export writes it from #+AI_MODEL`, and the errors come in that order.
- **Property keywords.** A `#+PROPERTY` keyword line whose value begins with a property name that starts with `EXPORT_` or is `LOG_INTO_DRAWER`, compared case-insensitively, gives an error with field `#+PROPERTY` and the message `must not set <NAME>; M`. `<NAME>` is the property name in upper case. There is one error per distinct name, in order of first appearance.
- **Node properties.** A line whose text after optional spaces or tabs is `:<NAME>:` or `:<NAME>+:`, alone or followed by whitespace and a value, outside blocks, where `<NAME>` starts with `EXPORT_` or is `LOG_INTO_DRAWER` in any case, gives an error with field `:<NAME>:` (upper case) and the message `must not be used; M`. There is one error per distinct name, in order of first appearance.
- **Logbook drawers.** A line whose text, trimmed of spaces and tabs, is `:LOGBOOK:` in any case, outside blocks, gives one error with field `:LOGBOOK:` and the message `must not be used; M`.
- **Extra front matter.** A line that, after optional spaces or tabs, begins with `#+begin_src`, `#+header:`, `#+property:` or `:header-args`, compared case-insensitively, and contains `:front_matter_extra` in any case gives one error with field `:front_matter_extra` and the message `must not be used; M`. Such a line counts when it is outside blocks or opens a block. A source gives at most one such error.

Problems of this requirement follow those of "Org file-level keywords", in the order of the rules above.

#### Scenario: Keywords that would set exported values
- **WHEN** an ERT test examines, each alone in a temporary directory `R`, copies of `valid/org/OSDB-0003-propyl-acetate.org` with one added line `#+<keyword in lower case>: x` for each keyword of the first rule
- **THEN** each copy's problem lines are exactly `R/OSDB-0003-propyl-acetate.org:#+<KEYWORD>: error: must not be used; the export sets date, lastmod, ai_model and the export file name itself`

#### Scenario: Custom front matter that would set exported values
- **WHEN** an ERT test examines, each alone in a temporary directory `R`, copies of `valid/org/OSDB-0003-propyl-acetate.org` with one added line `#+HUGO_CUSTOM_FRONT_MATTER: :ai_model "example-model-1"`, `#+HUGO_CUSTOM_FRONT_MATTER: :Date 2026-01-01`, or `#+HUGO_CUSTOM_FRONT_MATTER: :lastmod 2026-01-01 :date 2026-01-01`
- **THEN** the problem lines are exactly, in turn, `R/OSDB-0003-propyl-acetate.org:#+HUGO_CUSTOM_FRONT_MATTER: error: must not set :ai_model; the export writes it from #+AI_MODEL`; `R/OSDB-0003-propyl-acetate.org:#+HUGO_CUSTOM_FRONT_MATTER: error: must not set :date; the export writes it from #+CREATED`; and that same `:date` line followed by `R/OSDB-0003-propyl-acetate.org:#+HUGO_CUSTOM_FRONT_MATTER: error: must not set :lastmod; the export writes it from #+LAST_MODIFIED`

#### Scenario: Colons inside values are not keys
- **WHEN** an ERT test examines a copy of `valid/org/OSDB-0003-propyl-acetate.org` with the added line `#+HUGO_CUSTOM_FRONT_MATTER: :notes "see :date" :refs '(":lastmod" "a :ai_model")`
- **THEN** it returns no problem

#### Scenario: Export properties and logbooks
- **WHEN** an ERT test examines, each alone in a temporary directory `R`, copies of `valid/org/OSDB-0003-propyl-acetate.org` with, in turn, the added line `#+PROPERTY: EXPORT_FILE_NAME other`; the added line `#+property: log_into_drawer t`; a property drawer `:PROPERTIES:`, `:EXPORT_DATE: [2026-01-01 Thu]`, `:END:` under its first heading; and a drawer `:LOGBOOK:`, `- Note taken on [2026-01-01 Thu 10:00]`, `:END:` under its first heading
- **THEN** the problem lines are exactly, in turn, with `P` for `R/OSDB-0003-propyl-acetate.org` and `M` as above: `P:#+PROPERTY: error: must not set EXPORT_FILE_NAME; M`; `P:#+PROPERTY: error: must not set LOG_INTO_DRAWER; M`; `P::EXPORT_DATE:: error: must not be used; M`; and `P::LOGBOOK:: error: must not be used; M`

#### Scenario: Extra front matter
- **WHEN** an ERT test examines, each alone in a temporary directory `R`, copies of `valid/org/OSDB-0003-propyl-acetate.org` with, under its first heading, in turn: a block `#+begin_src toml :front_matter_extra t`, `ai_model = "example-model-1"`, `#+end_src`; the same block opened by `#+begin_src toml` after the line `#+header: :front_matter_extra t`; the added line `#+PROPERTY: header-args:toml :front_matter_extra t`; and a property drawer `:PROPERTIES:`, `:header-args:toml: :front_matter_extra t`, `:END:`
- **THEN** each copy's problem lines are exactly `R/OSDB-0003-propyl-acetate.org::front_matter_extra: error: must not be used; the export sets date, lastmod, ai_model and the export file name itself`

#### Scenario: Forbidden lines inside blocks are ignored
- **WHEN** an ERT test examines a copy of `valid/org/OSDB-0003-propyl-acetate.org` with the lines `#+DATE: x`, `#+HUGO_CUSTOM_FRONT_MATTER: :date x`, `:EXPORT_DATE: x` and `:LOGBOOK:` added between a `#+begin_example` line and a `#+end_example` line
- **THEN** it returns no problem

## MODIFIED Requirements

### Requirement: Org file-level keywords
Every Org procedure source SHALL carry each of the file-level keywords `#+CREATED`, `#+LAST_MODIFIED` and `#+AI_MODEL` exactly once. A keyword line is a line made of optional spaces or tabs, `#+`, a name of ASCII letters and underscores, matched case-insensitively, a `:` and the value. The value is trimmed of spaces, tabs and CRs. A line whose text after optional spaces or tabs begins with `#+begin_`, in any case, opens a block. The block runs to the next line that begins the same way with `#+end_`, and no line from the opening line to the closing line is a keyword line. The following rules apply to the values:
- Each timestamp is an Org inactive timestamp of the exact form `[YYYY-MM-DD Day hh:mm:ss]`. Its digits are the ASCII digits `0` to `9`, and `Day` is a run of characters other than spaces, tabs, `]` and `>`.
- Its date and time are valid, and `Day` is the English three-letter abbreviation (`Mon` … `Sun`) of that date.
- It is Europe/Berlin local wall-clock time, carrying no offset, and names a time that exists in Europe/Berlin.
- `#+LAST_MODIFIED` is not earlier than `#+CREATED`, compared as follows. A wall-clock time in the autumn fall-back hour maps to two instants, so the earliest possible instant of `#+CREATED` is compared with the latest possible instant of `#+LAST_MODIFIED`. The check passes when the first is not later than the second, that is, when some choice of Berlin offsets puts the two in order. The exported `lastmod >= date` comparison is the authoritative ordering check.
- `#+AI_MODEL` is `none` for human-authored files, or otherwise a single model identifier matching `^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$`.

The export checks these rules, as org-export "Org sources and their problems" states. A keyword that is missing or given more than once gets one error and no further check. A timestamp gets at most one error, from the first of these checks that fails: form (including brackets that do not pair, such as `[` with `>`), active, date, time, weekday, existence. The ordering check runs only when both timestamps are present once and valid. The `#+AI_MODEL` check is independent of the timestamps. Problems are reported in the order `#+CREATED`, `#+LAST_MODIFIED`, `#+AI_MODEL`, ordering. The messages are:

| Problem | Field | Message |
|---|---|---|
| Missing keyword | the keyword | `keyword missing` |
| Repeated keyword | the keyword | `appears more than once` |
| Wrong form | the keyword | `"<value>" must have the form [YYYY-MM-DD Day hh:mm:ss]` |
| Active timestamp | the keyword | `"<value>" must be an inactive timestamp in square brackets, [YYYY-MM-DD Day hh:mm:ss]` |
| Invalid date | the keyword | `"<value>" is not a valid date` |
| Invalid time | the keyword | `"<value>" is not a valid time` |
| Wrong weekday | the keyword | `weekday "<given>" does not match <YYYY-MM-DD> (<expected>)` |
| Skipped time | the keyword | `"<value>" does not exist in Europe/Berlin (skipped by the clock change)` |
| Wrong order | `#+LAST_MODIFIED` | `is earlier than #+CREATED` |
| Bad AI model | `#+AI_MODEL` | `must be a model identifier or none` |

#### Scenario: Missing creation keyword
- **WHEN** an ERT test examines `org-invalid/missing-created/org/OSDB-0201-missing-created.org`, which has no `#+CREATED` line
- **THEN** it reports exactly one error with field `#+CREATED` containing `keyword missing`

#### Scenario: Keyword given twice
- **WHEN** an ERT test examines `org-invalid/duplicate-created/org/OSDB-0202-duplicate-created.org`, which has two `#+CREATED` lines
- **THEN** it reports exactly one error with field `#+CREATED` containing `appears more than once`

#### Scenario: Active timestamp
- **WHEN** an ERT test examines `org-invalid/active-timestamp/org/OSDB-0203-active-timestamp.org`, whose `#+LAST_MODIFIED` is `<2026-10-19 Mon 17:42:05>`
- **THEN** it reports exactly one error with field `#+LAST_MODIFIED` containing `must be an inactive timestamp`

#### Scenario: Timestamp without seconds
- **WHEN** an ERT test examines `org-invalid/missing-seconds/org/OSDB-0204-missing-seconds.org`, whose `#+CREATED` is `[2026-10-19 Mon 17:42]`
- **THEN** it reports exactly one error with field `#+CREATED` containing `must have the form [YYYY-MM-DD Day hh:mm:ss]`

#### Scenario: Impossible calendar date
- **WHEN** an ERT test examines `org-invalid/invalid-date/org/OSDB-0205-invalid-date.org`, whose `#+CREATED` is `[2026-02-30 Mon 10:00:00]`
- **THEN** it reports exactly one error with field `#+CREATED` containing `is not a valid date`

#### Scenario: Invalid date does not cascade
- **WHEN** the same ERT test formats the problems it found
- **THEN** there is exactly one line, and it contains neither `weekday` nor `earlier than`

#### Scenario: Weekday does not match the date
- **WHEN** an ERT test examines `org-invalid/wrong-weekday/org/OSDB-0206-wrong-weekday.org`, whose `#+CREATED` is `[2026-10-19 Tue 17:42:05]`
- **THEN** it reports exactly one error with field `#+CREATED` containing `weekday "Tue" does not match 2026-10-19 (Mon)`

#### Scenario: Local time skipped by the spring clock change
- **WHEN** an ERT test examines `org-invalid/nonexistent-local-time/org/OSDB-0207-nonexistent-local-time.org`, whose `#+CREATED` is `[2026-03-29 Sun 02:30:00]` and `#+LAST_MODIFIED` is `[2026-03-29 Sun 04:00:00]`
- **THEN** it reports exactly one error with field `#+CREATED` containing `does not exist in Europe/Berlin`

#### Scenario: Modification before creation
- **WHEN** an ERT test examines `org-invalid/last-modified-before-created/org/OSDB-0208-last-modified-before-created.org`, whose `#+CREATED` is `[2026-10-19 Mon 17:42:05]` and `#+LAST_MODIFIED` is `[2026-10-18 Sun 09:00:00]`
- **THEN** it reports exactly one error with field `#+LAST_MODIFIED` containing `is earlier than #+CREATED`

#### Scenario: Modification before creation across the fall-back hour
- **WHEN** an ERT test examines a temporary directory holding a copy of `valid/org/OSDB-0004-ambiguous-hour.org` whose `#+CREATED` is `[2026-10-25 Sun 03:00:00]` and `#+LAST_MODIFIED` is `[2026-10-25 Sun 02:10:00]` (03:00 at +01:00 follows both instants of 02:10)
- **THEN** it reports exactly one error with field `#+LAST_MODIFIED` containing `is earlier than #+CREATED`

#### Scenario: Ambiguous fall-back hour can be in order
- **WHEN** an ERT test examines `valid/org/OSDB-0004-ambiguous-hour.org`, whose `#+CREATED` is `[2026-10-25 Sun 02:50:00]` and `#+LAST_MODIFIED` is `[2026-10-25 Sun 02:10:00]` (02:50 at +02:00 precedes 02:10 at +01:00)
- **THEN** it returns no problem, and its sources include `OSDB-0004-ambiguous-hour` with the AI model `claude-sonnet-5-5`

#### Scenario: Empty AI model
- **WHEN** an ERT test examines `org-invalid/bad-ai-model/org/OSDB-0209-bad-ai-model.org`, whose `#+AI_MODEL:` line has no value
- **THEN** it reports exactly one error with field `#+AI_MODEL` containing `must be a model identifier or none`

#### Scenario: Org file name breaks the naming rule
- **WHEN** an ERT test examines `org-invalid/bad-org-file-name/org/osdb-0210-lowercase.org`, whose keywords are otherwise valid
- **THEN** it reports exactly one error with field `file_name` containing `must be named OSDB-NNNN-short-slug.org`

#### Scenario: Invalid time
- **WHEN** an ERT test examines a temporary directory `R` holding a copy of `valid/org/OSDB-0003-propyl-acetate.org` whose `#+CREATED` is `[2026-10-19 Mon 24:00:00]`
- **THEN** the problem lines are exactly `R/OSDB-0003-propyl-acetate.org:#+CREATED: error: "[2026-10-19 Mon 24:00:00]" is not a valid time`

#### Scenario: Dependent checks of the keywords
- **WHEN** an ERT test examines, each alone in a temporary directory `R`, copies of `valid/org/OSDB-0003-propyl-acetate.org` with these keyword lines replaced, removed or added:
  1. `#+CREATED: [2026-10-19 Mon 17:42]` and `#+LAST_MODIFIED: [2026-10-18 Sun 09:00:00]`;
  2. `#+LAST_MODIFIED: [2026-03-29 Sun 02:30:00]`;
  3. a second line `#+CREATED: [2026-10-19 Mon 17:42:05]`, and `#+LAST_MODIFIED: [2026-10-18 Sun 09:00:00]`;
  4. no `#+LAST_MODIFIED` line;
  5. `#+CREATED: <2026-10-19 Mon 17:42:05>`, `#+LAST_MODIFIED: [2026-02-30 Mon 10:00:00]` and `#+AI_MODEL: two words`;
  6. `#+CREATED: [2026-03-29 Mon 02:30:00]`;
  7. `#+CREATED: [2026-02-30 Mon 25:00:00]`;
  8. `#+CREATED: [2026-10-19 Mon 17:42:05>`;
  9. `#+AI_MODEL: example-model-1`
- **THEN** the problem lines, with `P` standing for `R/OSDB-0003-propyl-acetate.org`, are exactly:
  1. `P:#+CREATED: error: "[2026-10-19 Mon 17:42]" must have the form [YYYY-MM-DD Day hh:mm:ss]`;
  2. `P:#+LAST_MODIFIED: error: "[2026-03-29 Sun 02:30:00]" does not exist in Europe/Berlin (skipped by the clock change)`;
  3. `P:#+CREATED: error: appears more than once`;
  4. `P:#+LAST_MODIFIED: error: keyword missing`;
  5. `P:#+CREATED: error: "<2026-10-19 Mon 17:42:05>" must be an inactive timestamp in square brackets, [YYYY-MM-DD Day hh:mm:ss]`, then `P:#+LAST_MODIFIED: error: "[2026-02-30 Mon 10:00:00]" is not a valid date`, then `P:#+AI_MODEL: error: must be a model identifier or none`;
  6. `P:#+CREATED: error: weekday "Mon" does not match 2026-03-29 (Sun)`;
  7. `P:#+CREATED: error: "[2026-02-30 Mon 25:00:00]" is not a valid date`;
  8. `P:#+CREATED: error: "[2026-10-19 Mon 17:42:05>" must have the form [YYYY-MM-DD Day hh:mm:ss]`;
  9. none, and the source's AI model is `example-model-1`

#### Scenario: Keyword lines
- **WHEN** an ERT test examines, each alone, copies of `valid/org/OSDB-0003-propyl-acetate.org` whose `#+CREATED` line is written as `#+created: [2026-10-19 Mon 17:42:05]`; as `  #+CREATED:   [2026-10-19 Mon 17:42:05]  `; and moved between a `#+begin_example` line and a `#+END_EXAMPLE` line
- **THEN** the first two give no problem, and the third reports exactly one error with field `#+CREATED` containing `keyword missing`

#### Scenario: ASCII digits and ASCII trimming
- **WHEN** an ERT test examines, each alone in a temporary directory `R`, copies of `valid/org/OSDB-0003-propyl-acetate.org` whose `#+CREATED` value is `[٢٠٢٦-10-19 Mon 17:42:05]`, written with Arabic-Indic digits, and `[2026-10-19 Mon 17:42:05]` followed by a no-break space (U+00A0)
- **THEN** each gives exactly one line, `R/OSDB-0003-propyl-acetate.org:#+CREATED: error: "<value>" must have the form [YYYY-MM-DD Day hh:mm:ss]`, with the value as written, no-break space included

### Requirement: Org keywords map to exported front matter
The export of an Org procedure SHALL carry front matter as follows:
- `date` equal to `#+CREATED` and `lastmod` equal to `#+LAST_MODIFIED`. Each is read as Europe/Berlin local time and written as a TOML offset datetime with the same wall-clock time and the Europe/Berlin offset in force at that instant (`+01:00` or `+02:00`).
- `ai_model` equal to `#+AI_MODEL`, or no `ai_model` key at all when `#+AI_MODEL` is `none`.
- `slug` from `#+HUGO_SLUG`.
- No `author` key.

#### Scenario: Exported dates match the fixture exports
- **WHEN** an integration test adds `org/procedures/` to a copy of the test collection `tests/fixtures/collection/`, holding only copies of `tests/fixtures/valid/org/OSDB-0003-propyl-acetate.org` and `tests/fixtures/valid/org/OSDB-0004-ambiguous-hour.org`, and runs `tools/orgsyndb -C <collection> export`
- **THEN** it exits 0, and the `date`, `lastmod` and `ai_model` of each export, or the absence of `ai_model`, equal those of the file with the same stem in `tests/fixtures/valid/export/`
- **AND** for `OSDB-0004-ambiguous-hour` these are `date = 2026-10-25T02:50:00+02:00`, `lastmod = 2026-10-25T02:10:00+01:00` and `ai_model = "claude-sonnet-5-5"`

#### Scenario: Exported instants decide the ordering
- **WHEN** a test copies `valid/export/OSDB-0004-ambiguous-hour.md` into a temporary content root, changes its `lastmod` to `2026-10-25T02:10:00+02:00`, and makes a fixture run on that root
- **THEN** it reports exactly one error, on the `.md` path, field `lastmod`, containing `is earlier than date`

### Requirement: Org template
The file `templates/procedure.org` SHALL be a complete Org procedure that satisfies the following:
- It carries `#+CREATED`, `#+LAST_MODIFIED` and `#+AI_MODEL` in the required format, with `#+AI_MODEL` naming the exact identifier of the model that wrote it, never `none`.
- It sets `#+HUGO_SLUG: osdb-0000` and `#+HUGO_TAGS`.
- It sets the keys `id` (as `OSDB-0000`), `authors`, `status`, `reaction_types`, `product`, `scale`, `yield_percent` and `hazards` on repeated `#+HUGO_CUSTOM_FRONT_MATTER:` lines.
- It sets `product` alone on the last `#+HUGO_CUSTOM_FRONT_MATTER:` line, because tomelr emits keys in order and every key after a `[product]` table header would parse as a member of that table.
- It has the eight body sections as top-level headings, in order.
- It does not set `#+DATE`, `#+HUGO_LASTMOD`, `#+HUGO_AUTO_SET_LASTMOD`, `#+HUGO_DRAFT`, `#+HUGO_BASE_DIR` or `#+HUGO_SECTION`.

#### Scenario: Org template passes the Org checks
- **WHEN** an ERT test copies `templates/procedure.org` to a temporary directory as `OSDB-0001-template.org`, replacing every `OSDB-0000` with `OSDB-0001` and every `osdb-0000` with `osdb-0001`, and calls `osdb-org-examine` on that directory
- **THEN** it returns no problem and one source

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
