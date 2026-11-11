## MODIFIED Requirements

### Requirement: Registry pages
The registry's pages SHALL need no sign-in:

- `/lab/registry/` lists the substances under the heading `Substanzen` (`Substances`), followed by their number, ordered by name regardless of case, in a table with the columns `Name`, `Schlüssel` (`Key`), `Kurzname` (`Short name`), `Gruppe` (`Group`), `Stoffklassen` (`Chemical classes`), `Summenformel` (`Formula`), `Molmasse` (`Molar mass`) and `Artikelnr.` (`Article no.`), the name linking to the substance's page. The GET parameter `q`, from a search field labelled `Substanzen suchen` (`Search substances`), lists the substances in whose key, name, German name, short name or CAS number the text is found regardless of case. Above the table, links lead to the four vocabularies and, as `Importe der Sammlung` (`Collection imports`), to `/lab/collection/` (collection-import "Imports page"), and for a signed-in user a link `Neue Substanz` (`New substance`) to the new-substance form.
- `/lab/registry/substances/<key>/` shows the substance's name as heading and its key, names, short name, group, chemical classes, formula, molar mass, SMILES, CAS number, note and article number, each `–` when it has none; when the collection index lists the key (web-app "Collection index"), a link `In der Sammlung` (`In the collection`) to `/compounds/<key>/`; for a signed-in user a link `Bearbeiten` (`Edit`) to its edit form; and the sections `Gebinde` (`Containers`), its article's items linking to their pages, `Bulk-Lose` (`Bulk lots`), its open lots linking to theirs, and `Aufträge` (`Tasks`), its tasks linking to theirs, each `Keine` (`None`) when empty. An unknown key answers 404.
- `/lab/registry/<vocabulary>/`, `<vocabulary>` one of `chemical-classes`, `groups`, `projects` and `reaction-types`, lists the vocabulary's terms under its name as heading, each term after its parent and its parent's earlier children, in key order among siblings, indented by its depth, with the columns `Schlüssel` (`Key`), `Bezeichnung` (`Label`), `Bezeichnung deutsch` (`German label`), `Oberbegriff` (`Parent`), but no parent column for the reaction types, and `Verwendet` (`In use`), the number of substances that name the term; for a signed-in user, a link `Neuer Begriff` (`New term`) and each term's key linking to its edit form. Any other vocabulary answers 404.

#### Scenario: Substance list and search
- **WHEN** the demo data set is written and a test client requests `/lab/registry/?q=zimt`
- **THEN** the list holds `(E)-Zimtsäure` linking to `/lab/registry/substances/cinnamic-acid/`, with the article number `CH-0012`, and no substance whose names, key, short name and CAS number lack `zimt`

#### Scenario: Substance page
- **WHEN** the demo data set is written, the index lists the key `cinnamic-acid`, and a test client requests `/lab/registry/substances/cinnamic-acid/`
- **THEN** the page is headed `(E)-Zimtsäure`, links `In der Sammlung` to `/compounds/cinnamic-acid/`, and lists the article's items under `Gebinde`

#### Scenario: Not in the collection
- **WHEN** the demo data set is written, the substance `ethyl-acetate`, named `Ethylacetat`, is added to the registry after the collection index was written, and a test client requests `/lab/registry/substances/ethyl-acetate/`
- **THEN** the page is headed `Ethylacetat` and has no link `In der Sammlung`

### Requirement: Snapshot
`registry.snapshot.build()` SHALL return the registry as a table that `json.dumps` serializes:

- `format`: `1`;
- `vocabularies`: a table of `chemical-classes`, `inventory-groups`, `projects` and `reaction-types`, the last three the groups, the projects and the reaction types, each a list of its terms, each a table of `key`, `label`, `label_de` and, for the trees, `parent`, the parent's key; ordered so that a parent precedes the terms filed under it and siblings follow in key order;
- `substances`: a list of the substances ordered by key, each a table of `key`, `name`, `name_de`, `short_name`, `group`, the group's key, `chemical_classes`, the classes' keys in key order, `formula`, `mw`, a number, `smiles`, `cas`, `note` and `article_number`, the number of its article;
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

### Requirement: Loading a registry
`manage.py registry_load FILE` SHALL fill an empty registry from the snapshot in FILE, in one transaction: the terms of each vocabulary in their order, the substances with their classes, and an article with its number for each substance that has `article_number`, each with a creation in its history, made at the time it is loaded by the user the loading names, the command naming none. It ignores `digest` and `import`. It exits 1 with a message and changes nothing when the database holds a substance or a term, when the format is not `1`, when a term or substance names a key that does not exist, or when a value breaks a rule the forms check; the message names the record and the field. On success it prints how many terms, substances and articles it wrote.

#### Scenario: Round trip
- **WHEN** a test loads `webapp/demo/registry.json` into an empty database and builds the snapshot
- **THEN** the snapshot equals the file but for `digest` and `import`, which is `null`

#### Scenario: Registry not empty
- **WHEN** a substance exists and `registry_load` runs on the demo registry
- **THEN** it exits 1 with a message, and the database holds that one substance
