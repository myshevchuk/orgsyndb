## 1. Org keyword

- [x] 1.1 ERT: dependent-checks items 10 (no `#+AI_MODEL`) and 11
  (`#+AI_MODEL` twice); red first
- [x] 1.2 `tools/osdb-org.el`: `#+AI_MODEL` optional, at most once;
  absent gives no AI model
- [x] 1.3 Integration: "AI model mapping" with a source without
  `#+AI_MODEL`

## 2. Stubs

- [x] 2.1 Tests: Org stub has no `#+AI_MODEL` line; Markdown stub with a
  quoted title has no `ai_model`; drop the model-identifier tests
- [x] 2.2 `pipeline.fill_template` and `new_procedure` without
  `ai_model`; drop `--ai-model` from `tools/orgsyndb` and its usage

## 3. Samples and templates

- [x] 3.1 Drop the model checks from `tests/test_samples.py`,
  `tests/test_templates.py` and `tests/test_localization.py`
- [x] 3.2 Test-collection sync check: `ai_model` only where the Org
  source names a model

## 4. Docs and verification

- [x] 4.1 Doc writer: update `README.md`, `docs/SCHEMA.md`,
  `docs/SCHEMA.de.md`, `docs/AUTHORING-ORG.org`,
  `docs/AUTHORING-ORG.de.org`
- [x] 4.2 Full suite with and without Emacs; demo export unchanged
