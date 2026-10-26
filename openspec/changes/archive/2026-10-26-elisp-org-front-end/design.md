## Context

Today the export reads Org in two languages. `pipeline.plan_export`
discovers `org/procedures/*.org`, runs `validate.lint_org` on each, picks
`date` and `lastmod` with `export_instants`, and writes
`build/export-plan.json`; `tools/export.el` reads that plan and runs
ox-hugo. `orgsyndb validate` then passes `--org-root org/procedures` to
the validator, which repeats the discovery, checks the Org file names,
lints the keywords again, and cross-checks `date`, `lastmod` and
`ai_model` against the export.

After this change, Emacs is the only program that reads an Org source,
and Python reads only Markdown. Python still looks at the *names* in
`org/procedures/`.

## The boundary

```
orgsyndb export
  recover build/export/                        (Python)
  org/procedures exists but is no directory?   (Python) -> fail, export kept
  has_org_sources("org/procedures")?           (Python, names only)
    no  -> empty staging, install              (Python)
    yes -> emacs -Q --batch -l tools/export.el org/procedures build/.export-staging
             check Europe/Berlin is available
             examine ORG_ROOT: discovery, file names, keywords, timestamps,
                               forbidden routes to date/lastmod/ai_model
             print problem lines on stdout
             any error -> exit 1 (nothing installed, loaded or written)
             bootstrap + pin check, load ox-hugo
             export each source with the date/lastmod/ai_model it chose
           check_staging(build, org_stems("org/procedures"))   (Python)
           replace_export(build)                                (Python)
```

Problem lines go to Emacs's stdout and nothing else does. Org, ox-hugo
and export.el's own messages go to stderr, which is where `message`
writes in batch mode. `orgsyndb` captures both streams, writes both to
`build/export.log` (stdout first), and copies Emacs's stdout to its own
stdout whether Emacs succeeded or not. That way warnings reach the user
on a successful run, and `orgsyndb validate` shows the Org lines and
the validator's lines on the same stream in the same format.

When Emacs exits non-zero, `orgsyndb` chooses its message by looking at
Emacs's stdout. If any line there has severity `error`, it says "the
Org sources have errors; build/export/ is unchanged" and does not dump
the log, because the lines have already been printed. Otherwise it
prints the log to stderr and says "export failed; Emacs output is in
build/export.log", as it does today.

A regular file at `org/procedures` is rejected by Python before
staging. `has_org_sources` is false for it, because it lists no
entries, so without this check the "no Org sources" branch would
install an empty `build/export/`. Today `plan_export` raises on it and
the previous export survives; the new check keeps that outcome and
names the cause. It needs no Emacs, and it reads no Org.

Rejected alternatives:

- *A distinct exit status for Org problems.* Exit 1 is already the
  status of every export.el failure (old Emacs, clone, pin mismatch,
  export error), and the specs fix it. Reading the severity from the
  report needs no new convention.
- *Emacs printing problems to stderr, as `write_export_plan` does
  today.* They would be mixed with ox-hugo's messages in the log, and
  `orgsyndb` would have to pick them out of it.

## Where the Org file-name rule lives

All problems with the contents of `org/procedures/` come from Emacs:

- the discovery problems: a subdirectory is an error, and a stray file
  is a warning;
- the `OSDB-NNNN-slug[.lang].org` rule and the unknown language code;
- the read errors;
- the keyword and timestamp checks;
- the routes by which a source could set the exported values itself
  (see "Authoritative exported values").

The messages are the validator's, word for word, apart from the
deliberate differences listed under "Keeping the messages identical".

Python looks only at names, through `validate.discover(org_root,
".org")`, the function it already uses for Markdown roots:

- `pipeline.has_org_sources(org_root)` is true when `discover` returns
  at least one entry, with or without a problem. Such an entry is one
  that Emacs will either export or report.
- `pipeline.org_stems(org_root)` returns, sorted, the stems of the
  entries that have no problem. `check_staging(build, stems)` expects
  exactly `<stem>.md` for each. Emacs exits 0 only when every such
  entry passed its checks and was exported, so a mismatch means
  export.el is broken, not a source.

Consequence: an `org/procedures/` that holds only a subdirectory or a
stray file now needs Emacs. Today the export skips such entries and the
validator reports them. With Emacs as the only reporter, the
alternative would be to drop those entries silently whenever Emacs is
not run. Starting Emacs keeps a subdirectory of Org files from being
skipped without a word. The cost falls on a Markdown-only collection
that keeps stray files in `org/procedures/`, which is unusual.

