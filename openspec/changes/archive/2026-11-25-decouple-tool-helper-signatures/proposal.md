## Why

`org-export` and `build-script` currently embed internal Python helper
names and parameter lists from `tools/pipeline.py` and
`tools/validate.py` (such as `pipeline.replace_export(build, rename,
remove)`, `pipeline.new_procedure(collection, words, md, now,
language)`, `pipeline.new_sequence(collection, words, now)`,
`pipeline.check_staging`, `pipeline.recover_export`, `pipeline.pdf_jobs`,
`pipeline.has_org_sources`, `pipeline.org_error_reported`, and
`pipeline.manifest_data`) directly inside normative requirements. That
couples behavioral specifications to internal module layout and helper
signatures, even when the observable CLI and filesystem behavior does
not change.

## What Changes

- Rewrite the affected requirements in `org-export` and `build-script`
  to state observable CLI, filesystem, rollback, timestamp, and JSON
  output behavior rather than internal `pipeline.*` / `validate.*`
  function signatures.
- Keep all existing helper functions and dependency-injection parameters
  (`rename`, `remove`, `now`) intact in `tools/pipeline.py` and keep the
  existing unit and integration tests unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `org-export`: state export staging, atomic swap/rollback/recovery, and
  error-severity detection behaviorally without pinning internal
  `pipeline.*` / `validate.*` helper signatures.
- `build-script`: state tool-presence detection, `build`, `pdf`, `new`,
  `index`, and `manifest` behaviorally without pinning internal
  `pipeline.*` / `validate.*` helper signatures.

## Impact

- `openspec/specs/org-export/spec.md`,
  `openspec/specs/build-script/spec.md`
- No production code changes and no test changes; all existing
  dependency-injection hooks in `tools/pipeline.py` remain in place.
