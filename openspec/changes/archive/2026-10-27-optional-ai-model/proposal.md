## Why

Recording which AI model assisted with a procedure is a side detail, but
the schema treats it as a central one: every Org source must carry
`#+AI_MODEL`, even a human-written one must say `none`, `orgsyndb new`
has an `--ai-model` option, and every sample must name its writing model.
The keyword should be tolerated and recognised when present, and nothing
more.

## What Changes

- `#+AI_MODEL` becomes optional in Org sources. When present it is still
  checked (at most once, `none` or a model identifier) and still mapped
  to `ai_model`; when absent the export writes no `ai_model`.
- **BREAKING** `orgsyndb new` loses `--ai-model`. Stubs record no AI
  model: an Org stub has no `#+AI_MODEL` line, a Markdown stub keeps the
  template's commented-out `ai_model` line.
- The Org template and the samples are no longer required to name the
  model that wrote them. The files keep their existing lines.
- The Markdown `ai_model` field, and the rule that an Org source sets
  the exported `ai_model` only through `#+AI_MODEL`, are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `procedure-schema`: `#+AI_MODEL` optional; mapping when absent; the
  Org template need not name a model.
- `build-script`: `new` without `--ai-model`; stubs record no model.
- `sample-procedures`: samples need not name a model; the test
  collection carries `ai_model` only where the Org source names one.
- `org-export`: `ai_model` written only for a source that names a model.

## Impact

- `tools/osdb-org.el`, `tools/pipeline.py`, `tools/orgsyndb`.
- Tests: `tests/el/osdb-org-tests.el`, `tests/test_pipeline_logic.py`,
  `tests/test_export_integration.py`, `tests/test_samples.py`,
  `tests/sample_support.py`, `tests/test_templates.py`,
  `tests/test_localization.py`.
- Docs: `README.md`, `docs/SCHEMA.md`, `docs/SCHEMA.de.md`,
  `docs/AUTHORING-ORG.org`, `docs/AUTHORING-ORG.de.org`.
