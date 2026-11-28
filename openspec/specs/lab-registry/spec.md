# lab-registry Specification

## Purpose
Keep the lab's substances and vocabularies in the lab application, the registry the inventory, the tasks and planning refer to by foreign key: their models, pages, forms and admin, the snapshot that serves the registry as one JSON document, and the commands that load a snapshot and import a collection's compounds and vocabularies.
## Requirements
### Requirement: Substances
The `registry` package SHALL keep substances, each with a change history:

- `key`, required, at most 100 characters, matching `^[a-z0-9]+(-[a-z0-9]+)*$`, unique, and fixed once the substance is created;
- `name`, required, at most 200 characters, the name on an English site, and `name_de`, optional, at most 200 characters, the name on a German site;
- `short_name`, optional, at most 50 characters;
- `group`, a required term of the inventory groups (Vocabularies), protected;
- its chemical classes, terms of the chemical classes, kept as rows of `registry.SubstanceClass`, one per substance and class;
- `formula`, optional, at most 100 characters;
- `mw`, the molar mass in g/mol, optional, a decimal greater than zero with up to three places;
- `smiles`, optional text;
- `molfile`, optional text, a molfile with LF line endings, from which the lab draws the substance's structure image (Structure images);
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
The `vocabulary` package SHALL keep four vocabularies, each term with a change history: the chemical classes (`Stoffklassen`, `Chemical classes`), the inventory groups (`Bestandsgruppen`, `Inventory groups`) and the projects (`Projekte`, `Projects`), each a tree whose terms may name a `parent` of the same vocabulary, and the reaction types (`Reaktionstypen`, `Reaction types`), a flat list. A term holds `key`, required, at most 50 characters, matching `^[a-z0-9]+(-[a-z0-9]+)*$`, unique in its vocabulary and fixed once the term is created; `label`, required, at most 100 characters, the label on an English site; and `label_de`, optional, at most 100 characters, the label on a German site. A term shows as `label_de` on a German site when it has one, else `label`. A term is never its own parent nor filed under a term filed under it, which the form and the admin refuse with an error at the parent. A term that a substance, a procedure or another term refers to cannot be deleted.

#### Scenario: No loop
- **WHEN** the group `starting-materials` is filed under `purchased`, and a signed-in user posts the edit form of `purchased` with the parent `starting-materials`
- **THEN** the form shows an error at the parent and `purchased` keeps no parent

#### Scenario: Term in use
- **WHEN** a staff user deletes in the admin the chemical class of a substance
- **THEN** the admin refuses, naming the substance, and the term remains

### Requirement: Registry pages
The registry's pages SHALL need no sign-in:

