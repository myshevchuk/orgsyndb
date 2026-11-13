## MODIFIED Requirements

### Requirement: Default paths come from the working directory
When `--static-dir` is omitted, the validator SHALL use `static` in the working directory, the location of a collection's static files when run from the collection's root. A static directory that does not exist is not a configuration error; it only makes every image path a procedure names unresolvable. When `--registry` is omitted, it SHALL use `build/registry.json` in the working directory, where the collection's tools leave the registry they read (compound-registry "Reading the registry"); a registry file that does not exist is a configuration error (Registry errors are configuration errors). When `--sequences` is omitted, it SHALL use `md/sequences` in the working directory; a sequences directory that does not exist holds no sequence. When `--settings` is omitted, it SHALL use `orgsyndb.toml` in the working directory, the settings file of a collection when run from the collection's root. A settings file that does not exist declares no field when `--settings` is omitted; a settings file that `--settings` names and that does not exist is a configuration error (procedure-fields "Procedure declaration errors are configuration errors").

#### Scenario: Default static and registry directories are the working directory's
- **WHEN** a test runs `<app>/tools/validate.py` without `--static-dir` and `--registry`, with `cwd` set to a temporary directory holding `static/structures/ethyl-acetate.svg`, `build/registry.json`, a copy of the fixture registry, and a content root whose one procedure is the baseline
- **THEN** it reports no problem and exits 0

#### Scenario: Missing registry
- **WHEN** a fixture run on `baseline` names `--registry tests/fixtures/no-such-registry.json`
- **THEN** it exits 2, stdout is empty, and stderr contains `validate.py: error:` and `no-such-registry.json`

#### Scenario: Default settings file is the working directory's
- **WHEN** a test runs `<app>/tools/validate.py` without `--settings`, with `cwd` set to a temporary directory holding an `orgsyndb.toml` that declares the required procedure text field `sample_code`, with `--registry <app>/tests/fixtures/registry.json` and `--static-dir <app>/tests/fixtures/static`, on the content root `<app>/tests/fixtures/baseline`
- **THEN** it exits 1, and its one stdout line has field `sample_code` and contains `required field missing`
