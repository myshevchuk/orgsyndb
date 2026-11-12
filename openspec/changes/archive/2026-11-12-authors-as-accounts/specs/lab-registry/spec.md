## MODIFIED Requirements

### Requirement: Snapshot
`registry.snapshot.build()` SHALL return the registry as a table that `json.dumps` serializes:

- `format`: `1`;
- `vocabularies`: a table of `chemical-classes`, `inventory-groups`, `projects` and `reaction-types`, the last three the groups, the projects and the reaction types, each a list of its terms, each a table of `key`, `label`, `label_de` and, for the trees, `parent`, the parent's key; ordered so that a parent precedes the terms filed under it and siblings follow in key order;
- `substances`: a list of the substances ordered by key, each a table of `key`, `name`, `name_de`, `short_name`, `group`, the group's key, `chemical_classes`, the classes' keys in key order, `formula`, `mw`, a number, `smiles`, `cas`, `note` and `article_number`, the number of its article;
- `accounts`: every account, active or not, ordered by user name, each a table of `username` and `name`, its display name (web-app "Accounts and sign-in");
- `import`: the latest accepted import of the collection (collection-import "Accepting an import"), a table of its `id`, `build`, `commit`, `snapshot`, `tooling`, `release` and `language`, or `null` when none was accepted;
- `digest`: the lowercase hexadecimal SHA-256 of the table without `digest` and `import`, serialized by `json.dumps` with `sort_keys=True`, `separators=(",", ":")` and `ensure_ascii=True`, encoded as UTF-8.

Empty or absent text, a missing molar mass and a missing article number are `null`. `GET /lab/registry/snapshot.json` answers it as `application/json`, with no sign-in.

#### Scenario: Same registry, same digest
- **WHEN** a test loads the demo registry into two empty databases and builds the snapshot of each
- **THEN** both are equal, digests included, and changing one substance's note changes the digest

#### Scenario: Snapshot over HTTP
- **WHEN** the demo data set is written and a test client that is not signed in requests `/lab/registry/snapshot.json`
- **THEN** the answer is 200 with JSON whose `substances` include `cinnamic-acid` with `article_number` `CH-0012` and `mw` 148.16, and whose `vocabularies.inventory-groups` lists `purchased` before `starting-materials`

#### Scenario: An import changes no digest
- **WHEN** the demo data set is written, a test takes the snapshot, an import of the demo collection is accepted, and the test takes the snapshot again
- **THEN** both have the same `digest`, the first has `import` `null`, and the second's `import` names the accepted import's id, commit and release

#### Scenario: Accounts in the snapshot
- **WHEN** the demo data set is written and a test takes the snapshot, changes the last name of `tbauer`, and takes it again
- **THEN** the first lists the five demo accounts with `klehmann` named `Katrin Lehmann`, and the two digests differ

### Requirement: Loading a registry
`manage.py registry_load FILE` SHALL fill an empty registry from the snapshot in FILE, in one transaction: the terms of each vocabulary in their order, the substances with their classes, and an article with its number for each substance that has `article_number`, each with a creation in its history, made at the time it is loaded by the user the loading names, the command naming none. It ignores `digest`, `import` and `accounts`, which it does not create. It exits 1 with a message and changes nothing when the database holds a substance or a term, when the format is not `1`, when a term or substance names a key that does not exist, or when a value breaks a rule the forms check; the message names the record and the field. On success it prints how many terms, substances and articles it wrote.

#### Scenario: Round trip
- **WHEN** a test loads `webapp/demo/registry.json` into an empty database and builds the snapshot
- **THEN** the snapshot equals the file but for `digest`, `import`, which is `null`, and `accounts`, which lists the database's accounts

#### Scenario: Registry not empty
- **WHEN** a substance exists and `registry_load` runs on the demo registry
- **THEN** it exits 1 with a message, and the database holds that one substance