- `/lab/registry/` lists the substances under the heading `Substanzen` (`Substances`), followed by their number, ordered by name regardless of case, in a table with the columns `Name`, `Schlüssel` (`Key`), `Kurzname` (`Short name`), `Bestandsgruppe` (`Inventory group`), `Stoffklassen` (`Chemical classes`), `Summenformel` (`Formula`), `Molmasse` (`Molar mass`) and `Artikelnr.` (`Article no.`), the name linking to the substance's page. The GET parameter `q`, from a search field labelled `Substanzen suchen` (`Search substances`), lists the substances in whose key, name, German name, short name or CAS number the text is found regardless of case. The GET parameters `group` and `class`, from the choices `Bestandsgruppe` (`Inventory group`) and `Stoffklasse` (`Chemical class`), each offering `Alle` (`All`) and the vocabulary's terms in the order of its page, list the substances filed under the term with that key or under a term filed below it, at any depth; a key that names no term lists none. The parameters narrow the list together, and the form keeps their values. For a signed-in user a link `Neue Substanz` (`New substance`) to the new-substance form.
- `/lab/registry/substances/<key>/` shows the substance's name as heading and its data in widgets (web-app "Widgets"):
  - `Verbindung` (`Compound`): when the substance has a structure image (Structure images), a `figure.structure` holding an `img` whose `src` is `/lab/registry/substances/<key>/structure.svg` and whose `alt` is `Strukturformel von <name>` (`Structure of <name>`), `<name>` its shown name; and its key, name, German name, short name, inventory group, linking to `/lab/registry/groups/`, chemical classes, formula, molar mass, SMILES, CAS number, note and article number, each `–` when it has none. The SMILES is followed by the copy button of the site's pages (site-theme "Site scripts").
  - `Gebinde` (`Containers`): its article's items, each with its article number and container size, linking to its page, and its number of containers, `<n> Gebinde` (`<n> containers`); `Chargen` (`Batches`): its batches, newest first as the batch list orders them, each linking to its page, with the amount in its open vessels by unit; and `Aufträge` (`Tasks`): its tasks, each linking to its page, with its state. Each reads `Keine` (`None`) when it has no row.
  - The following show only when they have a row:
    - `Hergestellt nach` (`Made by`): one row per specific procedure that is not withdrawn whose entry is not withdrawn and has the substance among its products, and one per such entry of a general procedure that is not withdrawn, by ID and then by entry position, each with a link `<ID> <title>` to `/procedures/<id>/`, the ID in lower case and the title the procedure's shown title; for an entry, `Eintrag <n>` (`entry <n>`), `<n>` its position; the product's yield, `<yield> %`, when it is known; and the procedure's status badge.
    - `Verwendet in` (`Used in`): one row per procedure that is not withdrawn with the substance among the substrates of an entry that is not withdrawn, by ID, with the link and the badge.
    - `Synthesewege` (`Sequences`): one row per sequence that is not withdrawn whose target is the substance, by ID, with a link `<ID> <title>` to `/sequences/<id>/`, the ID in lower case and the title the sequence's shown title.
  - `Herstellungswege` (`Routes`), a collapsible widget, open when the page loads, shown only when the substance has a route tree: the tree (synthesis-routes "Routes in the lab"), each step written as the link `<ID> <title>`, then ` · Eintrag <n>` (` · entry <n>`) for an entry, then ` · <yield> %` when the yield is known, then ` · ` and the badge, followed by the substances it starts from, each linking its substance page with its shown name and followed by the steps it keeps, or, when it is cut off, by ` · weitere Stufen auf ihrer Seite` (` · more steps on its page`).

  For a signed-in user the page has a link `Bearbeiten` (`Edit`) to the substance's edit form.
  A procedure's shown title is `title_de` on a German site when it has one, else `title`, and so is a sequence's. These links assume the site serves the latest accepted import's release: the builder publishes it on acceptance, and until it does, after a lost answer or for the demo data set's own import, a link may lead to a page the site does not serve yet. A yield is written as a number in the language's form, without a fractional part when it is whole. The status badge reads `Entwurf`, `Geprüft` or `Zurückgezogen` (`draft`, `checked`, `retired`), and a procedure without a status has none. An unknown key answers 404.
- `/lab/registry/<vocabulary>/`, `<vocabulary>` one of `chemical-classes`, `groups`, `projects` and `reaction-types`, lists the vocabulary's terms under its name as heading, each term after its parent and its parent's earlier children, in key order among siblings, indented by its depth, with the columns `Schlüssel` (`Key`), `Bezeichnung` (`Label`), `Bezeichnung deutsch` (`German label`), `Oberbegriff` (`Parent`), but no parent column for the reaction types, and `Verwendet` (`In use`), the number of records that name the term: substances for the chemical classes and the inventory groups, procedures of the collection, withdrawn ones included, for the projects and the reaction types; for a signed-in user, a link `Neuer Begriff` (`New term`) and each term's key linking to its edit form. Any other vocabulary answers 404.

#### Scenario: Substance list and search
- **WHEN** the demo data set is written and a test client requests `/lab/registry/?q=zimt`
- **THEN** the list holds `(E)-Zimtsäure` linking to `/lab/registry/substances/cinnamic-acid/`, with the article number `CH-0012`, and no substance whose names, key, short name and CAS number lack `zimt`

#### Scenario: Substance page
- **WHEN** the demo data set is written, an import of the demo collection was accepted, and a test client requests `/lab/registry/substances/cinnamic-acid/`
- **THEN** the page is headed `(E)-Zimtsäure`, its widget `Verbindung` holds the article number `CH-0012`, its widget `Gebinde` lists the article's items, and it links no path under `/compounds/`

