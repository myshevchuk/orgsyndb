## 1. Fixtures (test writer)

Fixture layout, and the split between committed cases and in-test
variants, follow design.md D13. Each case's file name, field values and
expected message are given by its scenario in
`specs/procedure-schema/spec.md` or `specs/procedure-validation/spec.md`.
Every fixture is fully valid apart from the one fault it exists for:
all required fields, all eight body sections, and correct offsets. That
way it yields exactly one problem. Use fictitious names only.

- [x] 1.1 Add `tests/fixtures/reaction_types.toml`: at least
      `esterification` and `reduction`, each with a `label`, and
      deliberately without `reductive-amination`. Add
      `tests/fixtures/bad-vocabulary.toml` (entry `[reduction]` with no
      `label`) and `tests/fixtures/static/structures/osdb-0001.svg` (a
      minimal hand-written SVG).
- [x] 1.2 Add `tests/fixtures/baseline/OSDB-0100-baseline.md`. It has the
      required fields only, `reaction_types = ["esterification"]`, a
      summer `+02:00` `date`, one front-matter key per line, `[product]`
      as the last table, and all eight body sections.
- [x] 1.3 Add the valid set:
      - `valid/md/OSDB-0001-*.md`: every optional field;
        `structure_image = "structures/osdb-0001.svg"`; a valid `cas` such
        as `141-78-6`; a winter `+01:00` `date`; and the tolerated keys
        `description` and `weight`. It lists no precursors.
      - `valid/md/OSDB-0002-*.md`: `precursors = ["OSDB-0003"]`, the
        heading `## Workup and purification`, and an extra `## Discussion`.
      - `valid/org/OSDB-0003-*.org`, with
        `#+CREATED: [2026-10-19 Mon 17:42:05]` and `#+AI_MODEL: none`. Its
        export `valid/export/OSDB-0003-*.md` is shaped like ox-hugo output,
        with `draft = false`, `date = 2026-10-19T17:42:05+02:00`, a
        matching `lastmod`, no `ai_model`, and headings with `{#anchor}`
        suffixes.
      - `valid/org/OSDB-0004-ambiguous-hour.org`, with
        `#+CREATED: [2026-10-25 Sun 02:50:00]` and
        `#+LAST_MODIFIED: [2026-10-25 Sun 02:10:00]`. Its export
        `valid/export/OSDB-0004-ambiguous-hour.md` has
        `date = 2026-10-25T02:50:00+02:00` and
        `lastmod = 2026-10-25T02:10:00+01:00`.
- [x] 1.4 Add the committed invalid content cases under
      `tests/fixtures/invalid/`, one directory and one file each:
      `invalid-toml`, `bad-id-format`, `file-name-id-mismatch`,
      `slug-mismatch`, `missing-title`, `unknown-reaction-type`,
      `yield-out-of-range`, `date-as-string`, `missing-precursor`,
      `missing-structure-image` and `author-key`. Two cases differ in
      shape:
      - `subdirectory`: the root holds only `nested/OSDB-0135-nested.md`.
      - `duplicate-id`: roots `a/` and `b/`, one file each.
- [x] 1.5 Add the committed warning cases under `tests/fixtures/warn/`:
      `missing-section`, `offset`, and `stray-file` (a valid procedure plus
      `notes.txt`).
- [x] 1.6 Add the Org cases under
      `tests/fixtures/org-invalid/<case>/org/`:
      - Lint-only: `missing-created`, `duplicate-created`,
        `active-timestamp`, `missing-seconds`, `invalid-date`,
        `wrong-weekday`, `nonexistent-local-time`,
        `last-modified-before-created`, `bad-ai-model`,
        `bad-org-file-name`, and `subdirectory` (the root holds only
        `nested/OSDB-0215-nested.org`).
      - Cross-check, each with an `export/` directory:
        `export-date-mismatch`, `export-offset-mismatch`,
        `export-ai-model-mismatch`, and `missing-export` (whose `export/`
        holds only `.gitkeep`).

## 2. Failing tests (test writer)

All tests are `unittest.TestCase` classes in `tests/test_*.py`, named for
the behaviour they pin, and run with `python3 -m pytest tests`. They drive
`tools/validate.py` as a subprocess with `cwd` set to a temporary
directory, and locate the repo from their own `__file__` (design.md D12).
Each test must fail on its assertion, not merely on an import error, once
`tools/validate.py` exists.

- [x] 2.1 Add a shared test helper (e.g. `tests/support.py`). It makes
      fixture runs and valid-set runs as defined in "Fixture suite", and
      variant runs: it copies the baseline into a fresh temporary content
      root under a given file name, with one textual edit applied. The
      edits are: replace or insert a front-matter line (including inside
      `[product]`), remove a line, swap the delimiters, move a body
      section, or fence a heading. It also parses stdout lines into
      `(path, field, severity, message)`.
- [x] 2.2 `tests/test_validate_cli.py` covers every scenario of the
      requirements "Command-line interface", "Default paths resolve from
      the script location", "Vocabulary file errors are configuration
      errors", "Problem report format", "Exit status", "File discovery"
      (both subdirectory cases included) and "Front-matter parsing".
