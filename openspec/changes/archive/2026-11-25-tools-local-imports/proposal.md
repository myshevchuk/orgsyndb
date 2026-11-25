## Why

`tools/validate.py`, `tools/pipeline.py`, and `tools/orgsyndb` are
required to need no third-party Python packages so that authors,
pre-commit hooks, Emacs, CI, and the builder container run them with
system `python3` and no virtual environment. The AST import scenarios
express that rule as fixed allowlists (`sys.stdlib_module_names`, plus
only `validate` for `pipeline.py` and `pipeline`/`validate` for
`orgsyndb`), and `build-script` pins a 21-function inventory on
`tools/pipeline.py`. Together those constraints prevent organizing
`tools/` into smaller stdlib-only modules without violating the specs.

## What Changes

- Relax the import rule in `procedure-validation` and `build-script`
  from fixed allowlists to standard-library modules plus local modules
  and packages under `tools/`, keeping the zero-third-party-package
  guarantee for every Python file under `tools/`.
- Remove the 21-function exposure inventory from `build-script`
  ("Pipeline helper module").
- Update the AST import tests to check against
  `sys.stdlib_module_names` and local modules under `tools/`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `procedure-validation`: allow `tools/validate.py` to import local
  modules under `tools/` in addition to the standard library.
- `build-script`: allow `tools/orgsyndb`, `tools/pipeline.py`, and any
  local Python modules under `tools/` to import from the standard
  library and local modules under `tools/`, and drop the flat
  21-function inventory on `tools/pipeline.py`.

## Impact

- `openspec/specs/procedure-validation/spec.md`,
  `openspec/specs/build-script/spec.md`
- `tests/support.py`, `tests/test_validate_cli.py`,
  `tests/test_pipeline_logic.py`, `tests/test_build_script.py`
- No production code changes and no new dependencies.