#### Scenario: Procedures beside a substance
- **WHEN** the demo data set is written and a test client requests the pages of `acetylsalicylic-acid`, `salicylic-acid` and `1-biphenyl-4-yl-ethanol`
- **THEN** the first's widget `Hergestellt nach` holds one row: `OSDB-0002 Aspirin (Acetylsalicylsäure)` linking `/procedures/osdb-0002/`, no entry, `75 %` and the badge `Entwurf`; its widget `Synthesewege` a row linking `/sequences/seq-0001/` with `SEQ-0001` and the sequence's title; and its widget `Herstellungswege` the step `OSDB-0002`, under it `salicylic-acid` and `acetic-anhydride` linking their substance pages, and under `salicylic-acid` the step `OSDB-0001` with ` · 80 % · `
- **AND** the second's widget `Hergestellt nach` holds `OSDB-0001` and its widget `Verwendet in` `OSDB-0002`, and it has no widget `Herstellungswege`
- **AND** the third's widget `Hergestellt nach` holds `OSDB-0005` with `90 %`, then `OSDB-0009` with `Eintrag 1` and `90 %`

#### Scenario: Filters of the list
- **WHEN** the inventory group `final-products` is filed under `synthesised`, the substance `a` is filed under `final-products`, `b` under `synthesised` and `c` under `purchased`, and a test client requests `/lab/registry/?group=synthesised`, then `?group=final-products`, then `?group=nope`
- **THEN** the first lists `a` and `b`, the second `a` alone and the third none

#### Scenario: Uses of a reaction type
- **WHEN** the reaction type `esterification` is named by two procedures of the collection, one of them withdrawn, and by no other record, and a test client requests `/lab/registry/reaction-types/`
- **THEN** the row of `esterification` reads `2` under `Verwendet`

#### Scenario: Structure on the page
- **WHEN** the demo data set is written and a test client requests the pages of `isopentyl-acetate` and `new-compound-7`
- **THEN** the first's widget `Verbindung` holds one `figure.structure` whose `img` has the `src` `/lab/registry/substances/isopentyl-acetate/structure.svg` and the `alt` `Strukturformel von Isopentylacetat`, and the second has no `figure.structure`

#### Scenario: Empty widgets of a substance
- **WHEN** a test client requests the page of a substance without article, batch, task, procedure, sequence or route
- **THEN** its widgets `Gebinde`, `Chargen` and `Aufträge` each read `Keine`, and it has no widget `Hergestellt nach`, `Verwendet in`, `Synthesewege` or `Herstellungswege`

### Requirement: Registry forms
A signed-in user SHALL create and edit substances and terms through these forms, each saved with its change history:

- `/lab/registry/substances/new/` and `/lab/registry/substances/<key>/edit/`: the key, on the new form only; the name and German name; the short name; the inventory group, a choice of the inventory groups in the order of their page; the chemical classes, a check box per class in that order, at least one checked; the formula; the molar mass; the SMILES; the CAS number; the note; and the structure, a file field `Strukturformel (Molfile)` (`Structure (molfile)`), with, on the edit form of a substance that has a molfile, a check box `Strukturformel entfernen` (`Remove structure`). A chosen file becomes the substance's molfile, its line endings made LF; the checked box removes the molfile; with neither, the molfile stays. After saving, the substance's page opens.
- `/lab/registry/<vocabulary>/new/` and `/lab/registry/<vocabulary>/<key>/edit/`: the key, on the new form only; the label and German label; and, for the trees, the parent, a choice of the vocabulary's terms without the term itself and the terms filed under it, or none. After saving, the vocabulary's page opens.

A key that breaks its pattern or is taken, a molar mass that is not a number above zero, a CAS number of the wrong form, with a wrong check digit or taken, and a structure file that is larger than 1 MB, is not UTF-8 text, holds a NUL character, or from which RDKit reads no molecule with at least one atom, or that is chosen while the box is checked, show an error at their field and save nothing. A number may be entered with a decimal comma.

