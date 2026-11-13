# lab-registry Specification

## Purpose
Keep the lab's substances and vocabularies in the lab application, the registry the inventory, the tasks and planning refer to by foreign key: their models, pages, forms and admin, the snapshot that serves the registry as one JSON document, and the commands that load a snapshot and import a collection's compounds and vocabularies.
## Requirements
### Requirement: Substances
The `registry` package SHALL keep substances, each with a change history:

- `key`, required, at most 100 characters, matching `^[a-z0-9]+(-[a-z0-9]+)*$`, unique, and fixed once the substance is created;
- `name`, required, at most 200 characters, the name on an English site, and `name_de`, optional, at most 200 characters, the name on a German site;
- `short_name`, optional, at most 50 characters;
- `group`, a required term of the groups (Vocabularies), protected;
- its chemical classes, terms of the chemical classes, kept as rows of `registry.SubstanceClass`, one per substance and class;
- `formula`, optional, at most 100 characters;
- `mw`, the molar mass in g/mol, optional, a decimal greater than zero with up to three places;
- `smiles`, optional text;
- `cas`, optional, matching `^\d{2,7}-\d{2}-\d$` with a check digit that verifies, unique among substances when given;
- `note`, optional text.

A substance is a compound, or a mixture or solution taken as one. Its name is `name_de` when the language (web-app "Interface language") is German and it has one, else `name`. A substance cannot be deleted while a record refers to it.

#### Scenario: Name by language
- **WHEN** a substance has `name` `(E)-Cinnamic acid` and `name_de` `(E)-Zimtsäure`, and another only `name` `Acetophenone`
- **THEN** on a German site they show as `(E)-Zimtsäure` and `Acetophenone`, and on an English site as `(E)-Cinnamic acid` and `Acetophenone`

#### Scenario: Key fixed
- **WHEN** a signed-in user posts the edit form of the substance `cinnamic-acid` with the key `zimtsaeure`
- **THEN** the substance keeps the key `cinnamic-acid`

#### Scenario: CAS number checked
- **WHEN** a signed-in user posts a new substance with the CAS number `140-10-4`, and then one with `140-10-3` while another substance has it
- **THEN** each form shows an error at the CAS number and no substance is created

### Requirement: Vocabularies
The `vocabulary` package SHALL keep four vocabularies, each term with a change history: the chemical classes (`Stoffklassen`, `Chemical classes`), the groups (`Gruppen`, `Groups`) and the projects (`Projekte`, `Projects`), each a tree whose terms may name a `parent` of the same vocabulary, and the reaction types (`Reaktionstypen`, `Reaction types`), a flat list. A term holds `key`, required, at most 50 characters, matching `^[a-z0-9]+(-[a-z0-9]+)*$`, unique in its vocabulary and fixed once the term is created; `label`, required, at most 100 characters, the label on an English site; and `label_de`, optional, at most 100 characters, the label on a German site. A term shows as `label_de` on a German site when it has one, else `label`. A term is never its own parent nor filed under a term filed under it, which the form and the admin refuse with an error at the parent. A term that a substance or another term refers to cannot be deleted.

#### Scenario: No loop
- **WHEN** the group `starting-materials` is filed under `purchased`, and a signed-in user posts the edit form of `purchased` with the parent `starting-materials`
- **THEN** the form shows an error at the parent and `purchased` keeps no parent

#### Scenario: Term in use
- **WHEN** a staff user deletes in the admin the chemical class of a substance
- **THEN** the admin refuses, naming the substance, and the term remains

### Requirement: Registry pages
The registry's pages SHALL need no sign-in:

