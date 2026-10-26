## 1. Tests (red)

- [x] 1.1 Before any production change, save a copy of a fresh
  `tools/orgsyndb -C examples/demo export` (`build/export/`) outside the
  repository, and the output of the current validator run with
  `--org-root` on each directory `tests/fixtures/org-invalid/*/org` and
  on `tests/fixtures/valid/org`. Tasks 6.4 and 6.5 compare against
  them.
- [x] 1.2 Create `tests/el/osdb-org-tests.el`. It loads
  `tools/osdb-org.el` by file name relative to itself, finds fixtures
  under `tests/fixtures/` the same way, and has one `ert-deftest` per
  scenario stated as an ERT test, with the scenario name in its
  docstring:
  - org-export: "Entries of the Org root", "Subdirectory in the Org
    root", "Problem line format", "Problems in path order", "File name
    and keywords together", "Language code in an Org file name",
    "Invalid UTF-8 suppresses every other check", "Unreadable source",
    "Byte-order mark and CRLF line ends", "Missing time zone", "Library
    loads alone", "Summer time", "Winter time, last second before the spring
    change", "Fall-back hour out of wall-clock order", "Equal times in
    the fall-back hour", "Instants of a wall-clock time" and "Choice
    among fall-back instants".
  - procedure-schema "Org file-level keywords": all seventeen
    scenarios, including "Invalid date does not cascade",
    "Modification before creation across the fall-back hour", "Invalid
    time", "Dependent checks of the keywords" (one test per numbered
    case, or a table-driven test that names each case), "Keyword lines"
    and "ASCII digits and ASCII trimming".
  - procedure-schema "Exported values come only from the file-level
    keywords": all five scenarios. "Keywords that would set exported
    values" covers every keyword of the rule.
  - procedure-schema "Org template passes the Org checks".
  - localization "German Org template passes the Org checks".

  Keyword edits work like `set_keyword` in the deleted
  `test_export_plan.py`: replace exactly one `#+KEYWORD:` line of a
  copy, and fail if there is not exactly one. The scenarios that say
  "the problem lines are exactly" compare whole lines, as the ERT suite
  requirement defines.
- [x] 1.3 Add `tests/test_elisp.py` for org-export "ERT suite under
  pytest" and "ERT suite without Emacs". It runs `emacs -Q --batch -l
  <repo>/tests/el/osdb-org-tests.el -f ert-run-tests-batch-and-exit`
  with a timeout, asserts exit 0, shows the captured output when the run
  fails, and skips through `pipeline_support.require_tool("emacs")`.
- [x] 1.4 Add the committed fixture
  `tests/fixtures/org-invalid/custom-ai-model/org/OSDB-0216-custom-ai-model.org`.
  It is a valid Org procedure with `#+AI_MODEL: none` and the line
  `#+HUGO_CUSTOM_FRONT_MATTER: :ai_model "example-model-1"`, with
  fictitious names.
- [x] 1.5 In `tests/test_export_integration.py`:
  - add "Org errors stop validate before any package is installed" and
    "Conflicting front matter stops the export" (test collection,
    `make_sandbox(..., link_caches=False)`; they skip without `emacs` or
    `git` only);
  - add "Emacs's stdout holds only problem lines" and "ORG_ROOT that is
    not a directory" (they skip without `emacs` only);
  - add "Org root that is not a directory" (test collection; it needs
    no Emacs);
  - add "Warnings alone do not stop the export", "Warnings followed by
    an export failure" (with the pin-mismatch setup of `PinTests`) and
    "Stubs from new pass the Org checks";
  - for every stdout assertion, compare the lines that do not begin
    with `==> ` exactly, as the scenarios state;
  - add procedure-schema "Exported dates match the fixture exports";
  - make "Seed export validates cleanly" run the validator without
    `--org-root`;
  - make "No package.el" read `tools/osdb-org.el` as well.
- [x] 1.6 In `tests/test_export_replace.py`, add "Org stems" and
  "Staging check".
- [x] 1.7 In `tests/test_build_script.py`, add "Org sources by entry
  names" and "No Org reading in Python".
