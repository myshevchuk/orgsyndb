## Context

The repository holds only an initialised `openspec/`. This change is the
first of three:

1. `add-procedure-schema` (this change) covers the schema, vocabulary,
   templates, validator, fixtures and tests.
2. `add-build-pipeline` covers `export.el`, `build.fish`, the Hugo config,
   the minimum layouts, Pagefind, PDF, the hook and the seed samples.
3. `add-site-theme` covers the theme, the remaining samples and the
   structure images.

ox-hugo is not installed; change 2 bootstraps it into a repo-local package
directory. Hugo 0.162.1 (the Fedora 44 build, extended) and WeasyPrint 70.0
are installed on the owner's machine, but nothing in this change runs them.
The validator therefore cannot run on real export output yet, and the
interfaces it fixes have to be pinned down here so that change 2 can
conform to them.

Constraints from the brief and the owner:

- Front matter is TOML (`+++`) for both formats.
- The validator is Python 3 with the standard library only, and runs on
  merged, exported content so that one code path covers both formats.
- Org timestamps are Europe/Berlin local wall-clock time (CET/CEST), not a
  fixed GMT+1.
- The co-worker writes Markdown by hand from a template and knows neither
  Org, git nor Hugo, so every rule they can break must yield a message they
  can act on.
- No user or machine identifiers may enter committed files.

The stakeholders are the owner (Org author, maintainer), the co-worker
(Markdown author), and changes 2 and 3, which consume these interfaces.

## Goals / Non-Goals

**Goals:**

- One written, testable definition of a valid procedure, shared by both
  source formats.
- A validator whose every rejection is pinned by a fixture and a test, with
  messages naming the field and the expected value.
- Interfaces exact enough that change 2 can be built and checked against
  them: the validator CLI, the template placeholders, the mapping from Org
  keywords to front matter, and the slug/URL rule.

**Non-Goals:**

- Running ox-hugo or Hugo, and any build, export, layout, search, PDF or
  hook work. These belong to changes 2 and 3.
- Enforcing that IDs are never reused over time. That needs history, and
  the validator sees only the current tree.
- Checking chemistry: formula syntax, SMILES validity, or that MW, mmol and
  equivalents agree.
- Checking the Reagents table's columns, numbered steps, or anything inside
  a section beyond its heading.
- Writing `docs/SCHEMA.md` or any other document a person reads. The doc
  writer does that after implementation, from this change.

## Decisions

### D1. Validator input contract: explicit roots, location-relative defaults

The interface is
`tools/validate.py [--org-root DIR]... [--vocabulary FILE] [--static-dir DIR] [CONTENT_ROOT ...]`.

- **Content roots** are positional. Each is a directory whose top-level
  `*.md` files are procedures with `+++` TOML front matter. A subdirectory
  is an error (D11). Change 2 will pass the ox-hugo export directory and
  `md/procedures/`, and will mount exactly those two directories into the
  Hugo `procedures` section. Every page Hugo publishes there is then a
  top-level file the validator has checked.
- **Org roots** (`--org-root`, repeatable) are directories of Org sources,
  linted as described in D2.
- At least one root of either kind is required. Otherwise the validator
  exits 2. This keeps the validator from silently validating nothing when
  the caller forgets an argument.
- `--vocabulary` defaults to `<repo>/site/data/reaction_types.toml`, and
  `--static-dir` defaults to `<repo>/site/static`. Here `<repo>` is the
  parent of the directory that holds the resolved script file
  (`Path(__file__).resolve().parent.parent`), never the working directory.
- **Output** goes to stdout, one line per problem:
  `<path>:<field>: <severity>: <message>`. Severity is `error` or `warning`.
  - `<path>` is the root argument as given, joined with the file name. A
    relative root therefore yields relative paths, which suits a build
    script that passes repo-relative roots.
  - `<field>` is the front-matter key in dotted form for nested keys
    (`product.cas`). It is the Org keyword with its `#+` prefix for Org
    lints (`#+CREATED`). Otherwise it is one of the pseudo-fields
    `file_name`, `front_matter` or `body`.
- After all problem lines, one summary line goes to stderr:
  `validated <F> files: <E> errors, <W> warnings`.
- **Exit codes:**
  - `0`: no errors (warnings allowed).
  - `1`: at least one error.
  - `2`: usage or configuration error. This covers no roots, a root that is
    not a directory, and a vocabulary file that is missing, unparseable or
    malformed. It also covers the `Europe/Berlin` zone being unavailable,
    because a validator that cannot read its rules must not report
    success. Configuration errors go to stderr as
    `validate.py: error: <message>`, matching argparse's own usage errors,
    which already exit 2.
- Files are examined in sorted path order, and checks within a file run in
  a fixed order, so the output is deterministic.