- `/lab/registry/` lists the substances under the heading `Substanzen` (`Substances`), followed by their number, ordered by name regardless of case, in a table with the columns `Name`, `Schlüssel` (`Key`), `Kurzname` (`Short name`), `Gruppe` (`Group`), `Stoffklassen` (`Chemical classes`), `Summenformel` (`Formula`), `Molmasse` (`Molar mass`) and `Artikelnr.` (`Article no.`), the name linking to the substance's page. The GET parameter `q`, from a search field labelled `Substanzen suchen` (`Search substances`), lists the substances in whose key, name, German name, short name or CAS number the text is found regardless of case. Above the table, links lead to the four vocabularies, as `Laborjournale` (`Lab notebooks`) to `/lab/journal/` (lab-journal "Journal pages"), and, as `Importe der Sammlung` (`Collection imports`), to `/lab/collection/` (collection-import "Imports page"), and for a signed-in user a link `Neue Substanz` (`New substance`) to the new-substance form.
- `/lab/registry/substances/<key>/` shows the substance's name as heading and its key, names, short name, group, chemical classes, formula, molar mass, SMILES, CAS number, note and article number, each `–` when it has none; when an import of the collection was accepted no earlier than the substance was created, a link `In der Sammlung` (`In the collection`) to `/compounds/<key>/`, which assumes the site serves that import's release: the builder publishes it on acceptance, and until it does, after a lost answer or for the demo data set's own import, the link may lead to a page the site does not serve yet; for a signed-in user a link `Bearbeiten` (`Edit`) to its edit form; and the sections `Gebinde` (`Containers`), its article's items linking to their pages, `Bulk-Lose` (`Bulk lots`), its open lots linking to theirs, and `Aufträge` (`Tasks`), its tasks linking to theirs, each `Keine` (`None`) when empty. An unknown key answers 404.
- `/lab/registry/<vocabulary>/`, `<vocabulary>` one of `chemical-classes`, `groups`, `projects` and `reaction-types`, lists the vocabulary's terms under its name as heading, each term after its parent and its parent's earlier children, in key order among siblings, indented by its depth, with the columns `Schlüssel` (`Key`), `Bezeichnung` (`Label`), `Bezeichnung deutsch` (`German label`), `Oberbegriff` (`Parent`), but no parent column for the reaction types, and `Verwendet` (`In use`), the number of substances that name the term; for a signed-in user, a link `Neuer Begriff` (`New term`) and each term's key linking to its edit form. Any other vocabulary answers 404.

#### Scenario: Substance list and search
- **WHEN** the demo data set is written and a test client requests `/lab/registry/?q=zimt`
- **THEN** the list holds `(E)-Zimtsäure` linking to `/lab/registry/substances/cinnamic-acid/`, with the article number `CH-0012`, and no substance whose names, key, short name and CAS number lack `zimt`

#### Scenario: Substance page
- **WHEN** the demo data set is written, an import of the demo collection was accepted, and a test client requests `/lab/registry/substances/cinnamic-acid/`
- **THEN** the page is headed `(E)-Zimtsäure`, links `In der Sammlung` to `/compounds/cinnamic-acid/`, and lists the article's items under `Gebinde`

#### Scenario: Not in the collection
- **WHEN** the demo data set is written, the substance `ethyl-acetate`, named `Ethylacetat`, is added to the registry after the latest accepted import, and a test client requests `/lab/registry/substances/ethyl-acetate/`
- **THEN** the page is headed `Ethylacetat` and has no link `In der Sammlung`

### Requirement: Registry forms
A signed-in user SHALL create and edit substances and terms through these forms, each saved with its change history:

- `/lab/registry/substances/new/` and `/lab/registry/substances/<key>/edit/`: the key, on the new form only; the name and German name; the short name; the group, a choice of the groups in the order of their page; the chemical classes, a check box per class in that order, at least one checked; the formula; the molar mass; the SMILES; the CAS number; and the note. After saving, the substance's page opens.
- `/lab/registry/<vocabulary>/new/` and `/lab/registry/<vocabulary>/<key>/edit/`: the key, on the new form only; the label and German label; and, for the trees, the parent, a choice of the vocabulary's terms without the term itself and the terms filed under it, or none. After saving, the vocabulary's page opens.

A key that breaks its pattern or is taken, the substance key `group`, which names the directory of the site's compound tabs (site-catalogue "Compound tabs"), a molar mass that is not a number above zero, and a CAS number of the wrong form, with a wrong check digit or taken, show an error at their field and save nothing. A number may be entered with a decimal comma.

#### Scenario: New substance
- **WHEN** a signed-in user posts the new-substance form with the key `ethyl-acetate`, the name `Ethyl acetate`, the group `reagents`, the chemical class `esters` and the molar mass `88,11`
- **THEN** the substance exists with the molar mass 88.11, its history records its creation, and `/lab/registry/substances/ethyl-acetate/` opens

#### Scenario: No chemical class
- **WHEN** a signed-in user posts the new-substance form with no chemical class checked
- **THEN** the form shows an error at the chemical classes and no substance is created

#### Scenario: Bad key
- **WHEN** a signed-in user posts a new term of the projects with the key `Teaching 2`
- **THEN** the form shows an error at the key and no term is created

#### Scenario: The key of the compound tabs
- **WHEN** a signed-in user posts the new-substance form with the key `group`
- **THEN** the form shows an error at the key and no substance is created

### Requirement: Registry in the admin
The admin SHALL list the substances and the terms of each vocabulary for staff, with search by key and names or labels and the change history of each record. Keys are read-only once a record exists, and a term's parent is refused as in the forms.