- [x] 2.3 `tests/test_schema_fields.py` covers the scenarios of the
      procedure-schema field requirements: identifier, uniqueness, file
      names, slug, required fields, status, reaction type, tags, yield,
      scale, product, timestamps, precursors, structure image, other
      optional fields, and keys outside the schema. Each committed case
      runs from disk, and each variant case through the helper. Each test
      asserts the exit status, the exact line count, the field, the
      severity and the message substring.
- [x] 2.4 `tests/test_body_sections.py` covers the "Body sections"
      scenarios. `missing-section` runs from disk; `section-order` and
      `heading-in-code` run as variants. It also checks that the valid
      set's anchors, case variants and extra headings produce no `body`
      line.
- [x] 2.5 `tests/test_org_sources.py` covers the scenarios of "Org
      file-level keywords" (the ambiguous-hour case included), "Org
      keywords map to exported front matter" (including the in-test
      `OSDB-0004` mutation), "Org sources are cross-checked against their
      export", and the Org half of "Dependent checks are suppressed".
- [x] 2.6 `tests/test_vocabulary.py` covers both scenarios of
      "Reaction-type vocabulary file".
- [x] 2.7 `tests/test_templates.py` covers every scenario of "Markdown
      template" and "Org template". It performs the `OSDB-0000` and
      `osdb-0000` substitutions itself, as `orgsyndb new` will.
- [x] 2.8 Add the "Fixture suite" scenarios ("Valid set passes cleanly",
      "Baseline is valid", "Each committed invalid fixture fails for one
      reason") and the remaining "Dependent checks are suppressed"
      scenario. Then run the whole suite and report which tests fail and
      why. All are expected red at this point.

## 3. Vocabulary (implementer)

- [x] 3.1 Add `site/data/reaction_types.toml` with the fifteen entries of
      design.md D7, in alphabetical order, each a table with a `label`.

## 4. Validator (implementer)

`tools/validate.py` is a single, standard-library-only, annotated,
79-column file, with a `#!/usr/bin/env python3` shebang, a PEP 723 block,
an executable bit, and `main(argv) -> int` (design.md D12). Keep pure checks
separate from I/O.

- [x] 4.1 Add argument parsing, default-path resolution from the script
      location, and configuration errors with exit status 2: no roots, a
      root that is not a directory, a bad vocabulary file, and the
      Europe/Berlin zone being unavailable.
- [x] 4.2 Add root discovery (D11): a subdirectory is an error, a stray
      file is a warning, and dotfiles and `_index.md` are skipped. Add
      front-matter splitting and parsing, with the `front_matter`
      errors.
- [x] 4.3 Add the per-field checks for the required fields, `status`,
      `reaction_types`, `tags`, `yield_percent`, `scale`, `product` (with
      the CAS check digit) and `date`/`lastmod` (typing, ordering and the
      offset warning).
- [x] 4.4 Add the optional-field checks (`precursors` shape and self
      reference, `structure_image`, `checked_by`, `references`, `ai_model`)
      and the handling of tolerated, rejected and unknown keys (D4).
- [x] 4.5 Add the cross-file checks: file-name/ID agreement, `slug`
      equality, duplicate IDs across roots and precursor existence. Apply
      the D10 suppression rules.
- [x] 4.6 Add body-section recognition and the missing-section and order
      warnings (D6).
- [x] 4.7 Add the Org keyword lint for `--org-root`: presence, uniqueness,
      format, inactive brackets, calendar validity, weekday, Europe/Berlin
      existence, ordering (earliest possible `#+CREATED` instant against
      latest possible `#+LAST_MODIFIED` instant, D2), `#+AI_MODEL` and the
      file name.
- [x] 4.8 Add the Org-to-export cross-check: stem pairing, the missing
      export, `date`/`lastmod` against the Org timestamps under
      Europe/Berlin, and `ai_model` against `#+AI_MODEL`.
- [x] 4.9 Add output: sorted, deterministic problem lines on stdout, the
      summary line on stderr, and exit statuses 0, 1 and 2.

## 5. Templates (implementer)

- [x] 5.1 Add `templates/procedure.md` per "Markdown template" and D8. It
      uses plain-language TOML comments for the co-worker, has the optional
      fields commented out, and passes once its placeholders are
      substituted.
- [x] 5.2 Add `templates/procedure.org` per "Org template" and D8. It has
      real Europe/Berlin timestamps at the time of writing, `#+AI_MODEL`
      set to the writing model's exact identifier, repeated
      `#+HUGO_CUSTOM_FRONT_MATTER:` lines (with `product` as an alist map),
      and the eight top-level headings.

## 6. Verification (implementer)

- [x] 6.1 Run `python3 -m pytest tests` until it is fully green, without
      editing any test. Return any test that looks wrong to the
      orchestrator.
- [x] 6.2 Run `tools/validate.py` by hand from a directory outside the repo
      on `tests/fixtures/valid/*` and confirm that the output is empty and
      the exit status is 0. Run `openspec validate add-procedure-schema
      --strict`.

## 7. Documentation (orchestrator)

- [x] 7.1 Hand `docs/SCHEMA.md` to the doc writer (Markdown, for the owner
      and the co-worker). Its sources are this change's specs, design.md,
      `site/data/reaction_types.toml`, the two templates and
      `tools/validate.py`. Check the result against those sources.
