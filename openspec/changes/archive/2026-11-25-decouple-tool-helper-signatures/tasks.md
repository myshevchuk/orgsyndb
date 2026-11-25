## 1. Specs

- [x] 1.1 Rewrite `org-export` delta to state staging, swap/rollback, and severity detection behaviorally
- [x] 1.2 Rewrite `build-script` delta to state tool detection, `build`, `pdf`, `new`, `index`, and `manifest` behaviorally

## 2. Check

- [x] 2.1 Validate OpenSpec change strictly (`openspec validate decouple-tool-helper-signatures --strict`)
- [x] 2.2 Archive change and verify living specs cleanly apply with no behavioral regression (`tests/test_export_replace.py`, `tests/test_pipeline_logic.py`)
