## Tests

- [ ] Call `write_export_plan` and `new_procedure` in-process instead
  of running the pipeline's command line.
- [ ] Replace the CLI and pass-through scenarios with the
  no-command-line and arguments-refused tests.
- [ ] Assert that `check-deps` prints no version note, and update the
  ignore-rule test.

## Implementation

- [ ] Remove the pipeline's command line, shebang and PEP 723 block,
  the `PROG` override and the executable bit.
- [ ] Check `new`'s input only in `new_procedure`.
- [ ] Remove `validate ARGS...` and the `check-deps` version notes.
- [ ] Share `remove_tree`; name the directories in the validate step.
- [ ] Remove the second argument check in `export.el`.
- [ ] Drop the leftover ignore rules.

## Documents

- [ ] README: command table, usage text and sample build output.

## Validation

- [ ] `openspec validate --strict`.
- [ ] Run the full test suite.
