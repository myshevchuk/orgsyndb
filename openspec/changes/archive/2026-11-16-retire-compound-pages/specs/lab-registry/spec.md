## MODIFIED Requirements

### Requirement: Registry pages
The registry's pages SHALL need no sign-in:

- `/lab/registry/` lists the substances under the heading `Substanzen` (`Substances`), followed by their number, ordered by name regardless of case, in a table with the columns `Name`, `Schlüssel` (`Key`), `Kurzname` (`Short name`), `Bestandsgruppe` (`Inventory group`), `Stoffklassen` (`Chemical classes`), `Summenformel` (`Formula`), `Molmasse` (`Molar mass`) and `Artikelnr.` (`Article no.`), the name linking to the substance's page. The GET parameter `q`, from a search field labelled `Substanzen suchen` (`Search substances`), lists the substances in whose key, name, German name, short name or CAS number the text is found regardless of case. The GET parameters `group` and `class`, from the choices `Bestandsgruppe` (`Inventory group`) and `Stoffklasse` (`Chemical class`), each offering `Alle` (`All`) and the vocabulary's terms in the order of its page, list the substances filed under the term with that key or under a term filed below it, at any depth; a key that names no term lists none. The parameters narrow the list together, and the form keeps their values. For a signed-in user a link `Neue Substanz` (`New substance`) to the new-substance form.
- `/lab/registry/substances/<key>/` shows the substance's name as heading and its key, names, short name, inventory group, chemical classes, formula, molar mass, SMILES, CAS number, note and article number, each `–` when it has none; when it has a structure image (Structure images), a `figure.structure` holding an `img` whose `src` is `/lab/registry/substances/<key>/structure.svg` and whose `alt` is `Strukturformel von <name>` (`Structure of <name>`), `<name>` its shown name; for a signed-in user a link `Bearbeiten` (`Edit`) to its edit form; and the sections `Gebinde` (`Containers`), its article's items linking to their pages, `Bulk-Lose` (`Bulk lots`), its open lots linking to theirs, and `Aufträge` (`Tasks`), its tasks linking to theirs, each `Keine` (`None`) when empty. The SMILES is followed by the copy button of the site's pages (site-theme "Content does not need JavaScript"). Each of these sections shows only when it has an item:
  - `Hergestellt nach` (`Made by`): one item per specific procedure that is not withdrawn whose entry is not withdrawn and has the substance among its products, and one per such entry of a general procedure that is not withdrawn, by ID and then by entry position. An item is a link `<ID> <title>` to `/procedures/<id>/`, the ID in lower case and the title the procedure's shown title, then, for an entry, ` · Eintrag <n>` (` · entry <n>`), `<n>` its position, then ` · <yield> %` when the product's yield is known, then ` · ` and the procedure's status badge.
  - `Verwendet in` (`Used in`): one item per procedure that is not withdrawn with the substance among the substrates of an entry that is not withdrawn, by ID: the link, then ` · ` and the badge.
  - `Synthesewege` (`Sequences`): one item per sequence that is not withdrawn whose target is the substance, by ID, linking `/sequences/<id>/`, the ID in lower case, with its shown title.
  - `Herstellungswege` (`Routes`): the substance's route tree (synthesis-routes "Routes in the lab"), as nested lists: each step written as an item of `Hergestellt nach`, followed by the substances it starts from, each linking its substance page with its shown name and followed by the steps it keeps, or, when it is cut off, by ` · weitere Stufen auf ihrer Seite` (` · more steps on its page`).

  A procedure's shown title is `title_de` on a German site when it has one, else `title`, and so is a sequence's. These links assume the site serves the latest accepted import's release: the builder publishes it on acceptance, and until it does, after a lost answer or for the demo data set's own import, a link may lead to a page the site does not serve yet. A yield is written as a number in the language's form, without a fractional part when it is whole. The status badge reads `Entwurf`, `Geprüft` or `Zurückgezogen` (`draft`, `checked`, `retired`), and a procedure without a status has none. An unknown key answers 404.
- `/lab/registry/<vocabulary>/`, `<vocabulary>` one of `chemical-classes`, `groups`, `projects` and `reaction-types`, lists the vocabulary's terms under its name as heading, each term after its parent and its parent's earlier children, in key order among siblings, indented by its depth, with the columns `Schlüssel` (`Key`), `Bezeichnung` (`Label`), `Bezeichnung deutsch` (`German label`), `Oberbegriff` (`Parent`), but no parent column for the reaction types, and `Verwendet` (`In use`), the number of records that name the term: substances for the chemical classes and the inventory groups, procedures of the collection, withdrawn ones included, for the projects and the reaction types; for a signed-in user, a link `Neuer Begriff` (`New term`) and each term's key linking to its edit form. Any other vocabulary answers 404.

#### Scenario: Substance list and search
- **WHEN** the demo data set is written and a test client requests `/lab/registry/?q=zimt`
- **THEN** the list holds `(E)-Zimtsäure` linking to `/lab/registry/substances/cinnamic-acid/`, with the article number `CH-0012`, and no substance whose names, key, short name and CAS number lack `zimt`

#### Scenario: Substance page
- **WHEN** the demo data set is written, an import of the demo collection was accepted, and a test client requests `/lab/registry/substances/cinnamic-acid/`
- **THEN** the page is headed `(E)-Zimtsäure`, lists the article's items under `Gebinde`, and links no path under `/compounds/`

#### Scenario: Procedures beside a substance
- **WHEN** the demo data set is written and a test client requests the pages of `acetylsalicylic-acid`, `salicylic-acid` and `1-biphenyl-4-yl-ethanol`
- **THEN** the first lists under `Hergestellt nach` one item, `OSDB-0002 Aspirin (Acetylsalicylsäure)` linking `/procedures/osdb-0002/`, then ` · 75 % · ` and the badge `Entwurf`; under `Synthesewege` `SEQ-0001` linking `/sequences/seq-0001/`; and under `Herstellungswege` the step `OSDB-0002`, under it `salicylic-acid` and `acetic-anhydride` linking their substance pages, and under `salicylic-acid` the step `OSDB-0001` with ` · 80 % · `
- **AND** the second lists `OSDB-0001` under `Hergestellt nach` and `OSDB-0002` under `Verwendet in`, and has no `Herstellungswege`
- **AND** the third lists under `Hergestellt nach` `OSDB-0005` with ` · 90 % · ` and `OSDB-0009` with ` · Eintrag 1 · 90 % · `, in that order

#### Scenario: Filters of the list
- **WHEN** the inventory group `final-products` is filed under `synthesised`, the substance `a` is filed under `final-products`, `b` under `synthesised` and `c` under `purchased`, and a test client requests `/lab/registry/?group=synthesised`, then `?group=final-products`, then `?group=nope`
- **THEN** the first lists `a` and `b`, the second `a` alone and the third none


#### Scenario: Uses of a reaction type
- **WHEN** the reaction type `esterification` is named by two procedures of the collection, one of them withdrawn, and by no other record, and a test client requests `/lab/registry/reaction-types/`
- **THEN** the row of `esterification` reads `2` under `Verwendet`

#### Scenario: Structure on the page
- **WHEN** the demo data set is written and a test client requests the pages of `isopentyl-acetate` and `new-compound-7`
- **THEN** the first has one `figure.structure` whose `img` has the `src` `/lab/registry/substances/isopentyl-acetate/structure.svg` and the `alt` `Strukturformel von Isopentylacetat`, and the second has no `figure.structure`

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
