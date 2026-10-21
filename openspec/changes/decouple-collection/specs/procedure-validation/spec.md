## MODIFIED Requirements

<!-- Reason: structure images belong to a collection, not to the
application (design.md D9). The vocabulary stays with the application. -->

### Requirement: Default paths resolve from the script location
When `--vocabulary` is omitted, the validator SHALL use `<app>/site/data/reaction_types.toml`, where `<app>` is the parent of the directory containing the resolved `validate.py`, independent of the working directory. When `--static-dir` is omitted, it SHALL use `static` in the working directory, the location of a collection's static files when run from the collection's root. A static directory that does not exist is not a configuration error; it only makes every `structure_image` unresolvable.

#### Scenario: Run from an unrelated working directory
- **WHEN** a test runs `<app>/tools/validate.py` as a subprocess, with `cwd` set to an empty temporary directory and without `--vocabulary`, on a temporary content root holding one procedure whose `reaction_types` is `["reductive-amination"]`
- **AND** `reductive-amination` is a key of the shipped vocabulary but not of `tests/fixtures/reaction_types.toml`
- **THEN** it reports no `reaction_types` problem and exits 0

#### Scenario: Default static directory is the working directory's
- **WHEN** a test runs `<app>/tools/validate.py` without `--static-dir`, with `cwd` set to a temporary directory holding `static/structures/osdb-0100.svg` and a content root whose one procedure sets `structure_image = "structures/osdb-0100.svg"`
- **THEN** it reports no `structure_image` problem and exits 0
