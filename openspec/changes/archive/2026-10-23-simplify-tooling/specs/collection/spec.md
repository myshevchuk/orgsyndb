## MODIFIED Requirements

### Requirement: Choosing the collection
The program SHALL accept a global option `-C DIR` or `--collection DIR` (also `--collection=DIR`) before the subcommand.
- With the option, `DIR` is the collection. When `DIR/orgsyndb.toml` does not exist, the program exits 1 with an error naming `DIR` and `orgsyndb.toml`; it does not search elsewhere.
- Without it, the collection is the first directory holding `orgsyndb.toml` among the working directory and its ancestors. When there is none, the program exits 1 with an error that names `-C` and `init`.

Only `export`, `validate`, `build`, `serve`, `pdf`, `new` and `clean` use a collection. `help`, `check-deps` and `init` never look for one.

#### Scenario: Found from a subdirectory
- **WHEN** a test runs `<app>/tools/orgsyndb validate` with the working directory set to `md/procedures/` of a collection copy
- **THEN** it exits 0, and the collection copy's `build/export/` exists afterwards

#### Scenario: No collection found
- **WHEN** a test runs `tools/orgsyndb build` in an empty temporary directory outside any collection
- **THEN** it exits 1, stderr contains `-C` and `init`, and the directory is still empty

#### Scenario: Option names a directory without a marker
- **WHEN** a test runs `tools/orgsyndb -C <empty temporary directory> build`
- **THEN** it exits 1, stderr contains `orgsyndb.toml`, and the directory is still empty

