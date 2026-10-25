## ADDED Requirements

### Requirement: Export without Org sources
When the collection has no Org sources, as the build-script spec defines them, `tools/orgsyndb export` SHALL start no Emacs. It prints the step line `==> export: no Org sources; Emacs is not needed` in place of the Emacs step, and otherwise runs the recover, stage and install steps of "Complete and fresh export directory", so that `build/export/` exists and is empty.

#### Scenario: Export with neither Emacs nor git
- **WHEN** an integration test removes every file from `org/procedures/` and runs `tools/orgsyndb -C <collection> export` with a `PATH` that holds `python3` but neither `emacs` nor `git`
- **THEN** it exits 0, stdout contains `==> export: no Org sources; Emacs is not needed`, and `build/export/` exists and is empty
