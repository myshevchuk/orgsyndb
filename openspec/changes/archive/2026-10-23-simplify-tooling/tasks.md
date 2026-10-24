## Tests

- [x] Call `write_export_plan` and `new_procedure` in-process instead
  of running the pipeline's command line.
- [x] Replace the CLI and pass-through scenarios with the
  no-command-line and arguments-refused tests.
- [x] Assert that `check-deps` prints no version note, and update the
  ignore-rule test.

## Implementation

- [x] Remove the pipeline's command line, shebang and PEP 723 block,
  the `PROG` override and the executable bit.
- [x] Check `new`'s input only in `new_procedure`.
- [x] Remove `validate ARGS...` and the `check-deps` version notes.
- [x] Share `remove_tree`; name the directories in the validate step.
- [x] Remove the second argument check in `export.el`.
- [x] Drop the leftover ignore rules.

## Documents

- [x] README: command table, usage text and sample build output.

## Validation

- [x] `openspec validate --strict`.
- [x] Run the full test suite.