- [x] 1.8 In `tests/test_validate_cli.py`:
  - add "Org root option is refused";
  - remove "Subdirectory in an Org root", which moved to ERT;
  - expect `validated 4 files` in "Summary line".
- [x] 1.9 In `tests/support.py`, drop the `org_roots` parameter of
  `fixture_run`, and make `valid_set_run` run on `valid/md` and
  `valid/export` alone.
- [x] 1.10 Move "Exported instants decide the ordering" into
  `tests/test_schema_fields.py` as a Markdown-only fixture run, without
  an Org root.
- [x] 1.11 Remove the Org-lint uses of the validator:
  - in `tests/test_pipeline_logic.py`, delete the `export_instants`
    test ("Fall-back hour out of wall-clock order (function)"), and
    make "Org stub" assert each keyword line exactly once instead of
    running the validator;
  - in `tests/test_templates.py`, delete
    `test_substituted_org_template_passes_the_lint`;
  - in `tests/test_localization.py`, make "German stub" assert the
    `#+CREATED` line instead of running the validator on the Org stub;
  - in `tests/test_localization.py`, delete
    `test_german_org_source_and_its_export` ("A German Org source is
    exported under its own name"). It calls `fixture_run(...,
    org_roots=[org])` twice and expects the cross-check's `no exported
    content file` message. Its subject, a German source's stem keeping
    `.de`, moves to the ERT test of localization "German Org template
    passes the Org checks".
- [x] 1.12 Run `grep -rn "org_roots\|--org-root\|org-root\|export_instants\|write_export_plan\|export-plan\|lint_org\|cross_check" tests/`.
  It finds nothing outside the files this section deletes. Each other
  hit is a test this section has missed: replace it or remove it, and
  report which.
- [x] 1.13 In `tests/test_emacs_29_workflow.py`, expect the command
  `python -m pytest tests/test_export_integration.py
  tests/test_elisp.py`.
- [x] 1.14 Delete `tests/test_org_sources.py`,
  `tests/test_export_plan.py`, and the fixture directories
  `tests/fixtures/org-invalid/export-date-mismatch`,
  `export-offset-mismatch`, `export-ai-model-mismatch` and
  `missing-export`.
- [x] 1.15 Run the suite and record what fails. Expected:
  - every ERT test fails or errors on loading the missing library;
  - the new export and validate integration scenarios fail;
  - "Org stems", "Staging check", "Org sources by entry names", "No
    Org reading in Python", "Org root option is refused", "Org root
    that is not a directory", the 4-file summary and the workflow test
    fail.

  Each test must fail on its assertion once the module or function
  exists.

## 2. Elisp

- [x] 2.1 Write `tools/osdb-org.el` (feature `osdb-org`, requiring only
  `cl-lib`, `subr-x` and `time-date`) with the functions of design.md
  "Library interface", following "Timestamp algorithm" and "Keeping the
  messages identical". Loading it defines functions and constants only,
  and no word in it is `node` or `npm`.
- [x] 2.2 Rework `tools/export.el`:
  - take `ORG_ROOT STAGING_DIR`, and update the usage message and the
    commentary;
  - load the library by file name after the isolation settings;
  - check the zone, then that `ORG_ROOT` is a directory;
  - examine `ORG_ROOT`, print the problem lines to stdout and nothing
    else, and exit 1 on any error, all before the bootstrap;
  - exit 0 with no source, before the bootstrap;
  - export each source with the `date`, `lastmod` and `ai_model` that
    `osdb-org-examine` chose, with point at the beginning of the buffer
    after inserting the export's own lines;
  - delete `osdb-read-plan`.
- [x] 2.3 Run the ERT suite directly and through `tests/test_elisp.py`;
  every ERT test passes.

## 3. Python

- [x] 3.1 `tools/validate.py`: remove `--org-root`, the Org branch of
  `run`, `ORG_KEYWORDS`, the `ORG_*` patterns, `ORG_FORM`,
  `org_keywords`, `parse_org_timestamp`, `local_instants`,
  `OrgSource`, `lint_org`, `describe_instants` and `cross_check`.
  Require at least one content root, and update the module docstring
  and the argparse help.
- [x] 3.2 `tools/pipeline.py`:
  - remove `PLAN_NAME`, `export_instants`, `plan_export`,
    `write_export_plan` and any import left unused;
  - add `org_stems`, and give `has_org_sources` the build-script
    definition;
  - make `check_staging` take stems;
  - update the module docstring.
- [x] 3.3 `tools/orgsyndb` `run_export`:
  - after the recovery step, fail with `org/procedures is not a
    directory` when it exists and is not one;
  - decide by `has_org_sources`, and pass `org/procedures` and the
    staging directory to Emacs;
  - capture Emacs's stdout and stderr, write both to
    `build/export.log`, and copy Emacs's stdout to stdout;
  - on failure, choose between the two messages of org-export "Org
    sources and their problems";
  - install with `check_staging(build, org_stems("org/procedures"))`.

  `run_validator` drops `--org-root`, and its step line names only the
  content roots.
- [x] 3.4 Run the full suite with `emacs` on `PATH`; it passes.

## 4. Workflow

- [x] 4.1 In `.github/workflows/emacs-29.yml`, run
  `python -m pytest tests/test_export_integration.py
  tests/test_elisp.py` after the export step, and update the header
  comment.

## 5. Documentation (doc stage)

- [x] 5.1 `README.md`:
  - the `build/` row no longer lists the export plan;
  - the `export` row says that Org problems are reported on stdout and
    stop the export before ox-hugo is fetched;
  - the Development section names the ERT suite under `tests/el/`,
    which `tests/test_elisp.py` runs, and says that the Emacs 29
    workflow runs it too.
- [x] 5.2 `docs/SCHEMA.md`:
  - the Org keyword section says that `orgsyndb export` checks the
    keywords;
  - the paragraph on the validator's cross-check goes;
  - "Reading validator output" drops `--org-root` and the `#+` fields,
    and attributes the Org example line to `orgsyndb export`, which
    prints Org problems in the same form.
  - a new paragraph lists the inputs an Org source must not use to set
    `date`, `lastmod`, `ai_model` or the export's file name (procedure-schema
    "Exported values come only from the file-level keywords"), with the
    message forms.