#### Scenario: Key read-only
- **WHEN** a staff user opens the admin's change page of a substance
- **THEN** its key shows read-only

### Requirement: Snapshot
`registry.snapshot.build()` SHALL return the registry as a table that `json.dumps` serializes:

- `format`: `1`;
- `vocabularies`: a table of `chemical-classes`, `inventory-groups`, `projects` and `reaction-types`, the last three the groups, the projects and the reaction types, each a list of its terms, each a table of `key`, `label`, `label_de` and, for the trees, `parent`, the parent's key; ordered so that a parent precedes the terms filed under it and siblings follow in key order;
- `substances`: a list of the substances ordered by key, each a table of `key`, `name`, `name_de`, `short_name`, `group`, the group's key, `chemical_classes`, the classes' keys in key order, `formula`, `mw`, a number, `smiles`, `cas`, `note` and `article_number`, the number of its article;
- `accounts`: every account, active or not, ordered by user name, each a table of `username` and `name`, its display name (web-app "Accounts and sign-in");
- `notebooks`: every notebook, ordered by code, each a table of `code` and `user`, its owner's user name (lab-journal "Notebooks and entries");
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
- **WHEN** the demo registry, accounts and notebooks are written and no import exists, a test takes the snapshot, an import of the demo collection is accepted, and the test takes the snapshot again
- **THEN** both have the same `digest`, the first has `import` `null`, and the second's `import` names the accepted import's id, commit and release

#### Scenario: Accounts in the snapshot
- **WHEN** the demo data set is written and a test takes the snapshot, changes the last name of `tbauer`, and takes it again
- **THEN** the first lists the five demo accounts with `klehmann` named `Katrin Lehmann`, and the two digests differ

#### Scenario: Notebooks in the snapshot
- **WHEN** the demo data set is written and a test takes the snapshot, changes the note of `AE-2`, gives `AE-2` the owner `tbauer`, and takes it again
- **THEN** the first lists `AE-1`, `AE-2`, `CE-1` and `CE-3` with `AE-2` of `aschmidt`, and the second `AE-2` of `tbauer`, with another digest

### Requirement: Loading a registry
`manage.py registry_load FILE` SHALL fill an empty registry from the snapshot in FILE, in one transaction: the terms of each vocabulary in their order, the substances with their classes, and an article with its number for each substance that has `article_number`, each with a creation in its history, made at the time it is loaded by the user the loading names, the command naming none. It ignores `digest`, `import`, `accounts` and `notebooks`, which it does not create. It exits 1 with a message and changes nothing when the database holds a substance or a term, when the format is not `1`, when a term or substance names a key that does not exist, or when a value breaks a rule the forms check; the message names the record and the field. On success it prints how many terms, substances and articles it wrote.

#### Scenario: Round trip
- **WHEN** a test loads `webapp/demo/registry.json` into an empty database and builds the snapshot
- **THEN** the snapshot equals the file but for `digest`, `import`, which is `null`, `accounts`, which lists the database's accounts, and `notebooks`, which is empty

#### Scenario: Registry not empty
- **WHEN** a substance exists and `registry_load` runs on the demo registry
- **THEN** it exits 1 with a message, and the database holds that one substance

### Requirement: Importing a collection's registry
`manage.py registry_import COLLECTION` SHALL build a snapshot from the collection directory COLLECTION and load it as `registry_load` does:

- the vocabularies from `vocabularies/chemical-classes.toml`, `inventory-groups.toml`, `projects.toml` and `reaction-types.toml`, each table name a key with its `label`, `label_de` and `parent`; a missing file gives an empty vocabulary;
- a substance for each `compounds/<key>.toml`, with `name`, `name_de`, `formula`, `mw`, `smiles` and `cas`, and the collection's declared fields `short_name`, `chemical_class` (the classes), `group` and `item_number` (the article number).

It writes to stderr one warning naming the other keys it leaves out, such as `structure_image`, `in_house` and `stock`, with how many compounds set each. A compound without a group or a chemical class, or a file that cannot be read, is an error naming the file, and nothing is loaded.

#### Scenario: A collection in the old layout
- **WHEN** `registry_import` runs into an empty database on `webapp/tests/fixtures/old-layout/`, a collection in the layout collections had before they named a registry: the demo collection's former `orgsyndb.toml`, `compounds/` and `vocabularies/`
- **THEN** the registry holds its 20 compounds as substances, `cinnamic-acid` with the group `final-products`, the chemical class `carboxylic-acids` and an article numbered `CH-0012`, and stderr names `in_house` and `stock`

