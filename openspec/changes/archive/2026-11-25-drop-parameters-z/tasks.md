## 1. Model and tests

- [x] 1.1 Remove `Parameters.z` and unused `z_of` import from `webapp/planning/models.py`
- [x] 1.2 Update `webapp/tests/test_planning_parameters.py` and test `z_of` in `webapp/tests/test_planning_demand.py`

## 2. Check

- [x] 2.1 Validate OpenSpec change strictly (`openspec validate drop-parameters-z --strict`)
- [x] 2.2 Run planning area tests (`uv run pytest tests/test_planning_parameters.py tests/test_planning_demand.py tests/test_planning_runway.py tests/test_planning_item.py tests/test_planning_list.py`)
