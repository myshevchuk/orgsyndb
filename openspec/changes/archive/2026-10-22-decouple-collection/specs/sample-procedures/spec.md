## ADDED Requirements

### Requirement: Demo collection
The sample procedures SHALL form the demo collection `examples/demo/` of the application, a complete collection as the `collection` capability defines it, with the structure images in `examples/demo/static/structures/`. Every path that this capability names under `org/procedures/` or `md/procedures/` is relative to `examples/demo/`. The application's own root holds no `org/`, `md/` or `site/static/` directory.

#### Scenario: Samples live in the demo collection
- **WHEN** a test inspects the application
- **THEN** `examples/demo/orgsyndb.toml` exists, `examples/demo/org/procedures/OSDB-0001-salicylic-acid.org` and `examples/demo/md/procedures/OSDB-0002-aspirin.md` exist, and neither `org/`, `md/` nor `site/static/` exists at the application root

## MODIFIED Requirements

<!-- Reason: the shipped tree is now the demo collection, built with the
new program. -->

### Requirement: Samples validate and export cleanly
The sample procedures SHALL produce no validator problem line at all, neither error nor warning, both as sources and after export.

#### Scenario: Clean validation of the shipped tree
- **WHEN** an integration test runs `tools/orgsyndb -C <copy of examples/demo> validate`
- **THEN** it exits 0, and no line of the form `<path>:<field>: <severity>: <message>` is printed
