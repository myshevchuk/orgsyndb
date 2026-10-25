## Why

Emacs is needed only to export Org procedures, yet every collection
command requires Emacs and git, even for a collection that holds only
Markdown. Installing Emacs is a heavy step for CI runners and agent
containers that never touch Org.

## What Changes

- `export`, `validate`, `build`, `serve` and `pdf` require `emacs` and
  `git` only when the collection has Org sources.
- With no Org sources, the export step starts no Emacs and leaves an
  empty `build/export/`.
- `check-deps` reports `emacs` and `git` as optional, for Org
  procedures, and requires only `python3`, `hugo` and `weasyprint`.

## Impact

Affects the build-script and org-export capabilities, `tools/orgsyndb`,
`tools/pipeline.py`, `tests/test_build_script.py` and the README's
dependency notes.