- A missing static directory is not a configuration error. It only makes
  every `structure_image` unresolvable, which is reported per file.
  `site/static/` will not exist until a later change.

*Rejected alternatives:*

- *Defaults for the content roots* (e.g. `<repo>/md/procedures`). The export
  directory is change 2's decision. A default that covers only one tree
  would also silently skip the cross-tree duplicate-ID check.
- *Resolving defaults from the cwd.* `build.fish` must work from any
  directory, and so must the validator it calls.
- *A config file.* It would add a file for three paths.
- *JSON output.* The brief asks for human-readable lines, and nothing
  consumes machine output yet.

### D2. The validator also lints Org sources, and cross-checks them against their export

The three Org keywords exist only in the Org source, so exported TOML alone
cannot show that they are present and well formed. With `--org-root DIR`,
the validator reads each top-level `*.org` file in `DIR` and checks the
following:

- the file name follows the same `OSDB-NNNN-short-slug` rule;
- each of `#+CREATED`, `#+LAST_MODIFIED` and `#+AI_MODEL` appears exactly
  once (keyword names are case-insensitive, as in Org);
- both timestamps match `[YYYY-MM-DD Day hh:mm:ss]` exactly;
- the timestamps are inactive (square brackets);
- each date is a real calendar date with a valid time;
- each weekday is the English abbreviation of that date;
- each local time exists in Europe/Berlin, which excludes the spring-forward
  gap;
- `#+LAST_MODIFIED` is not earlier than `#+CREATED`, under the rule for
  ambiguous times below;
- `#+AI_MODEL` is `none` or a single model identifier.

**Ordering across the autumn fall-back hour.** An Org timestamp carries no
offset, so a wall-clock time between 02:00 and 03:00 on the last Sunday of
October names two instants. The lint compares the *earliest* possible
instant of `#+CREATED` with the *latest* possible instant of
`#+LAST_MODIFIED`, and passes when the first is not later than the second.
In other words, it passes when some choice of offsets puts the pair in
order. For example, `[2026-10-25 Sun 02:50:00]` followed by
`[2026-10-25 Sun 02:10:00]` passes, because 02:50+02:00 precedes
02:10+01:00. The source cannot settle which offset was meant, so the lint
rejects only orderings that are impossible. The authoritative ordering
check is `lastmod >= date` on the exported content file, whose offsets are
explicit (D5). The cross-check below accepts either Berlin offset for an
ambiguous time, so an export that picks offsets placing `lastmod` before
`date` fails on the content file, not on the Org source.

*Rejected alternatives for ambiguous times:*

- Always assume the first occurrence (`fold=0`). That would reject the
  example above, although the owner may have written it correctly.
- Reject every timestamp in the ambiguous hour. That puts a whole hour of
  the year out of bounds for no gain.

**Cross-check.** When at least one content root is also given, every Org
file must have an exported counterpart: a content file with the same stem
(`X.org` matches `X.md`) in some content root. Each Org file is then
checked against that file:

- `date` must equal `#+CREATED` interpreted in Europe/Berlin. The exported
  wall-clock time equals the Org time, and the exported offset is the
  Europe/Berlin offset at that instant.
- `lastmod` must equal `#+LAST_MODIFIED` in the same way.
- `ai_model` must be absent when `#+AI_MODEL` is `none`, and equal to it
  otherwise.

Problems are reported against the Org file, because that is the file the
owner edits.

This turns the brief's acceptance criterion 9 (exported `date` and
`lastmod` match the Org keywords) into a check run on every build. It
catches two things only: an Org source with no export, and an export
whose `date`, `lastmod` or `ai_model` disagrees with its source. It does
not show that the rest of an export is current. An export changed in body
or other fields but not in those three passes. It also cannot recognise an
orphaned export whose Org source was deleted, because that file is
indistinguishable from any other content file and is validated, and
published, as one. Keeping exports fresh and removing orphans belong to
change 2. Its export must write into a directory it empties first, or an
equivalent mechanism that change 2 chooses. When only Org roots are given,
the cross-check is skipped. That allows lint-only runs, which the Org
template test uses.

*Rejected alternatives:*

- *Lint the Org keywords inside `export.el`.* That puts a schema rule in
  Emacs Lisp, leaves it untestable without Emacs, and splits the rules
  across two languages.
- *Have export emit the raw keywords as extra front-matter keys for the
  validator.* That pollutes the published front matter, and the result is
  still not a check on the source.
- *Search Org roots recursively.* One file per procedure in a flat
  directory is the brief's layout. A subdirectory is an error instead (D11).
- *Match Org files to exports by `id` instead of stem.* That needs the Org
  `id`, which is buried in `#+HUGO_CUSTOM_FRONT_MATTER`. ox-hugo already
  names the output after the source file (see Verification).