#### Scenario: New substance
- **WHEN** a signed-in user posts the new-substance form with the key `ethyl-acetate`, the name `Ethyl acetate`, the group `reagents`, the chemical class `esters` and the molar mass `88,11`
- **THEN** the substance exists with the molar mass 88.11, its history records its creation, and `/lab/registry/substances/ethyl-acetate/` opens

#### Scenario: No chemical class
- **WHEN** a signed-in user posts the new-substance form with no chemical class checked
- **THEN** the form shows an error at the chemical classes and no substance is created

#### Scenario: Bad key
- **WHEN** a signed-in user posts a new term of the projects with the key `Teaching 2`
- **THEN** the form shows an error at the key and no term is created

#### Scenario: The key group
- **WHEN** a signed-in user posts the new-substance form with the key `group` and otherwise the values of "New substance"
- **THEN** the substance `group` exists

#### Scenario: Structure from a file
- **WHEN** the demo data set is written and a signed-in user posts the edit form of `acetone` with a molfile of acetone whose lines end in CR LF
- **THEN** `acetone` has that molfile with LF line endings, and `/lab/registry/substances/acetone/structure.svg` answers 200

#### Scenario: Not a molfile
- **WHEN** the demo data set is written and a signed-in user posts the edit form of `new-compound-7`, which has no molfile, with a file holding `not a molfile`
- **THEN** the form shows an error at the structure and `new-compound-7` has no molfile

#### Scenario: Structure removed
- **WHEN** the demo data set is written and a signed-in user posts the edit form of `isopentyl-acetate` with the box `Strukturformel entfernen` checked
- **THEN** `isopentyl-acetate` has no molfile and `/lab/registry/substances/isopentyl-acetate/structure.svg` answers 404

#### Scenario: A file and the box together
- **WHEN** the demo data set is written and a signed-in user posts the edit form of `isopentyl-acetate` with a molfile of acetone and the box checked
- **THEN** the form shows an error at the structure and `isopentyl-acetate` keeps its molfile

### Requirement: Registry in the admin
The admin SHALL list the substances and the terms of each vocabulary for staff, with search by key and names or labels and the change history of each record. Keys are read-only once a record exists, and a term's parent is refused as in the forms.

#### Scenario: Key read-only
- **WHEN** a staff user opens the admin's change page of a substance
- **THEN** its key shows read-only

### Requirement: Snapshot
`registry.snapshot.build()` SHALL return the registry as a table that `json.dumps` serializes:

- `format`: `1`;
- `vocabularies`: a table of `chemical-classes`, `inventory-groups`, `projects` and `reaction-types`, the last three the groups, the projects and the reaction types, each a list of its terms, each a table of `key`, `label`, `label_de` and, for the trees, `parent`, the parent's key; ordered so that a parent precedes the terms filed under it and siblings follow in key order;
- `substances`: a list of the substances ordered by key, each a table of `key`, `name`, `name_de`, `short_name`, `group`, the group's key, `chemical_classes`, the classes' keys in key order, `formula`, `mw`, a number, `smiles`, `molfile`, `cas`, `note` and `article_number`, the number of its article;
- `accounts`: every account, active or not, ordered by user name, each a table of `username` and `name`, its display name (web-app "Accounts and sign-in");
- `notebooks`: every notebook, ordered by code, each a table of `code` and `user`, its owner's user name (lab-journal "Notebooks and entries");
- `import`: the latest accepted import of the collection (collection-import "Accepting an import"), a table of its `id`, `build`, `commit`, `snapshot`, `tooling`, `release` and `language`, or `null` when none was accepted;
- `digest`: the lowercase hexadecimal SHA-256 of the table without `digest` and `import`, serialized by `json.dumps` with `sort_keys=True`, `separators=(",", ":")` and `ensure_ascii=True`, encoded as UTF-8.

Empty or absent text, a missing molfile among it, a missing molar mass and a missing article number are `null`. `GET /lab/registry/snapshot.json` answers it as `application/json`, with no sign-in.

#### Scenario: Same registry, same digest
- **WHEN** a test loads the demo registry into two empty databases and builds the snapshot of each
- **THEN** both are equal, digests included, and changing one substance's note changes the digest

