## Why

The Emacs 29 workflow's `apt-get install` of `emacs-nox` and `git`
also installs every recommended package, among them postfix, mailutils,
guile and gsasl. None of them is needed to export or to run the tests,
and on its first GitHub run the install step took 24 of the job's 25
minutes, most of it downloading packages.

## What Changes

- The workflow installs `emacs-nox` and `git` with
  `--no-install-recommends`. The export and the 31 tests pass with that
  install on Ubuntu 24.04 (checked in a local `ubuntu:24.04` container
  with `ca-certificates` added, which the GitHub runner image already
  carries).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `org-export`: "Export checked on Emacs 29" names the flag.

## Impact

- `.github/workflows/emacs-29.yml`, `tests/test_emacs_29_workflow.py`.
- No document a person reads mentions the workflow's install command.
