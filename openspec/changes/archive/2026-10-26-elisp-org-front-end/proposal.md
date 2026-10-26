## Why

Org support is split across two languages. Python discovers the Org
procedures, lints their file-level keywords, parses their timestamps in
Europe/Berlin, chooses `date` and `lastmod`, and hands Emacs a JSON
plan; the validator then reads the Org sources again to cross-check
them against their exports. Org should be a self-contained front end:
everything that reads Org lives in Emacs, and Python only ever sees
Markdown.

## What Changes

- `tools/export.el` takes the Org directory instead of a plan:
  `emacs -Q --batch -l tools/export.el ORG_ROOT STAGING_DIR`. It
  discovers the Org sources, checks their file names and file-level
  keywords, parses the timestamps in Europe/Berlin, chooses `date` and
  `lastmod` by the existing rule, and exports each source. The JSON plan
  is gone.
- Emacs reports every problem with an Org source as a
  `<path>:<field>: <severity>: <message>` line, with the messages the
  Python checks gave. It narrows them only by accepting ASCII digits
  alone and trimming only spaces, tabs and CR. When any line is an error it exports nothing,
  installs nothing and exits 1, and `orgsyndb` stops with "the Org
  sources have errors; build/export/ is unchanged". `orgsyndb` prints
  these lines on its stdout.
- The values Emacs chooses become authoritative. A source that could
  set `date`, `lastmod`, `ai_model` or its export's file name by
  another route that ox-hugo reads is an error, and nothing is
  exported. Such routes include `#+DATE`, `#+HUGO_LASTMOD`, a custom
  front-matter `:ai_model`, `EXPORT_*` properties and logbook drawers.
- `orgsyndb` rejects an `org/procedures` that exists but is not a
  directory, and keeps the previous `build/export/`.
- The Org functions live in a new library, `tools/osdb-org.el`, which
  loads without Org, ox-hugo or tomelr and starts no export, so that an
  ERT suite under `tests/el/` can test them. A pytest module runs the
  ERT suite and skips without `emacs`, and the Emacs 29 workflow runs it
  as well.
- The validator handles Markdown only. **BREAKING**: `--org-root` is
  removed, along with the Org keyword lint and the cross-check between
  Org sources and their exports. Emacs writes `date`, `lastmod` and
  `ai_model` from the keywords and refuses every other route to them,
  so an export cannot disagree with its source.
- `pipeline.py` loses the export plan and its timestamp rule. It still
  reads Org file names to decide whether Emacs is needed and which
  `<stem>.md` files the staging directory must hold. `new` still
  fills the Org template.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `org-export`: the invocation, discovery, checks and problem report
  move into Emacs; the export plan is removed; adds the library and the
  ERT suite, and the workflow runs the suite.
- `procedure-schema`: the Org keyword, mapping and template scenarios
  are proved by the ERT suite and by the export instead of the
  validator; adds the rule that the exported values come only from the
  file-level keywords.
- `procedure-validation`: the validator takes Markdown content roots
  only; the cross-check requirement is removed.
- `build-script`: a new definition of "has Org sources", `validate`
  without `--org-root`, the Org stub scenario, and the pipeline
  module's functions.
- `localization`: the German Org stub and template are checked without
  the validator.

## Impact

- Code: `tools/export.el`, new `tools/osdb-org.el`, `tools/pipeline.py`,
  `tools/validate.py`, `tools/orgsyndb`.
- Tests: new `tests/el/osdb-org-tests.el` and `tests/test_elisp.py`;
  deletes `tests/test_org_sources.py`, `tests/test_export_plan.py` and
  the four cross-check fixture cases under `tests/fixtures/org-invalid/`;
  adds the fixture `tests/fixtures/org-invalid/custom-ai-model/`.
  Also changes `tests/support.py`, `tests/test_validate_cli.py`,
  `tests/test_pipeline_logic.py`, `tests/test_templates.py`,
  `tests/test_localization.py`, `tests/test_schema_fields.py`,
  `tests/test_build_script.py`, `tests/test_export_integration.py` and
  `tests/test_emacs_29_workflow.py`.
- CI: `.github/workflows/emacs-29.yml`.
- Documentation: `README.md`, `docs/SCHEMA.md`, `docs/SCHEMA.de.md`,
  `docs/AUTHORING-ORG.org` and `docs/AUTHORING-ORG.de.org`.
- Depends on `markdown-test-collection` being merged first: the
  integration scenarios use its test collection, and the deltas restate
  the requirements as that change leaves them.
