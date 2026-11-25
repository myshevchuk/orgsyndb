## MODIFIED Requirements

### Requirement: Command-line interface
The validator SHALL be the executable file `tools/validate.py`, invoked as `validate.py [--settings FILE] [--static-dir DIR] [--registry FILE] [--sequences DIR] CONTENT_ROOT...`, and it SHALL use no third-party Python packages: it imports only from the Python standard library and local modules under `tools/`.
- Each positional `CONTENT_ROOT` is a directory of procedure Markdown files with `+++` TOML front matter, such as an ox-hugo export directory or `md/procedures/`.
- At least one content root is required.
- `--sequences` names the directory of synthesis sequences (synthesis-sequences "Sequence files"). The validator checks every sequence in it against the procedures of the content roots and the registry.
- `--registry` names the collection's registry, a snapshot file (compound-registry "Registry checks"). The validator resolves every compound key of the procedures and sequences against its substances, and takes the reaction types and the vocabularies of procedure fields from it.
- `--settings` names the collection's settings file, its `orgsyndb.toml` (collection "Collection layout"). The validator applies the rules that requirement states for `format` and the top-level keys, reads only `fields` beyond them, checks the procedure declarations against the registry's vocabularies (procedure-fields "Procedure field declarations"), and checks every procedure of the content roots against the procedure fields (procedure-fields "Procedure field values"). The validator takes no option naming a vocabulary or a compound directory.
- It reads no Org source. An Org procedure reaches it only as its export, and the export checks the Org source itself (org-export "Org sources and their problems").
- The module also exposes `main(argv: Sequence[str] | None = None) -> int`, which returns the exit status.

#### Scenario: No roots given
- **WHEN** the validator runs with no `CONTENT_ROOT`
- **THEN** it exits 2 and prints an error to stderr

#### Scenario: Org root option is refused
- **WHEN** the validator runs with `--org-root tests/fixtures/valid/org tests/fixtures/valid/md`
- **THEN** it exits 2, stderr contains `--org-root`, and stdout is empty

#### Scenario: Vocabulary and compound options are refused
- **WHEN** the validator runs with `--vocabulary reaction-types.toml tests/fixtures/valid/md`, and separately with `--compounds tests/fixtures tests/fixtures/valid/md`
- **THEN** each exits 2, stderr contains `--vocabulary` and `--compounds` respectively, and stdout is empty

#### Scenario: Root is not a directory
- **WHEN** the validator runs on the content root `tests/fixtures/does-not-exist`
- **THEN** it exits 2, and stderr contains `validate.py: error:` and `not a directory`

#### Scenario: Only standard-library imports
- **WHEN** a test parses `tools/validate.py` with `ast` and collects the top-level module names of every absolute `import` and `from ... import` statement
- **THEN** every name is in `sys.stdlib_module_names` or is a local module or package under `tools/`
