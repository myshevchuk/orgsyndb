## Bootstrap

- [x] Add the tests for the old-Emacs refusal, the absence of package.el
  and the Emacs 29 workflow, red.
- [x] Clone the pinned packages with git and refuse Emacs older than 29.1
  in `tools/export.el`.
- [x] Add `.github/workflows/emacs-29.yml`.

## Validation

- [x] Run the full test suite with a fresh `.emacs-batch/`.
- [x] Run the export integration tests under Ubuntu 24.04's Emacs 29 in a
  container, as the workflow does.
- [x] Update the README's dependency notes.