- [x] 5.3 `docs/SCHEMA.de.md`: the same changes as 5.2.
- [x] 5.4 `docs/AUTHORING-ORG.org` and `docs/AUTHORING-ORG.de.org`,
  "Export, validate, and preview": `orgsyndb export` reports problems
  in the Org keywords and file names, and any line that would set the
  exported dates, AI model or file name, before it exports anything, in
  the validator's line format.

## 6. Validation

- [x] 6.1 Run `openspec validate elisp-org-front-end --strict`.
- [x] 6.2 Run the full suite with `emacs` on `PATH`; it passes.
- [x] 6.3 Run `python3 -m pytest -rs tests` with a `PATH` that finds
  every tool the suite uses except `emacs`. It passes, and every skip
  names `emacs`. The skipped tests are those
  `markdown-test-collection` lists, plus `tests/test_elisp.py` and the
  new Emacs-dependent scenarios of 1.5.
- [x] 6.4 Export `examples/demo` again, and compare `build/export/`
  byte for byte with the copy saved in 1.1; it is identical.
- [x] 6.5 For each directory of 1.1, run `osdb-org-examine` in batch
  Emacs and compare its problem lines with the saved validator lines,
  ignoring the summary line. They are identical, apart from the four
  deleted cross-check cases. None of these fixtures uses non-ASCII
  digits or Unicode whitespace, so the deliberate differences do not
  show here.
- [x] 6.6 In an Ubuntu 24.04 container with `emacs-nox` (Emacs 29) and
  Python 3.14, run `tools/orgsyndb -C examples/demo export` and
  `python -m pytest tests/test_export_integration.py
  tests/test_elisp.py` as the workflow does; both pass.
- [x] 6.7 After `openspec archive`, edit the Purpose line of
  `openspec/specs/procedure-validation/spec.md` so that it no longer
  mentions Org roots. Archiving does not change Purpose lines.