#### Scenario: Snapshot over HTTP
- **WHEN** the demo data set is written and a test client that is not signed in requests `/lab/registry/snapshot.json`
- **THEN** the answer is 200 with JSON whose `substances` include `cinnamic-acid` with `article_number` `CH-0012` and `mw` 148.16, whose `isopentyl-acetate` has a `molfile` string and `new-compound-7` the `molfile` `null`, and whose `vocabularies.inventory-groups` lists `purchased` before `starting-materials`

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

### Requirement: Structure images
The lab SHALL draw a substance's structure image from its molfile with RDKit whenever the substance is saved with a molfile, through a form, the admin or `registry_load`, and keep the drawing with the substance until its molfile changes or is removed; the drawing is not part of the substance's change history. The drawing is an SVG document whose root element has a `viewBox`, in black on a white background, with the molfile's atom coordinates, or with coordinates RDKit computes when every atom lies at the origin. Text from the molfile, such as an atom alias, shows as text and adds no element. A substance has a structure image exactly when it has a molfile.

`GET /lab/registry/substances/<key>/structure.svg` answers the kept drawing as `image/svg+xml`, with no sign-in, the headers `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'` and `X-Content-Type-Options: nosniff`, and without drawing it again. A substance without a molfile, and an unknown key, answer 404.

#### Scenario: The demo's structure
- **WHEN** the demo data set is written and a test client that is not signed in requests `/lab/registry/substances/isopentyl-acetate/structure.svg`, then the same path of `new-compound-7` and of `no-such-substance`
- **THEN** the first answers 200 as `image/svg+xml` with both headers, its body parses as XML whose root is an SVG `svg` element with a `viewBox`, and every colour it names is black or white; the other two answer 404
- **AND** every demo substance with a SMILES has a molfile, which RDKit reads as a molecule of the substance's `formula`, and `new-compound-7`, which has no SMILES, has none

#### Scenario: Drawn when saved
- **WHEN** a test saves a substance with a molfile, requests its image twice, saves it with another molfile and requests its image again
- **THEN** RDKit drew twice, once at each save, and the third answer differs from the first two, which are equal

#### Scenario: Not in the history
- **WHEN** a signed-in user gives a substance a molfile through its edit form
- **THEN** the substance's newest history record holds the molfile and no drawing

#### Scenario: Markup in an atom alias
- **WHEN** a signed-in user saves a substance with a molfile whose first atom has the alias `<script>alert(1)</script>`
- **THEN** its image parses as XML and has no `script` element

### Requirement: Live substance list
`/lab/registry/` SHALL implement live list updates (web-app "Live lists") as a main list (web-app "Main lists"):

- Its filter form (`#filters`) updates `#item-rows` in place with `morph:outerHTML`, each row carrying the stable `id="substance-row-<pk>"`. It updates `#substance-count`, `#item-head`, `#item-detail` and `#filter-selected` out of band with `#substance-count:morph,#item-head:morph,#item-detail:morph,#filter-selected:morph`. It uses `hx-get="/lab/registry/"`, `hx-push-url="true"`, `hx-sync="#main:replace"`, and scoped triggers (`submit`, `search from:#filter-q`, `input delay:200ms from:#filter-q`, `change target:select`). It keeps its `method="get"`, `action="/lab/registry/"`, and submit button for no-script use.
- Its column header links update `#item-rows` in place with `hx-sync="#main:replace"`, and out of band `#substance-count:morph,#item-head:morph,#item-detail:morph,#filters:morph`, keeping their `href` fallbacks.
- When `group` or `class` holds a non-empty key that names no vocabulary term, the corresponding `<select>` SHALL keep that key as a selected `<option>`, so later live edits to `q` keep the unknown filter until the user explicitly selects `All`.
- Its view returns the complete page for plain GET requests and HTMX history restores (`HX-Request: true` with `HX-History-Restore-Request: true`), and varies on `HX-Request` and `HX-History-Restore-Request`. On non-restore HTMX GET responses it sets `HX-Push-Url` to `/lab/registry/` with:
  - trimmed non-empty `q`, `group`, and `class` parameters;
  - `sort` and `dir=desc` as web-app "Main lists" states;
  - the resolved `selected` substance key, omitted when the list is empty.
