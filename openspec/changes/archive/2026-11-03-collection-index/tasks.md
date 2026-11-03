## 1. Tests, red first

- [x] 1.1 `tests/test_index.py`: the scenarios of collection-index "Index
  data" against `pipeline.index_data`
- [x] 1.2 `tests/test_index.py`: the scenarios of build-script "index
  subcommand"
- [x] 1.3 The usage text names `index` (build-script "Entry point
  conventions", scenario "Help"), and `index_data` passes the existing
  pipeline-module checks

## 2. Implementation

- [x] 2.1 `tools/validate.py`: name the scope-entry and product keys as
  constants and use them in `check_scope` and `check_products`
- [x] 2.2 `tools/pipeline.py`: `index_data`
- [x] 2.3 `tools/orgsyndb`: the `index` subcommand and its usage line

## 3. Documents

- [x] 3.1 The README's command list (doc writer)

## 4. Verification

- [x] 4.1 Full suite green
- [x] 4.2 `openspec validate collection-index --strict`
