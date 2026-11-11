## MODIFIED Requirements

### Requirement: Registry pages
The registry's pages SHALL need no sign-in:

- `/lab/registry/` lists the substances under the heading `Substanzen` (`Substances`), followed by their number, ordered by name regardless of case, in a table with the columns `Name`, `Schlüssel` (`Key`), `Kurzname` (`Short name`), `Gruppe` (`Group`), `Stoffklassen` (`Chemical classes`), `Summenformel` (`Formula`), `Molmasse` (`Molar mass`) and `Artikelnr.` (`Article no.`), the name linking to the substance's page. The GET parameter `q`, from a search field labelled `Substanzen suchen` (`Search substances`), lists the substances in whose key, name, German name, short name or CAS number the text is found regardless of case. Above the table, links lead to the four vocabularies, and for a signed-in user a link `Neue Substanz` (`New substance`) to the new-substance form.
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

### Requirement: Importing a collection's registry
`manage.py registry_import COLLECTION` SHALL build a snapshot from the collection directory COLLECTION and load it as `registry_load` does:

- the vocabularies from `vocabularies/chemical-classes.toml`, `inventory-groups.toml`, `projects.toml` and `reaction-types.toml`, each table name a key with its `label`, `label_de` and `parent`; a missing file gives an empty vocabulary;
- a substance for each `compounds/<key>.toml`, with `name`, `name_de`, `formula`, `mw`, `smiles` and `cas`, and the collection's declared fields `short_name`, `chemical_class` (the classes), `group` and `item_number` (the article number).

It writes to stderr one warning naming the other keys it leaves out, such as `structure_image`, `in_house` and `stock`, with how many compounds set each. A compound without a group or a chemical class, or a file that cannot be read, is an error naming the file, and nothing is loaded.

#### Scenario: A collection in the old layout
- **WHEN** `registry_import` runs into an empty database on `webapp/tests/fixtures/old-layout/`, a collection in the layout collections had before they named a registry: the demo collection's former `orgsyndb.toml`, `compounds/` and `vocabularies/`
- **THEN** the registry holds its 20 compounds as substances, `cinnamic-acid` with the group `final-products`, the chemical class `carboxylic-acids` and an article numbered `CH-0012`, and stderr names `in_house` and `stock`
