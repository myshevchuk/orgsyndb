## Why

The export requires Emacs 30.2. Stable distributions such as Ubuntu
24.04 still ship Emacs 29, so CI runners and agent containers have to
build or fetch a newer Emacs just to export Org. The export itself
does not need Emacs 30: under Emacs 29 only the package.el bootstrap
fails, because `package-vc-install` cannot check out a pinned commit
there. With the packages cloned by git, Emacs 29.3 and Org 9.6.15
export the demo byte for byte as Emacs 30.2 and Org 9.7.11 do.

## What Changes

- `tools/export.el` clones tomelr and ox-hugo with git at their pins
  and puts them on `load-path`, instead of using package.el.
- The export works with Emacs 29.1 or later and refuses an older Emacs
  with a clear message.
- A GitHub Actions workflow runs the export integration tests under
  Ubuntu 24.04's Emacs 29.

## Impact

Affects the org-export capability, `tools/export.el`,
`tests/test_export_integration.py`, the new
`.github/workflows/emacs-29.yml` and its test, and the README's
dependency notes. Existing `.emacs-batch/` caches made by package.el
keep working; `tools/orgsyndb clean --all` replaces them.