Rejected alternatives:

- *Keeping the file-name rule and the discovery problems in the
  validator, run on `org/procedures/`.* Org problems would then come
  from two programs, at two steps, in two passes. Worse, a misnamed
  `.org` file would still be exported first and then rejected.
- *`has_org_sources` true only when there is an `.org` file.* A
  directory holding only a subdirectory of Org files would then be
  skipped silently, a regression from today.

## File layout

- `tools/osdb-org.el` (new) is a library that provides `osdb-org`. It
  holds every function that reads Org text or Org file names, plus the
  timestamp arithmetic. Loading it defines functions and constants and
  does nothing else. It does not require Org, ox-hugo or tomelr. It
  must not require Org because export.el has to set
  `temporary-file-directory` before Org loads: org-persist creates its
  directory when Org loads. The library requires only `cl-lib`,
  `subr-x` and `time-date`, which ship with Emacs.
- `tools/export.el` keeps the isolation, the version check, the
  argument check, the bootstrap and the export. After the isolation
  settings it loads the library with
  `(require 'osdb-org (expand-file-name "osdb-org" <its directory>))`,
  so that `load-path` does not change. It then checks the zone,
  examines ORG_ROOT, reports, and exports.
- `tests/el/osdb-org-tests.el` (new) loads the library the same way,
  from `../../tools/` relative to itself. It finds fixtures under
  `../fixtures/`, so it works from any working directory.

Rejected alternative: *a guard in export.el*, such as a variable that
suppresses `osdb-main` when set. export.el changes global state when it
loads: it checks the arguments, `kill-emacs`es on a bad count, creates
`tmp/` beside STAGING_DIR, sets `TMPDIR` and clears `GIT_*`. A test
would have to fake all of that and still risk `kill-emacs`. A separate
file makes "testable without the export running" true by construction.

