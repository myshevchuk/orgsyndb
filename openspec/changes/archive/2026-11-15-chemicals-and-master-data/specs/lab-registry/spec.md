## MODIFIED Requirements

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

- `/lab/registry/` lists the substances under the heading `Substanzen` (`Substances`), followed by their number, ordered by name regardless of case, in a table with the columns `Name`, `Schlüssel` (`Key`), `Kurzname` (`Short name`), `Bestandsgruppe` (`Inventory group`), `Stoffklassen` (`Chemical classes`), `Summenformel` (`Formula`), `Molmasse` (`Molar mass`) and `Artikelnr.` (`Article no.`), the name linking to the substance's page. The GET parameter `q`, from a search field labelled `Substanzen suchen` (`Search substances`), lists the substances in whose key, name, German name, short name or CAS number the text is found regardless of case. For a signed-in user a link `Neue Substanz` (`New substance`) to the new-substance form.
- `/lab/registry/substances/<key>/` shows the substance's name as heading and its key, names, short name, inventory group, chemical classes, formula, molar mass, SMILES, CAS number, note and article number, each `–` when it has none; when an import of the collection was accepted no earlier than the substance was created, a link `In der Sammlung` (`In the collection`) to `/compounds/<key>/`, which assumes the site serves that import's release: the builder publishes it on acceptance, and until it does, after a lost answer or for the demo data set's own import, the link may lead to a page the site does not serve yet; for a signed-in user a link `Bearbeiten` (`Edit`) to its edit form; and the sections `Gebinde` (`Containers`), its article's items linking to their pages, `Bulk-Lose` (`Bulk lots`), its open lots linking to theirs, and `Aufträge` (`Tasks`), its tasks linking to theirs, each `Keine` (`None`) when empty. An unknown key answers 404.
- `/lab/registry/<vocabulary>/`, `<vocabulary>` one of `chemical-classes`, `groups`, `projects` and `reaction-types`, lists the vocabulary's terms under its name as heading, each term after its parent and its parent's earlier children, in key order among siblings, indented by its depth, with the columns `Schlüssel` (`Key`), `Bezeichnung` (`Label`), `Bezeichnung deutsch` (`German label`), `Oberbegriff` (`Parent`), but no parent column for the reaction types, and `Verwendet` (`In use`), the number of records that name the term: substances for the chemical classes and the inventory groups, procedures of the collection, withdrawn ones included, for the projects and the reaction types; for a signed-in user, a link `Neuer Begriff` (`New term`) and each term's key linking to its edit form. Any other vocabulary answers 404.

#### Scenario: Substance list and search
- **WHEN** the demo data set is written and a test client requests `/lab/registry/?q=zimt`
- **THEN** the list holds `(E)-Zimtsäure` linking to `/lab/registry/substances/cinnamic-acid/`, with the article number `CH-0012`, and no substance whose names, key, short name and CAS number lack `zimt`

#### Scenario: Substance page
- **WHEN** the demo data set is written, an import of the demo collection was accepted, and a test client requests `/lab/registry/substances/cinnamic-acid/`
- **THEN** the page is headed `(E)-Zimtsäure`, links `In der Sammlung` to `/compounds/cinnamic-acid/`, and lists the article's items under `Gebinde`

#### Scenario: Not in the collection
- **WHEN** the demo data set is written, the substance `ethyl-acetate`, named `Ethylacetat`, is added to the registry after the latest accepted import, and a test client requests `/lab/registry/substances/ethyl-acetate/`
- **THEN** the page is headed `Ethylacetat` and has no link `In der Sammlung`

#### Scenario: Uses of a reaction type
- **WHEN** the reaction type `esterification` is named by two procedures of the collection, one of them withdrawn, and by no other record, and a test client requests `/lab/registry/reaction-types/`
- **THEN** the row of `esterification` reads `2` under `Verwendet`

### Requirement: Registry forms
A signed-in user SHALL create and edit substances and terms through these forms, each saved with its change history:

- `/lab/registry/substances/new/` and `/lab/registry/substances/<key>/edit/`: the key, on the new form only; the name and German name; the short name; the inventory group, a choice of the inventory groups in the order of their page; the chemical classes, a check box per class in that order, at least one checked; the formula; the molar mass; the SMILES; the CAS number; and the note. After saving, the substance's page opens.
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
