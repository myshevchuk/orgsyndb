## Why

Three requirements fix how the repository's tests and builds are run
rather than what the software does: the demo site's GitHub Actions
workflow, the Emacs 29 export workflow, and the development tools the
lab application's project file names. The owner decided on 2026-11-21
that continuous integration and test tooling belong to the
repository's instructions and its workflow files, which change with
the way the project is worked on, and that no spec fixes them.

## What Changes

- demo-site "Demo site workflow" is removed, and with it the demo-site
  capability, whose only requirement it is: `openspec/specs/demo-site/`
  is deleted at the archive, since a delta cannot leave a spec without
  requirements. The workflow file stays.
- org-export "Export checked on Emacs 29" is removed. The workflow file
  stays.
- web-app "Application project" no longer names the development tools
  of `webapp/pyproject.toml`.
- The tests of the removed requirements, `tests/test_demo_site.py` and
  `tests/test_emacs_29_workflow.py`, are removed, with the workflow
  helpers of `tests/pipeline_support.py` that only they use.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `demo-site`: removed with its only requirement (no delta; the
  directory is deleted at the archive).
- `org-export`: "Export checked on Emacs 29" is removed.
- `web-app`: "Application project" drops the development tools.

## Impact

- `openspec/specs/demo-site/` (removed), `openspec/specs/org-export/`,
  `openspec/specs/web-app/`.
- `tests/test_demo_site.py`, `tests/test_emacs_29_workflow.py`
  (removed), `tests/pipeline_support.py`.
- No production code, workflow file or document changes.