No word under `tools/` may be `node` or `npm` (site-search "Node stays
optional"). This applies to the library too.

## Library interface

Problems are lists of three strings, `(FIELD SEVERITY MESSAGE)`, with
SEVERITY `"error"` or `"warning"`. This matches `validate.Problem`.
Instants are integers, seconds since the epoch. The default ZONE is
the constant `osdb-org-zone`, `"Europe/Berlin"`. Functions take it as
an optional argument so that the zone check can be tested.

| Function | Returns |
|---|---|
| `(osdb-org-zone-available-p &optional zone)` | non-nil when ZONE's offsets at 2026-01-15T12:00:00Z and 2026-07-15T12:00:00Z are 3600 and 7200 |
| `(osdb-org-keywords text)` | alist `(NAME . VALUES)`, NAME upper-cased, VALUES trimmed and in file order |
| `(osdb-org-local-instants year month day hour minute second &optional zone)` | the instants that wall time names, earliest first: none, one or two |
| `(osdb-org-parse-timestamp field value &optional zone)` | a non-empty list of instants, or one problem |
| `(osdb-org-check-file-name name)` | list of problems |
| `(osdb-org-lint text &optional zone)` | `(PROBLEMS CREATED LAST-MODIFIED AI-MODEL)`, where PROBLEMS include the forbidden routes and each of the last three is nil when it is missing or invalid |
| `(osdb-org-export-instants created last-modified)` | `(DATE . LASTMOD)` |
| `(osdb-org-rfc3339 instant &optional zone)` | `YYYY-MM-DDThh:mm:ss+HH:MM` |
| `(osdb-org-examine root &optional zone)` | `(SOURCES . PROBLEMS)` |
| `(osdb-org-problem-line path problem)` | the report line |

`osdb-org-examine` returns:

- SOURCES: one plist `(:path :stem :date :lastmod :ai-model)` per Org
  source that has no problem, in name order. `:path` is absolute,
  `:date` and `:lastmod` are RFC 3339 strings, and `:ai-model` is nil
  for `none`.
- PROBLEMS: `(PATH . PROBLEM)` pairs in report order. PATH is ROOT as
  given, joined with the entry name by `file-name-concat`, so a
  trailing slash on ROOT does not double.

A plist and a cons pair serve here instead of a `cl-defstruct`, which
would give the tests one more definition to keep in step.

## Timestamp algorithm

The Python code relied on `zoneinfo` and `fold`. Emacs 29.1 and later
accept a TZ rule string such as `"Europe/Berlin"` as the ZONE argument
of `decode-time` and `format-time-string`. The algorithm needs only
those two functions plus `encode-time` in UTC:

1. **Form.** Match the value against
   `\`\([[<]\)\([0-9]\{4\}\)-\([0-9]\{2\}\)-\([0-9]\{2\}\) \([^][:space:]>]+\) \([0-9]\{2\}\):\([0-9]\{2\}\):\([0-9]\{2\}\)\([]>]\)\'`
   with `case-fold-search` bound to nil. If the value does not match,
   or its brackets do not pair, the error is `"<value>" must have the
   form [YYYY-MM-DD Day hh:mm:ss]`. An opening `<` gives
   `"<value>" must be an inactive timestamp in square brackets,
   [YYYY-MM-DD Day hh:mm:ss]`.
2. **Date.** The date is valid when the year is 1 to 9999, the month 1
   to 12, and the day 1 to `(date-days-in-month year month)`.
   Otherwise the error is `"<value>" is not a valid date`.
3. **Time.** The time is valid when the hour is below 24 and the minute
   and second are below 60. Otherwise the error is `"<value>" is not a
   valid time`.
4. **Weekday.** The weekday is looked up in the constant vector
   `["Sun" "Mon" … "Sat"]`, indexed by the day of week of the wall
   date in UTC. `format-time-string "%a"` follows `system-time-locale`
   and is not used. A mismatch gives `weekday "<given>" does not
   match <YYYY-MM-DD> (<expected>)`.
5. **Instants.** Let N be the wall time encoded as if it were UTC,
   `(time-convert (encode-time (list s m h d mo y nil nil 0))
   'integer)`. The
   candidate offsets are the zone's UTC offsets at the instants
   N − 86400 and N + 86400; no Berlin transitions fall within two days
   of each other. For each distinct candidate O, the instant N − O
   counts when `decode-time` of it in the zone gives offset O and the
   same six wall-clock fields. The counted instants, sorted, are the
   result. An empty result gives `"<value>" does not exist in
   Europe/Berlin (skipped by the clock change)`.
6. **Ordering.** When both timestamps are valid and the earliest
   instant of `#+CREATED` is later than the latest instant of
   `#+LAST_MODIFIED`, the error on `#+LAST_MODIFIED` is `is earlier
   than #+CREATED`.
7. **Choice.** `date` is the earliest instant of `#+CREATED`. `lastmod`
   is the earliest instant of `#+LAST_MODIFIED` that is not before
   `date`, or else the latest one.
8. **Format.** `format-time-string "%Y-%m-%dT%H:%M:%S%:z" instant zone`.

Rejected alternative: *`encode-time` with an explicit DST flag* (t and
nil) to obtain the two instants of the fold hour. What a contradictory
flag does, such as DST in January, is left to the C library's
`mktime`, and Emacs 29 changed `encode-time`'s calling convention. The
round trip through `decode-time` depends on neither.

### Zone availability

An unknown TZ string does not raise an error. The C library treats it
as UTC, and `decode-time` returns offset 0 for `"Nowhere/Nothing"` (as
observed on Emacs 30.2). Without a check, a container lacking tzdata
would export every timestamp with `+00:00`, and every export would then
fail the validator's offset check with a misleading message. So
export.el first calls `osdb-org-zone-available-p`, before it examines
ORG_ROOT. When that returns nil, it fails with `export.el: error: time
zone Europe/Berlin is not available; install the tz database
(tzdata)`, the validator's message. What the two reference dates
detect is a missing tz database, or a zone name it does not know, since
both silently become UTC. They do not prove that the rules are
Berlin's: any zone at +01:00 in January and +02:00 in July passes,
`Europe/Paris` for one. The check guards against a missing database,
not a corrupt one.

The zone is always passed explicitly, never taken from `TZ`. `orgsyndb`
sets `TZ=Europe/Berlin` for its children, but the ERT suite runs under
whatever `TZ` pytest inherits.

## Authoritative exported values

The cross-check caught one real failure that the old lint did not. A
source with `#+AI_MODEL: none` and `#+HUGO_CUSTOM_FRONT_MATTER: :ai_model
"example-model-1"` passed the lint, and the pinned ox-hugo exported
`ai_model = "example-model-1"`. With the cross-check gone, the values
Emacs chooses must be the only ones that can reach the export. Hence
procedure-schema "Exported values come only from the file-level
keywords". Reading the pinned ox-hugo (`b7dc44d`, `ox-hugo.el`) gives
every input that feeds `date`, `lastmod`, `ai_model` or the output
path in a whole-file export:

- **`date`**, in `org-hugo--get-date`, by precedence:
  1. `:logbook-date`, from a LOGBOOK drawer (`org-hugo--parse-logbook-entry`);
  2. `CLOSED` of the heading at point;
  3. `#+DATE` (`:date` in the options alist);
  4. `org-export-get-date`.
- **`lastmod`**: `:logbook-lastmod`, then `#+HUGO_LASTMOD`, then
  `#+HUGO_AUTO_SET_LASTMOD` (the current time).
- **`ai_model`**: only the custom front matter
  (`#+HUGO_CUSTOM_FRONT_MATTER`, parsed by
  `org-babel-parse-header-arguments`), whose entries are appended to
  ox-hugo's own.
- **Raw front matter**: a TOML or YAML source block with the header
  argument `:front_matter_extra` (`org-hugo-src-block` stores it as
  `:fm-extra`, and the body filter appends it verbatim to the front
  matter), so it can set any key. Header arguments reach a block from
  its `#+begin_src` line, a `#+header:` line, a `#+PROPERTY:
  header-args…` line or a `:header-args…:` node property.
- **Any of the three**, renamed or removed:
  `#+HUGO_FRONT_MATTER_KEY_REPLACE`.
- **Output path**: `#+EXPORT_FILE_NAME`, `#+HUGO_BASE_DIR`,
  `#+HUGO_BASE_CONTENT_FOLDER`, `#+HUGO_SECTION` and `#+HUGO_BUNDLE`.
  In-buffer keywords override the `org-hugo-*` variables that
  export.el binds. `EXPORT_HUGO_SECTION` and similar are read with
  `org-entry-get nil … :inherit`, which a file-level `#+PROPERTY`
  reaches.
- **Indirect routes**: `#+SETUPFILE` and `#+INCLUDE`, which bring in
  any of the keywords above before the export reads its options. The
  `EXPORT_*` node properties are also ox-hugo's subtree-export
  equivalents of all of these keywords.
- **Logbook parsing** happens only for the drawer that
  `(org-log-into-drawer)` names, which `LOG_INTO_DRAWER`, as a file or
  node property, can switch on and rename.

The checks reject each of these inputs, with one exception: `CLOSED`.
Planning lines are ordinary Org, and the `CLOSED` route applies only
when point is on a heading. export.el exports with point at the
beginning of the buffer, on its own inserted `#+DATE` line, so `CLOSED`
is never read. `#+HUGO_DATE_FORMAT` is left alone. A date that already
matches ox-hugo's RFC 3339 pattern, as export.el's does, is used
verbatim; the format applies only to the logbook and auto-lastmod
routes, which are rejected.

Custom front-matter keys are compared case-insensitively because Hugo
reads front-matter keys case-insensitively, so `:Date` would set the
page date as surely as `:date`. Keys are split as
`org-babel-parse-header-arguments` splits them: a `:` after whitespace,
outside quotes and parentheses. The library cannot call it, since that
would load Org, so it ports the splitting. No shipped Org file uses any
of the rejected inputs (checked by grep over `examples/`, `templates/`
and `tests/fixtures/`).

Rejected alternatives:

- *Neutralising the inputs in export.el*, by binding the variables,
  advising `org-hugo--get-date` or stripping lines from the in-memory
  copy. In-buffer keywords beat variables. Advice would depend on
  ox-hugo internals at a pinned commit, and stripping would export
  something other than the source the author wrote. Rejecting the
  source tells the author, and keeps the export a function of the file.
- *Keeping a post-export check of `date`, `lastmod` and `ai_model`* in
  Emacs, against the values it chose. It would catch the symptom after
  ox-hugo has run, and say nothing about the output path or about which
  line caused it. The pre-export check names the line.

## Keeping the messages identical

The keyword scanner is a port of `validate.org_keywords`, line for
line, rather than a call to `org-collect-keywords` or org-element. The
existing rules define a keyword line by a regular expression, skip
`#+begin_`…`#+end_` blocks, and count repeats. Org's parser differs on
keywords inside drawers and on affiliated keywords, and its behaviour
may differ between Org 9.6 and 9.7. A line scanner behaves the same on
both, and the library then needs no Org at all.

The messages and check order of the former Python lint carry over
unchanged. Three deliberate differences narrow what is accepted, and
the specs state them as rules: ASCII digits, trimming of spaces, tabs
and CR only, and lines split at LF only. Each has a scenario
(procedure-schema "ASCII digits and ASCII trimming", org-export
"Byte-order mark and CRLF line ends"). Everything else is meant to be
identical, and the one-off comparison in task 6.5 checks it against
the old validator's output.

Parity rules for the port:

- **Case.** Every `string-match` binds `case-fold-search` to nil. Only
  keyword names and the block markers are matched case-insensitively,
  explicitly: `[A-Za-z_]+` is upper-cased, and `#+begin_` and `#+end_`
  are matched in either case.
- **Lines** (deliberate difference). Lines split at LF, with a
  trailing CR removed. Values are trimmed of spaces, tabs and CR.
  Python's `splitlines` also split at VT, FF, FS, GS, RS, NEL, LS and
  PS, and `strip` removed every Unicode space, such as U+00A0. A value
  padded with a no-break space now gets the form error.
- **Digits** (deliberate difference). Digits are ASCII `[0-9]`.
  Python's `\d` also matched other Unicode decimal digits. A timestamp
  written with them now gets the form error instead of passing.
- **Reading.** Sources are read as UTF-8 with any byte-order mark
  dropped. If the decoded text holds raw bytes, which is what invalid
  UTF-8 decodes to, the source gets the `front_matter` error `file is
  not valid UTF-8`. A `file-error` gives `cannot read file: <reason>`.
  `<reason>` is the operating system's message, which is the second
  element of the error data (for example `Permission denied`), and
  which Python printed as `strerror`. It is not
  `error-message-string`, which would add `Opening input file` and the
  path. A read problem stops every later check, the file name check
  included, as it did in the validator.
- **Listing.** `os.listdir` never returns `.` and `..`; `directory-files`
  does unless given `directory-files-no-dot-files-regexp`. Without that
  regexp, both entries would be reported as subdirectories, since the
  "non-directory entry beginning with `.`" rule does not skip a
  directory. A dangling symlink is not a directory (`file-directory-p`
  follows links, as `os.path.isdir` does).
- **Check order** within one source: read, file name, `#+CREATED`,
  `#+LAST_MODIFIED`, `#+AI_MODEL`, ordering, then the forbidden routes.
  This is the validator's order, with the new checks appended. Within
  one timestamp, the first failing check of form, active, date, time,
  weekday, existence is the only one reported, and the ordering check
  needs both timestamps present once and valid. procedure-schema
  "Dependent checks of the keywords" enumerates the combinations from
  `lint_org` and `parse_org_timestamp`. Lines are sorted by path with a stable sort on `string<`,
  which matches Python's sort by code point.
- **Coverage.** The scenarios carried over from the Python tests
  assert the substrings those tests asserted. The parity scenarios
  compare whole lines: invalid time, invalid UTF-8, an unreadable file,
  the dependent-check combinations, the file name together with a
  keyword error, the deliberate differences, and the forbidden routes.

## Test layout

`tests/el/osdb-org-tests.el` replaces `tests/test_org_sources.py` and
`tests/test_export_plan.py` scenario for scenario. Every scenario that
needs no ox-hugo becomes an ERT test that keeps the scenario name in
its docstring. Tests that need Org fixtures call `osdb-org-examine` on
the committed fixture directories, `tests/fixtures/org-invalid/<case>/org/`
and `tests/fixtures/valid/org/`, or on a temporary directory built by
the test.

| Old test | New home |
|---|---|
| `OrgKeywordLintTests` (11 scenarios) | ERT, on the same fixtures |
| `OrgDependentCheckTests` | ERT ("Invalid date does not cascade") |
| `ExportPlanTests` | ERT, on `osdb-org-examine` |
| `ExportedTimestampTests` | ERT, on `osdb-org-examine` with edited copies |
| `test_pipeline_logic` fall-back function test | ERT, on `osdb-org-export-instants` |
| `OrgTemplateTests.test_substituted_org_template_passes_the_lint` | ERT |
| `test_validate_cli` "Subdirectory in an Org root" | ERT |
| `OrgExportMappingTests`: matching export, ambiguous hour | integration: exported dates equal `valid/export/` |
| "Exported instants decide the ordering" | stays in Python (`test_schema_fields.py`), Markdown only |
| the four cross-check scenarios, "Lint-only run" | deleted with the cross-check |
| "Missing org root yields an empty plan" | replaced by "ORG_ROOT that is not a directory" (integration) |
| `test_localization` "A German Org source is exported under its own name" (validator with `org_roots`) | ERT, localization "German Org template passes the Org checks" (stem keeps `.de`) |

New ERT tests also cover:

- both instants of the fold hour;
- `#+LAST_MODIFIED` before `#+CREATED` across the fold;
- a missing zone;
- the problem-line format;
- the absence of Org, ox-hugo and tomelr after the library loads.
- the whole-line parity scenarios and the forbidden routes listed
  under "Keeping the messages identical".

`tests/test_elisp.py` runs `emacs -Q --batch -l
<repo>/tests/el/osdb-org-tests.el -f ert-run-tests-batch-and-exit` with
a timeout and captured output. It asserts exit 0 and shows the output
when the run fails. It skips through `pipeline_support.require_tool`,
so the reason names `emacs`. Running the suite through pytest keeps
`python3 -m pytest tests` as the single entry point, and gives the
workflow one command to name.

The Emacs 29 workflow adds `tests/test_elisp.py` to its pytest command.
Ubuntu 24.04's Emacs 29 bundles Org 9.6, and local development uses
Emacs 30 with Org 9.7. The library uses no Org, but the workflow also
runs the export integration tests, which do.

## What Python keeps

| `validate.py` | kept for |
|---|---|
| `discover`, `read_text`, `Entry` | Markdown roots; `has_org_sources` and `org_stems` |
| `check_file_name`, `file_name_pattern` | Markdown file names |
| `language_of`, `base_name` | variants, staging, PDF names |
| `load_zone`, `ZONE_NAME`, `format_offset`, `zone_offset_mismatch` | Markdown offset warnings; `pipeline.berlin` |
| `WEEKDAYS` | `pipeline.org_timestamp` for `new` |
| `AI_MODEL_RE` | Markdown `ai_model`; `new --ai-model` |

Removed from `validate.py`:

- `ORG_KEYWORDS`, `ORG_KEYWORD_RE`, `ORG_BLOCK_BEGIN_RE`,
  `ORG_BLOCK_END_RE`, `ORG_TIMESTAMP_RE` and `ORG_FORM`;
- `org_keywords`, `parse_org_timestamp`, `local_instants`, `OrgSource`,
  `lint_org`, `describe_instants` and `cross_check`;
- `--org-root` and the Org branch of `run`, which becomes
  `run(content_roots, ctx)`.

Removed from `pipeline.py`: `PLAN_NAME`, `export_instants`,
`plan_export`, `write_export_plan`, and the `json` import if nothing
else uses it. `check_staging` takes stems instead of plan entries.
`org_stems` is added. `org_timestamp`, `rfc3339` and `fill_template`
stay, because `new` writes Org and Markdown stubs as plain text.

Whether a stub from `new` passes the Org checks is a question across
the boundary. Two tests answer it:

- the stub tests pin the exact keyword lines `new` writes;
- an integration scenario runs `new` and then `export`.

The Python tests no longer run the validator on Org stubs.

## Risks

- **The fold arithmetic is new code in a new language.** The ERT
  suite carries every timestamp case the Python tests had, plus both
  fold instants and the cross-fold ordering. The integration scenario
  "Exported dates match the fixture exports" compares real exports of
  `valid/org/` with the hand-written `valid/export/` files. This
  replaces the cross-check's role as a second opinion.
- **Org 9.6 versus 9.7.** The library avoids Org. The export path is
  unchanged apart from where its values come from.
- **Stdout pollution.** The contract is exact: Emacs's stdout holds
  only problem lines. Three scenarios enforce it:
  - "Emacs's stdout holds only problem lines" runs export.el directly;
  - "Warnings alone do not stop the export" requires that the
    non-step stdout lines of a full export, ox-hugo included, are
    exactly the warning;
  - "Warnings followed by an export failure" checks that warnings do
    not divert a later failure from the log-dumping branch.

  If ox-hugo ever printed to stdout in batch mode, these would fail,
  and export.el would have to bind `standard-output` around the
  ox-hugo call.