### D3. URL: a required `slug` field equal to the lowercased ID

Hugo's permalink tokens (current docs) are date parts, `:section(s)`,
`:sectionslug(s)`, `:title`, `:slug`, `:contentbasename` and
`:slugorcontentbasename`. None of them reads an arbitrary front-matter
parameter such as `id`. So `/procedures/osdb-0001/` cannot come from the
file name `OSDB-0001-short-slug.*` alone.

The decision has four parts:

- Every procedure carries `slug = "osdb-0001"`.
- The validator requires it and requires it to equal `id.lower()` exactly.
  The message states the expected value: `must be "osdb-0001" (the
  lowercased id)`.
- Change 2 sets the `procedures` permalink to `/procedures/:slug/`.
- In Org, the slug is written as `#+HUGO_SLUG: osdb-0001`, which ox-hugo
  emits as `slug`. Both templates carry the placeholder `osdb-0000`, which
  `build.fish new` replaces.

This is the least error-prone option for the co-worker. `new` fills the
value, so it is never typed. If it is edited wrongly, the error message
gives the exact correction, and the failure is caught before Hugo
publishes a wrong URL. `:slug` falls back to the title when `slug` is
absent, which is why `slug` is required rather than optional.

*Rejected alternatives:*

- *`url = "/procedures/osdb-0001/"` per file.* It has the same sync problem
  with more characters to get wrong, and it bypasses the permalink config.
  `url` is in fact rejected (D4).
- *Rename files at build time* (copy `md/procedures/*` into a staging tree
  as `osdb-0001.md`). The co-worker would write nothing extra, but a
  copy step would replace the brief's mount-based merge. The page's
  source path in Hugo would no longer be the file the author edits.
  Changes the co-worker makes while the preview server runs would
  need a re-copy.
- *Hugo content adapters.* They are far more machinery than one field.
- *Accept any case (`slug = "OSDB-0001"`) and rely on Hugo's default
  lowercasing of paths.* It works only while `disablePathToLower` stays
  false, and allowing two spellings of one value invites drift. One exact
  value is simpler to state and to check.

### D4. Unknown and extra keys

Keys fall into four sets:

- **Schema keys** (the required and optional fields, plus `slug`) are
  checked by their own rules.
- **Tolerated Hugo/ox-hugo keys** pass silently, subject to type rules:
  - `draft` must be the boolean `false`;
  - `description` must be a string;
  - `aliases` must be a list of strings;
  - `weight` must be an integer.

  ox-hugo emits `draft` on every export (verified in source), so it has to
  be allowed. The other three are harmless Hugo features an author might
  reasonably use.
- **Rejected keys** are errors:
  - `draft = true` is an error ("use status, not draft"). Hugo silently
    drops draft pages, so a procedure would vanish from the site, and
    workflow state belongs in `status`.
  - `author` is an error ("use authors"). ox-hugo exports `author` by
    default from `user-full-name`, which under `emacs --batch -Q` would
    publish a machine-derived name. Rejecting it forces change 2 to
    disable ox-hugo's author export (`org-export-with-author` nil or
    `#+options: author:nil`). The schema's taxonomy is `authors`.
  - `url` is an error ("the URL is derived from slug"), because it would
    override the permalink rule of D3.
- **Any other key is a warning** ("unknown field"). A misspelt optional
  key (`checkedby`) would otherwise be silently ignored. A misspelt
  required key is already caught as missing. Unknown keys inside
  `product` are also warnings.

*Rejected alternatives:*

- *Unknown keys are errors.* Any ox-hugo upgrade that adds an emitted key
  would break the build, which is too brittle.
- *Unknown keys are allowed silently.* Typos in optional fields would be
  lost.
- *Tolerating `author` and `categories` as Hugo-standard keys.* `author`
  carries the privacy risk above. `categories` is simply unknown and so a
  warning, since `reaction_types` plays the category role.

### D5. `date` and `lastmod` are TOML offset datetimes

- `date` and `lastmod` must be TOML offset datetimes, which `tomllib`
  returns as timezone-aware `datetime` values.
- A string, a local datetime (no offset), or a bare date is an error
  ("must be a TOML offset datetime"). The value is then still correct for
  Hugo, but carries no unambiguous instant.
- `lastmod >= date` is compared as instants.
- On every content file, an offset that is not the Europe/Berlin offset at
  that instant is a **warning**. For example, `2026-07-01T10:00:00+01:00`
  is the instant `11:00+02:00` in Berlin. The instant is still exact and
  Hugo orders it correctly; only the displayed local time is off. The
  co-worker updates `lastmod` by hand and could plausibly keep a winter
  offset into summer.

