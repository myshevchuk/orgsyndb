## Why

Work now lands on `develop`, and `main` moves only by fast-forward to a
tested commit of `develop`. Both workflows run on pushes to `main`
alone, so a change squash-merged into `develop` and pushed gets no CI
until it reaches `main`, which is when the demo site deploys. CI has to
run on `develop` for it to be the place where work is tried first.

## What Changes

- `demo-site.yml` and `emacs-29.yml` also run on pushes to `develop`.
- The demo site still deploys only from `main`; a push to `develop`
  builds it without deploying.
- The README says where work lands, which branch deploys, and how to
  install the package from `develop`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `demo-site`: "Demo site workflow" triggers on pushes to `main` and
  `develop`.
- `org-export`: "Export checked on Emacs 29" triggers on pushes to
  `main` and `develop`.

## Impact

- `.github/workflows/demo-site.yml`, `.github/workflows/emacs-29.yml`
- `tests/test_demo_site.py`, `tests/test_emacs_29_workflow.py`
- `README.md`
