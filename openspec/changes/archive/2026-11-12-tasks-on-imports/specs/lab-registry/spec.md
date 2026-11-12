## MODIFIED Requirements

### Requirement: Registry pages
The registry's pages SHALL need no sign-in:

- `/lab/registry/` lists the substances under the heading `Substanzen` (`Substances`), followed by their number, ordered by name regardless of case, in a table with the columns `Name`, `Schlüssel` (`Key`), `Kurzname` (`Short name`), `Gruppe` (`Group`), `Stoffklassen` (`Chemical classes`), `Summenformel` (`Formula`), `Molmasse` (`Molar mass`) and `Artikelnr.` (`Article no.`), the name linking to the substance's page. The GET parameter `q`, from a search field labelled `Substanzen suchen` (`Search substances`), lists the substances in whose key, name, German name, short name or CAS number the text is found regardless of case. Above the table, links lead to the four vocabularies and, as `Importe der Sammlung` (`Collection imports`), to `/lab/collection/` (collection-import "Imports page"), and for a signed-in user a link `Neue Substanz` (`New substance`) to the new-substance form.
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
