## 1. Helpers and tests

- [x] 1.1 Add `local_tool_modules()` and `imported_modules()` helpers to `tests/support.py`
- [x] 1.2 Update AST import tests in `tests/test_validate_cli.py`, `tests/test_pipeline_logic.py`, and `tests/test_build_script.py`

## 2. Check

- [x] 2.1 Validate OpenSpec change strictly (`openspec validate tools-local-imports --strict`)
- [x] 2.2 Run area tests (`python3 -m pytest tests/test_validate_cli.py tests/test_pipeline_logic.py tests/test_build_script.py`)