- `/lab/registry/substances/<key>/detail/` sets `HX-Replace-Url` on HTMX responses to the list URL with the active filters and `selected` naming the substance.

#### Scenario: Live filtering and canonical URL on the substance list
- **WHEN** a test client requests `/lab/registry/?q=+zimt+&group=+final-products+&class=`, `/lab/registry/?group=nope`, `/lab/registry/?group=nope&q=zimt`, `/lab/registry/?group=&q=zimt&sort=formula&dir=desc`, and `/lab/registry/?q=+` with `HX-Request: true`
- **AND** it requests `/lab/registry/?q=zimt` once with both `HX-Request: true` and `HX-History-Restore-Request: true`, and once without HTMX headers
- **THEN** all responses return complete page markup (`html`, `#main`, table, filter form) and vary on `HX-Request` and `HX-History-Restore-Request`
- **AND** `#filters` carries `hx-get="/lab/registry/"`, `hx-push-url="true"`, `hx-sync="#main:replace"`, scoped triggers (`submit`, `search from:#filter-q`, `input delay:200ms from:#filter-q`, `change target:select`), `hx-target="#item-rows"`, `hx-select="#item-rows"`, `hx-swap="morph:outerHTML"`, and disjoint `hx-select-oob="#substance-count:morph,#item-head:morph,#item-detail:morph,#filter-selected:morph"`
- **AND** populated `#item-rows` rows carry `id="substance-row-<pk>"` and `data-item` with the substance's key
- **AND** `/lab/registry/?group=nope` and `/lab/registry/?group=nope&q=zimt` render an empty `#item-rows` and a `#substance-count` of `0`, and keep `nope` as the selected `<option>` in `select[name="group"]`, whereas `/lab/registry/?group=&q=zimt&sort=formula&dir=desc` lists matching substances
- **AND** the five ordinary HTMX responses set `HX-Push-Url` to `/lab/registry/?q=zimt&group=final-products&selected=<resolved>`, `/lab/registry/?group=nope`, `/lab/registry/?q=zimt&group=nope`, `/lab/registry/?q=zimt&sort=formula&dir=desc&selected=<resolved>`, and `/lab/registry/?selected=<resolved>`, while the history-restore and plain GET responses omit `HX-Push-Url`

### Requirement: Substance details
The substance list SHALL be a main list (web-app "Main lists") whose details of a substance, `/lab/registry/substances/<key>/detail/`, need no sign-in and show:

- its name as heading, linking to its page;
- when it has a structure image (Structure images), the `figure.structure` of its page;
- its key, short name, inventory group, chemical classes, formula, molar mass, CAS number and article number, each `–` when it has none;
- its article's items in a table with the columns `Gebinde` and `Bestand` (`Container`, `Stock`), each with its article number and container size, linking to its page, and its number of containers;
- its batches, newest first as the batch list orders them, in a table with the columns `Charge`, `Datum` and `Bestand` (`Batch`, `Date`, `Stock`), each linking to its page, with its date and the amount in its open vessels by unit;
- its tasks in a table with the columns `Nr.` and `Status` (`No.`, `State`), each linking to its page, with its state;
- for each of the three tables that would have no row, `Keine` (`None`) in its place;
- a link `Substanzseite öffnen` (`Open substance page`) to the substance's page.

For a signed-in user the details also link `Bearbeiten` (`Edit`) to the substance's edit form.

#### Scenario: Details of a substance
- **WHEN** the demo data set is written and a test client requests `/lab/registry/?selected=cinnamic-acid`
- **THEN** `#item-detail` is headed `(E)-Zimtsäure` linking to `/lab/registry/substances/cinnamic-acid/`, shows the article number `CH-0012`, lists the article's items and the substance's batches, each linking to its page, and links `Substanzseite öffnen`

#### Scenario: Details of a bare substance
- **WHEN** a test client requests the substance list with `selected` naming a substance without article, batch or task
- **THEN** its details read `Keine` in place of each of the three tables

