## MODIFIED Requirements

### Requirement: Registry pages
The registry's pages SHALL need no sign-in:

- `/lab/registry/` lists the substances under the heading `Substanzen` (`Substances`), followed by their number, ordered by name regardless of case, in a table with the columns `Name`, `Schlüssel` (`Key`), `Kurzname` (`Short name`), `Bestandsgruppe` (`Inventory group`), `Stoffklassen` (`Chemical classes`), `Summenformel` (`Formula`), `Molmasse` (`Molar mass`) and `Artikelnr.` (`Article no.`), the name linking to the substance's page. The GET parameter `q`, from a search field labelled `Substanzen suchen` (`Search substances`), lists the substances in whose key, name, German name, short name or CAS number the text is found regardless of case. The GET parameters `group` and `class`, from the choices `Bestandsgruppe` (`Inventory group`) and `Stoffklasse` (`Chemical class`), each offering `Alle` (`All`) and the vocabulary's terms in the order of its page, list the substances filed under the term with that key or under a term filed below it, at any depth; a key that names no term lists none. The parameters narrow the list together, and the form keeps their values. For a signed-in user a link `Neue Substanz` (`New substance`) to the new-substance form.
- `/lab/registry/substances/<key>/` shows the substance's name as heading, followed by its key, its inventory group and its chemical classes, and shows its data in widgets (web-app "Widgets"):
  - a compound widget holding, when the substance has a structure image (Structure images), a `figure.structure` holding an `img` whose `src` is `/lab/registry/substances/<key>/structure.svg` and whose `alt` is `Strukturformel von <name>` (`Structure of <name>`), `<name>` its shown name, and then its article number, formula, molar mass, CAS number, SMILES, inventory group, chemical classes, key, name, German name, short name and note, each `–` when it has none. The SMILES is followed by the copy button of the site's pages (site-theme "Site scripts").
  - `Gebinde` (`Containers`), its article's items, each linking to its page, with its number of containers; `Chargen` (`Batches`), its batches, newest first as the batch list orders them, each linking to its page, with the amount in its open vessels by unit; and `Aufträge` (`Tasks`), its tasks, each linking to its page, with its state. Each reads `Keine` (`None`) when it has no row.
  - The following show only when they have a row, each a table:
    - `Hergestellt nach` (`Made by`): one row per specific procedure that is not withdrawn whose entry is not withdrawn and has the substance among its products, and one per such entry of a general procedure that is not withdrawn, by ID and then by entry position, with the procedure, a link `<ID> <title>` to `/procedures/<id>/`, the ID in lower case and the title the procedure's shown title; for an entry, `Eintrag <n>` (`entry <n>`), `<n>` its position; the product's yield, `<yield> %`, when it is known; and the procedure's status badge.
    - `Verwendet in` (`Used in`): one row per procedure that is not withdrawn with the substance among the substrates of an entry that is not withdrawn, by ID, with the link and the badge.
    - `Synthesewege` (`Sequences`): one row per sequence that is not withdrawn whose target is the substance, by ID, with its ID linking `/sequences/<id>/`, the ID in lower case, and its shown title.
  - `Herstellungswege` (`Routes`), a collapsible widget, open when the page loads, shown only when the substance has a route tree: the tree (synthesis-routes "Routes in the lab"), each step written as the link `<ID> <title>`, then ` · Eintrag <n>` for an entry, then ` · <yield> %` when the yield is known, then ` · ` and the badge, followed by the substances it starts from, each linking its substance page with its shown name and followed by the steps it keeps, or, when it is cut off, by ` · weitere Stufen auf ihrer Seite` (` · more steps on its page`).

  For a signed-in user the page has a link `Bearbeiten` (`Edit`) to the substance's edit form.
  A procedure's shown title is `title_de` on a German site when it has one, else `title`, and so is a sequence's. These links assume the site serves the latest accepted import's release: the builder publishes it on acceptance, and until it does, after a lost answer or for the demo data set's own import, a link may lead to a page the site does not serve yet. A yield is written as a number in the language's form, without a fractional part when it is whole. The status badge reads `Entwurf`, `Geprüft` or `Zurückgezogen` (`draft`, `checked`, `retired`), and a procedure without a status has none. An unknown key answers 404.
- `/lab/registry/<vocabulary>/`, `<vocabulary>` one of `chemical-classes`, `groups`, `projects` and `reaction-types`, lists the vocabulary's terms under its name as heading, each term after its parent and its parent's earlier children, in key order among siblings, indented by its depth, with the columns `Schlüssel` (`Key`), `Bezeichnung` (`Label`), `Bezeichnung deutsch` (`German label`), `Oberbegriff` (`Parent`), but no parent column for the reaction types, and `Verwendet` (`In use`), the number of records that name the term: substances for the chemical classes and the inventory groups, procedures of the collection, withdrawn ones included, for the projects and the reaction types; for a signed-in user, a link `Neuer Begriff` (`New term`) and each term's key linking to its edit form. Any other vocabulary answers 404.

#### Scenario: Substance list and search
- **WHEN** the demo data set is written and a test client requests `/lab/registry/?q=zimt`
- **THEN** the list holds `(E)-Zimtsäure` linking to `/lab/registry/substances/cinnamic-acid/`, with the article number `CH-0012`, and no substance whose names, key, short name and CAS number lack `zimt`

#### Scenario: Substance page
- **WHEN** the demo data set is written, an import of the demo collection was accepted, and a test client requests `/lab/registry/substances/cinnamic-acid/`
- **THEN** the page is headed `(E)-Zimtsäure`, its compound widget holds the article number `CH-0012`, its widget `Gebinde` lists the article's items, and it links no path under `/compounds/`

#### Scenario: Procedures beside a substance
- **WHEN** the demo data set is written and a test client requests the pages of `acetylsalicylic-acid`, `salicylic-acid` and `1-biphenyl-4-yl-ethanol`
- **THEN** the first's widget `Hergestellt nach` holds one row: `OSDB-0002 Aspirin (Acetylsalicylsäure)` linking `/procedures/osdb-0002/`, no entry, `75 %` and the badge `Entwurf`; its widget `Synthesewege` a row `SEQ-0001` linking `/sequences/seq-0001/`; and its widget `Herstellungswege` the step `OSDB-0002`, under it `salicylic-acid` and `acetic-anhydride` linking their substance pages, and under `salicylic-acid` the step `OSDB-0001` with ` · 80 % · `
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
- **THEN** the first's compound widget holds one `figure.structure` whose `img` has the `src` `/lab/registry/substances/isopentyl-acetate/structure.svg` and the `alt` `Strukturformel von Isopentylacetat`, and the second has no `figure.structure`

#### Scenario: Empty widgets of a substance
- **WHEN** a test client requests the page of a substance without article, batch, task, procedure, sequence or route
- **THEN** its widgets `Gebinde`, `Chargen` and `Aufträge` each read `Keine`, and it has no widget `Hergestellt nach`, `Verwendet in`, `Synthesewege` or `Herstellungswege`
