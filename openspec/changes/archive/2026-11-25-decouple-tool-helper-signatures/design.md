## Context

The dependency-injection parameters (`rename`, `remove`, `now`) and
internal pure helpers in `tools/pipeline.py` are useful engineering for
fast, mock-free unit tests (`tests/test_export_replace.py`,
`tests/test_pipeline_logic.py`). The spec drag comes from naming those
internal Python functions and parameter lists in normative `SHALL`
requirements rather than stating the observable contracts they enforce.

## Goals / Non-Goals

- **Goals:** Preserve every behavioral guarantee in `org-export` and
  `build-script` while removing internal `pipeline.*` and `validate.*`
  helper signatures from their normative requirements.
- **Non-Goals:** Changing any production code in `tools/pipeline.py`,
  removing DI parameters (`rename`, `remove`, `now`), or modifying
  existing unit tests.

## Decisions

- Keep all observable CLI exit codes, stderr/stdout formats, directory
  states (`.export-staging/`, `.export-previous/`, `build/tmp/`),
  rollback/recovery semantics, stub formatting, and JSON schemas intact.
- Keep `tools/pipeline.py`'s existing helper functions and DI parameters
  untouched so unit tests remain green and mock-free.