This is what ox-hugo emits. `org-hugo-date-format` defaults to
`%Y-%m-%dT%T%z`, and ox-hugo inserts the colon into the offset. tomelr, its
TOML encoder, writes any string matching its RFC 3339 regexp unquoted, so
both `#+date` values and custom-front-matter values reach the TOML as
datetimes (verified in source; see Verification). A hand-written
Markdown file uses the same literal form, which `build.fish new --md` will
fill.

*Rejected alternatives:*

- *Accept strings and parse them.* That puts two representations in the
  tree. Hugo accepts both, but the theme would then format two kinds of
  value, and "Org and Markdown indistinguishable" becomes harder to show.
- *Accept local datetimes and assume Berlin.* An exported page would then
  depend on Hugo's `timeZone` setting to mean the right instant.
- *Make a wrong offset an error.* It is not wrong data, only an
  inconsistent display. An error would block the co-worker's build for a
  cosmetic issue.

### D6. Body sections: level-2 ATX headings, case-insensitive exact text

- **Canonical headings**, in order: `Summary`, `Reagents`, `Procedure`,
  `Workup and Purification`, `Characterization`, `Notes`,
  `Hazards and Waste Disposal`, `References`.
- **Org mapping.** In Org they are top-level headings (`* Summary`), which
  ox-hugo exports as `## Summary {#summary}`. Its default
  `HUGO_LEVEL_OFFSET` is 1 and its headline style is ATX. It appends a
  `{#anchor}` by default, controlled by `org-hugo-headline-anchor`, which
  defaults to `t` (verified in source). Recognition accepts headings with
  and without the anchor, so the option's setting does not matter.
- **Recognition.** A heading is a line matching `^##[ \t]+(.+)$` outside
  fenced code blocks (lines between matching ```` ``` ```` or `~~~`
  fences). Its text is taken after removing a trailing `{...}` attribute
  block and a trailing closing `#` sequence, then trimming and collapsing
  internal whitespace. `#` and `###`+ headings are ignored, and setext
  headings are not recognised; the template uses ATX.
- **Matching.** The text matches a canonical heading when the two are
  equal case-insensitively. The match is exact otherwise: no fuzzy or
  partial matching.
- **Missing sections.** Each canonical heading with no match gives one
  `body` warning: `missing section "Notes"`.
- **Order.** Take the canonical headings that are present, in order of
  their first occurrence. If that sequence is not in canonical order, one
  `body` warning is given per file. It contains `out of order` and lists
  the expected order.
- **Other headings.** Extra `##` headings are allowed silently.

All of these are warnings, never errors, per brief §5.4.

*Rejected alternatives:*

- *Case-sensitive matching.* It would warn about "Workup and purification",
  which is a cosmetic difference.
- *Fuzzy matching.* Its behaviour is hard to state as a contract and hard to
  predict for the author.
- *Parsing Markdown properly.* That needs a dependency. Line-based ATX
  matching with fence tracking is enough for template-shaped documents.
- *Errors for missing sections.* The brief fixes these as warnings.

### D7. Vocabulary file: one table per slug with a `label`

`site/data/reaction_types.toml` holds one table per reaction type:

```toml
[esterification]
label = "Esterification"
```

The rules:

- Keys are slugs matching `^[a-z0-9]+(-[a-z0-9]+)*$`.
- Each entry is a table with a non-empty string `label`. Other keys in an
  entry are allowed and ignored, which leaves room for a later
  `description`.
- A file that breaks these rules is a configuration error (exit 2).
- Hugo exposes the file as `site.Data.reaction_types`. Hyphenated keys need
  `index` in templates, which is change 3's concern.

The initial entries, alphabetical, are listed below. Brief §6.4's reaction
maps onto them as follows:

| Slug | Label | Covers |
|---|---|---|
| `acylation` | Acylation | aspirin synthesis |
| `aldol-condensation` | Aldol condensation | Claisen–Schmidt condensation |
| `alkylation` | Alkylation | |
| `amide-coupling` | Amide coupling | |
| `cross-coupling` | Cross-coupling | Suzuki coupling |
| `cycloaddition` | Cycloaddition | |
| `deprotection` | Deprotection | |
| `esterification` | Esterification | Fischer esterification |
| `hydrolysis` | Hydrolysis | |
| `nucleophilic-substitution` | Nucleophilic substitution | |
| `olefination` | Olefination | Wittig olefination |
| `oxidation` | Oxidation | |
| `protection` | Protection | Boc protection |
| `reduction` | Reduction | NaBH₄ reduction |
| `reductive-amination` | Reductive amination | reductive amination |

The vocabulary is broad enough that change 3's samples (at least five
types) and the co-worker's first procedures fit without an edit. It is
narrow enough that the taxonomy pages stay meaningful.

*Rejected alternatives:*

