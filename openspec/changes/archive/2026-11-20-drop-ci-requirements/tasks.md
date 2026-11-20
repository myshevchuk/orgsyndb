## 1. Tests

- [x] 1.1 Remove `tests/test_demo_site.py` and
  `tests/test_emacs_29_workflow.py`, and the workflow helpers of
  `tests/pipeline_support.py` that no other test uses

## 2. Verification

- [x] 2.1 The root suite's affected area passes: `tests/` collects, and
  nothing imports the removed helpers
- [x] 2.2 `openspec validate --specs --strict` passes after the archive

## 3. Archive

- [x] 3.1 Archive, remove `openspec/specs/demo-site/`, and
  squash-merge into `develop`