- *A flat list `types = ["esterification", ...]`.* It has no display
  label, so the theme would have to title-case slugs (giving
  "Cross-Coupling" and "Aldol-Condensation").
- *An array of tables `[[type]] slug = ... label = ...`.* Lookup in Hugo
  templates would need a loop instead of `index`.
- *Mechanism-level types (`sn2`, `e2`).* Too fine-grained for a category
  taxonomy.

### D8. Templates and their interface to `build.fish new`

Both templates use the placeholder ID `OSDB-0000` and the placeholder slug
`osdb-0000`. `OSDB-0000` is outside the valid ID range
(`OSDB-0001`–`OSDB-9999`), so a template copied by hand without
substitution fails validation instead of publishing.

`build.fish new` (change 2) does the following:

- replaces every occurrence of `OSDB-0000` with the new ID, and of
  `osdb-0000` with its lowercase form;
- in Org, replaces the values of the `#+CREATED:` and `#+LAST_MODIFIED:`
  lines with the current Europe/Berlin time in the required format, and the
  value of `#+AI_MODEL:` with `none` unless told otherwise;
- in Markdown, replaces the values of the `date =` and `lastmod =` lines
  with the current Europe/Berlin offset datetime.

After those substitutions, each template must validate with no errors and
no warnings. Every other placeholder value is therefore type-correct, and
all eight sections are present.

The Org template is written by an AI, so its `#+AI_MODEL:` carries the
writing model's exact identifier (house rule). `new` rewrites it to `none`,
because the person filling the stub is the author of the procedure.

Org template content:

- It sets the schema fields through `#+TITLE`, `#+HUGO_SLUG`, `#+HUGO_TAGS`
  and repeated `#+HUGO_CUSTOM_FRONT_MATTER:` lines. `product` is written
  as an alist map, which ox-hugo emits as a `[product]` table.
- It does not set `#+DATE`, `#+HUGO_LASTMOD`, `#+HUGO_AUTO_SET_LASTMOD`,
  `#+HUGO_DRAFT`, `#+HUGO_BASE_DIR` or `#+HUGO_SECTION`. `date` and
  `lastmod` come from the `#+CREATED`/`#+LAST_MODIFIED` mapping, and the
  base dir and section are export configuration that `export.el` supplies
  through `org-hugo-base-dir` and `org-hugo-section`.

The brief speaks of "`+` continuation lines". The ox-hugo docs reserve the
`+` suffix for property drawers (`:EXPORT_HUGO_CUSTOM_FRONT_MATTER+:`). For
the file-level keyword, the documented form is to repeat
`#+hugo_custom_front_matter:`, and the source declares the option with
`space` concatenation. The template uses repeated keywords.

The Markdown template explains each field in plain-language TOML comments,
and shows the optional fields commented out, ready to uncomment.
`structure_image` and `precursors` stay commented out, because active
placeholders would fail the existence checks.

*Rejected alternatives:*

- *Templates with `{{id}}`-style tokens.* The template itself would not be
  parseable TOML, so it could not be validated in its own test.
- *`#+AI_MODEL: none` in the committed Org template.* That breaks the house
  rule that AI-written Org files name their model.

### D9. Identifier, file-name and list rules

- **`id`** matches `^OSDB-\d{4}$`, with the number between 1 and 9999.
- **File names** match `^OSDB-\d{4}-[a-z0-9]+(-[a-z0-9]+)*\.(md|org)$`, and
  the `OSDB-NNNN` prefix must equal `id`. This applies to content files
  and to Org sources.
- **`tags`** must be non-empty, and each tag must match the slug pattern.
  ox-hugo omits `tags` entirely when `#+HUGO_TAGS` is empty, so "present
  but possibly empty" would treat the two formats differently.
- **`authors`** and **`hazards`** must be non-empty. **`checked_by`** and
  **`references`** may be empty lists.
- **`scale`** matches `^\d+(\.\d+)?\s+\S+$`: a number, whitespace, and a
  unit token. The unit set is not enumerated.
- **`product.cas`**, when present, matches `^\d{2,7}-\d{2}-\d$`, and its
  check digit must verify. For example, `64-17-5` is valid and `64-17-4`
  fails.
- **Numbers** (`yield_percent`, `product.mw`) are TOML integers or floats,
  never booleans, and must be finite.
- **`ai_model = "none"`** in front matter is an error ("omit ai_model when
  no AI was involved"). The mapping omits the key in that case, so the
  value can only come from a hand-written mistake.

### D10. Dependent checks are suppressed so one fault gives one error

Each invalid fixture must fail for exactly one reason, and real authors
benefit from the same property. Checks that depend on a value are skipped
when that value is missing or malformed:

- If the front matter is unparseable, only the `front_matter` error is
  reported. The file contributes no ID, and its body is not checked.
- If `id` is missing or malformed, the file-name/ID agreement, the `slug`
  equality and the duplicate-ID check are skipped.
- If `date` or `lastmod` is not an offset datetime, the `lastmod >= date`
  comparison, the offset warning for that field, and the Org cross-check
  for that field are skipped.
- If `product` is not a table, its sub-field checks are skipped.
- If a `precursors` entry is not an ID, its existence check is skipped.
- If `structure_image` has the wrong suffix or lies outside `structures/`,
  its existence check is skipped.
- If an Org timestamp is malformed, it is excluded from the ordering check
  and the cross-check.

### D11. File discovery

Only the top-level entries of each root are read; roots are not searched
recursively.

- **Every subdirectory is an error**, whatever its name: a `file_name`
  error on the directory's path containing `subdirectories are not
  supported`. Its contents are not read. Hugo publishes nested content: a
  probe build put `content/procedures/sub/X.md` at a live URL (see
  Verification). An ignored subdirectory would therefore be a route by
  which unvalidated pages reach the site.
- Non-directory entries whose names begin with `.` are skipped silently
  (Emacs lock files, `.gitkeep`), and so is the file `_index.md`, Hugo's
  section page. No other `_`-prefixed name is special: `_draft.md` is a
  procedure file and fails the file-name rule, because Hugo would publish
  it.
- In a content root, any other file that is not `*.md` gets a `file_name`
  warning containing `not a procedure file; ignored`. In an Org root, the
  same applies to any file that is not `*.org`. Hugo does not render such
  files as pages, so a warning keeps them visible without failing the
  build.

*Rejected alternatives:*

- *Recurse into subdirectories and validate their files.* That would
  sanction a nested layout. Under Hugo, a nested layout changes section
  membership, and with it the URL scheme.
- *Warn on subdirectories.* A warning does not stop the build, so the
  nested pages would publish unvalidated.
- Files are read as UTF-8, and a BOM is tolerated. A decode failure is a
  `front_matter` error.
- Front matter begins with a first line `+++` and ends at the next line
  `+++`. Trailing whitespace and CR on the delimiter lines are tolerated.
  Everything after the closing delimiter is the body.

### D12. Python and test conventions

- `tools/validate.py` is a single executable file. It has the shebang
  `#!/usr/bin/env python3` and a PEP 723 block declaring
  `requires-python = ">=3.14"` and `dependencies = []`.
- It uses the standard library only (`argparse`, `tomllib`, `zoneinfo`,
  `datetime`, `re`, `pathlib`).
- Parameters and return types are annotated on every callable. Lines wrap
  at 79 columns.
- Docstrings state the contract only.
- It exposes `main(argv: Sequence[str] | None = None) -> int`, so tests may
  call it in-process, and runs `sys.exit(main())` under `__main__`.
- Pure checking logic, from parsed data to a list of problems, is kept
  apart from file I/O and printing, so most rules can be tested without
  touching the filesystem.
- Tests are `unittest.TestCase` classes in `tests/test_*.py`, run with
  `python3 -m pytest tests`, and named for the behaviour they pin.
- The contract tests drive the script as a subprocess
  (`[sys.executable, "<repo>/tools/validate.py", ...]`) with `cwd` set to a
  temporary directory. That proves both the output format and cwd
  independence. Tests locate the repo from their own `__file__`.
- Paths are always handled as `Path` objects or list arguments, never
  interpolated into shell strings, because paths may contain spaces.
- Fixtures use fictitious names ("A. Example") and no machine
  identifiers.

### D13. Fixture layout

Fixtures come in two kinds: committed files for a representative case of
each category, and in-test variants of one committed baseline for every
other field variation. Every behaviour scenario is kept either way; the
split changes only how a scenario is realised. Committed files are what
brief acceptance criterion 6 needs, since `build.fish validate` must have
real files to reject. Variants keep the fixture tree from becoming 30
near-copies of one procedure that drift apart as the schema evolves.

```
tests/fixtures/
  reaction_types.toml         fixture vocabulary (independent of site/)
  bad-vocabulary.toml         entry without label (exit-2 test)
  static/structures/osdb-0001.svg
  baseline/OSDB-0100-baseline.md
                              required fields only, all eight sections;
                              the source of every variant
  valid/md/                   OSDB-0001 (all optional fields, winter
                              offset), OSDB-0002 (cross-root precursor,
                              case-variant heading, extra section)
  valid/org/                  OSDB-0003, OSDB-0004-ambiguous-hour
  valid/export/               ox-hugo-shaped exports of valid/org
  invalid/<case>/             one content root per case, one file each
  warn/<case>/                one content root per warning case
  org-invalid/<case>/org/     one Org file per case
  org-invalid/<case>/export/  its export, for cross-check cases only
```

**Committed cases (on disk).** One or more per category:

| Category | Case directory |
|---|---|
| front-matter parse | `invalid/invalid-toml` |
| ID / file name / slug | `invalid/bad-id-format`, `invalid/file-name-id-mismatch`, `invalid/slug-mismatch` |
| required field missing | `invalid/missing-title` |
| enum / vocabulary | `invalid/unknown-reaction-type` |
| numeric range | `invalid/yield-out-of-range` |
| date typing / order | `invalid/date-as-string` |
| precursor existence | `invalid/missing-precursor` |
| `structure_image` existence | `invalid/missing-structure-image` |
| rejected key | `invalid/author-key` |
| duplicate ID across roots | `invalid/duplicate-id` (roots `a/`, `b/`) |
| subdirectory | `invalid/subdirectory`, `org-invalid/subdirectory` |
| stray file | `warn/stray-file` (valid file plus `notes.txt`) |
| warnings | `warn/missing-section`, `warn/offset` |
| Org lint | `org-invalid/` `missing-created`, `duplicate-created`, `active-timestamp`, `missing-seconds`, `invalid-date`, `wrong-weekday`, `nonexistent-local-time`, `last-modified-before-created`, `bad-ai-model`, `bad-org-file-name` |
| Org cross-check | `org-invalid/` `export-date-mismatch`, `export-offset-mismatch`, `export-ai-model-mismatch`, `missing-export` |

That is 13 `invalid/` case directories and 3 `warn/` cases, plus 15 Org
cases.

**Variant cases (in-test).** A variant run writes the baseline text, with
one stated change, into a fresh temporary content root under a stated
file name, and runs the validator on it. The changes are a line replaced,
removed or inserted in the front matter, the delimiters swapped, or a body
section moved or fenced. The cases are:

- `id-zero`, `bad-file-name`, `missing-slug`;
- `yield-not-number`, `empty-hazards`, `empty-tags`, `bad-status`,
  `two-reaction-types`, `bad-tag`, `bad-scale`, `product-missing-mw`,
  `bad-cas-check-digit`;
- `date-without-offset`, `lastmod-before-date`, `self-precursor`;
- `structure-image-wrong-type`, `structure-image-outside-structures`;
- `checked-by-not-list`, `ai-model-none`, `draft-true`, `url-key`,
  `unknown-key`, `no-front-matter`;
- `section-order`, `heading-in-code`.

One further in-test case mutates a copy of the valid `OSDB-0004` export:
"Exported instants decide the ordering". Variants keep the baseline's
`OSDB-0100` ID, except where the scenario changes the ID or the file name.
The baseline is laid out one key per line, with `[product]` as the last
table, so that each change is a plain text edit. The test writer owns the
helper that applies these edits.

Each invalid case, committed or variant, must produce exactly one `error`
line and no warnings, except where a scenario says otherwise. That is
what "rejected for the right reason" means here. Committed fixture IDs are
unique across the fixture tree, so that a test combining roots cannot trip
the duplicate check by accident. The exceptions are the duplicate-ID case
and an Org source paired with its own export. Org sources contribute no
IDs, so the pairing cannot collide.

## Verification of upstream facts

Verified against upstream on 2026-10-19: the ox-hugo docs at
ox-hugo.scripter.co, and `ox-hugo.el` (Version 0.12.1) and `tomelr.el` on
their GitHub `main` branches.

- File-based export keyword mapping: `#+title` → `title`, `#+date` →
  `date`, `#+hugo_lastmod` → `lastmod`, `#+hugo_tags: a b` →
  `tags = ["a", "b"]`, `#+hugo_draft` → `draft`.
- `HUGO_SLUG` is an export option (`:hugo-slug`) emitted as `slug`.
- `#+hugo_custom_front_matter:` may be repeated. The option is declared
  with `space` concatenation. The `+` suffix is documented only for
  property-drawer use.
- Custom front matter supports lists (`'(a "b c")`) and single-level maps
  (`'((name . "x") (mw . 176.12))`), which become TOML tables. Maps of
  maps are not supported.
- tomelr coerces number-like strings. The docs show `"0.48"` exported as
  `0.48`. None of the schema's string fields is number-like when filled
  sensibly, but a `scale` of `"25"` would become an integer and be
  reported as a type error.
- Dates: `org-hugo-date-format` defaults to `"%Y-%m-%dT%T%z"`, and
  `org-hugo--org-date-time-to-rfc3339` inserts the colon into the offset.
  tomelr writes strings matching its RFC 3339 regexp unquoted, so they
  become TOML datetimes.
- `draft` is always emitted (as `false` absent a TODO state or
  `#+hugo_draft`).
- `author` is exported by default, from `user-full-name`, as a list. It is
  disabled with `#+options: author:nil` or `org-export-with-author` nil.
- Headings: level N becomes `#` × (N + `HUGO_LEVEL_OFFSET`, default 1) in
  ATX style. A ` {#anchor}` suffix is appended by default
  (`org-hugo-headline-anchor`, default `t`). Section numbers default off
  (`org-hugo-export-with-section-numbers` nil).
- The output file name comes from `org-export-output-file-name ".md"`.
  Without `EXPORT_FILE_NAME`, it is the source file's base name. The
  output directory is `<HUGO_BASE_DIR>/content/<HUGO_SECTION>/`.
- Hugo permalink tokens (current docs) include `:slug`, which falls back to
  the title, and `:slugorcontentbasename`. There is no token for an
  arbitrary front-matter parameter.

Verified on this machine:

- **Hugo `:slug` permalink.** A throwaway site was built with Hugo 0.162.1
  (`v0.162.1+extended`, Fedora build) in the session scratchpad, outside
  the repo, with `[permalinks.page] procedures = "/procedures/:slug/"`.
  - `content/procedures/OSDB-0001-ethyl-acetate.md` with
    `slug = "osdb-0001"` was published at `/procedures/osdb-0001/`.
  - A page with no `slug` fell back to its title, at
    `/procedures/some-product-name/`. This is why `slug` is required.
  - `content/procedures/sub/OSDB-0003-nested.md` was published at
    `/procedures/osdb-0003/`. This is why a subdirectory is an error (D11).

  Whether change 2 writes the permalink as `[permalinks.page]` or the older
  `[permalinks]` form is its own decision.
- **Seconds in Org timestamps.** Org 9.7.11's parser reads
  `[2026-10-19 Mon 17:42:05]` with seconds = 0. This was verified by the
  reviewer on this machine, not re-run here. ox-hugo's `#+date` path
  (`org-parse-time-string`) would therefore drop the seconds. Change 2's
  `export.el` must parse `#+CREATED` and `#+LAST_MODIFIED` itself, keeping
  the seconds, and emit `date`/`lastmod` with the Europe/Berlin offset. The
  cross-check compares to the second and will fail an export that drops
  them.

**Unverified until change 2 installs ox-hugo (from MELPA):**

- That the MELPA build change 2 pins behaves as `main` does above.
- The exact TOML ox-hugo emits for the template's map and list custom
  front matter.

None of these affects this change's tests, which run on hand-made fixtures
shaped like the verified output.

## Risks / Trade-offs

- [The fixtures in `valid/export/` are shaped by reading ox-hugo's source,
  not by running it, and may differ from real output in details such as
  key order or table placement.] → The validator is order-insensitive and
  checks only parsed values. Change 2 adds the seed samples, runs the real
  export through the validator, and corrects the fixtures if real output
  disagrees. That correction restores this spec, so it needs no proposal.
- [The owner's Emacs may insert localised weekday names (`Mo`) when
  `system-time-locale` is not `C`.] → The rule fixes English abbreviations,
  and the lint error names the expected abbreviation. `build.fish new`
  formats under `LC_TIME=C` (change 2), and `docs/AUTHORING-ORG.org` will
  say how to configure Emacs.
- [`zoneinfo` needs the system tz database.] → Fedora ships `tzdata`. If it
  is missing, the validator exits 2 with a message rather than guessing an
  offset.
- [A required `slug` is one more line for the co-worker to keep in sync.]
  → `new` writes it, and the error message gives the exact value.
- [Warnings for unknown keys may become noise if ox-hugo starts emitting a
  new key.] → Adding it to the tolerated set restores this spec's intent
  and is a one-line change, made through a proposal since it changes a
  requirement.
- [The ambiguous autumn fall-back hour cannot be told apart in an Org
  timestamp, which has no offset.] → The lint accepts any ordering that
  some choice of offsets makes valid (D2). The cross-check accepts either
  Europe/Berlin offset there, because it compares wall-clock time plus "the
  offset Berlin had at that instant". The exported `lastmod >= date`, with
  explicit offsets, is the authoritative ordering check.
- [Exports can go stale, or outlive their deleted Org source, without the
  validator noticing (D2).] → Change 2 owns freshness and orphan removal:
  the export writes into a directory it empties first, or an equivalent
  mechanism of its choosing.
- [Variant fixtures exist only while the tests run, so `build.fish
  validate` cannot be pointed at them.] → The committed cases cover every
  category, and they are what acceptance criterion 6 exercises.

## Open Questions

- Should `status = "checked"` require a non-empty `checked_by`? Not decided
  here; this change does not check it. A later change can add it as a
  warning.
- Should the Reagents section's table header be checked? Left out (see
  Non-Goals). It is a candidate warning once real procedures show whether
  authors drift.
