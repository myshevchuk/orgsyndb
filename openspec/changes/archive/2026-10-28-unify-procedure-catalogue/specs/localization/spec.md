## MODIFIED Requirements

### Requirement: Interface strings
Every text that a layout shows SHALL come from the interface strings of the site's language, `site/i18n/de.toml` or `site/i18n/en.toml`, looked up with `T`; a page of `site/content/` names its title by a `title_key` front-matter value, a key of those files. The two files have the same keys, and every value is a non-empty string. The English strings are the texts that the site-theme, site-catalogue and print-layout specs name; a German site shows the German string in their place. In particular a German site shows:
- the skip link `Zum Inhalt springen`, the navigation `Vorschriften`, `Reaktionstypen`, `Hilfe` (in a `nav` with `aria-label="Website"`), the header search field labelled `Vorschriften durchsuchen` with the button `Suchen`, and the footer `OrgSynDB · interne Vorschriften`;
- the page titles `Vorschriften`, `Reaktionstypen`, `Schlagwörter`, `Autoren` and `Hilfe`;
- the panel labels `ID`, `Produkt`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ansatzgröße`, `Ausbeute`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Geprüft von`, `Erstellt`, `Geändert`, `Vorstufen`, `Verwendet in`;
- the status `Entwurf`, `geprüft` or `zurückgezogen` for `draft`, `checked` or `retired`, while the badge class stays `badge--<status>`;
- the banner `Beispieldaten – Mengenangaben nicht experimentell überprüft.`, the button `Drucken / Als PDF speichern`, the copy button `Kopieren` with the messages `Kopiert` and `Markiert: Strg+C drücken`, and the placeholder `Keine Strukturformel`;
- in the catalogue: the count `<n> Vorschriften` (`1 Vorschrift`) and `{shown} von {total} Vorschriften`; the search label `Vorschriften durchsuchen`, the placeholder `Produkt, CAS, SMILES oder Stichwort` and the button `Suchen`; the heading and toggle `Filter`; the facets `Reaktionstyp`, `Status`, `Schlagwort` and `Autor`; the directory links `Alle Reaktionstypen`, `Alle Schlagwörter` and `Alle Autoren`; `Alles zurücksetzen`; `Sortieren nach` with `Relevanz`, `ID`, `Titel (A–Z)`, `Erstellt (neueste zuerst)` and `Geändert (neueste zuerst)`; `Ansicht` with `Tabelle` and `Details`; the script texts `Suche läuft …`, `Suche nicht verfügbar`, `Der Suchindex konnte nicht geladen werden; die Suche wurde nicht angewendet.`, `Liste ohne Suche anzeigen`, `Keine Vorschrift passt zu Suche und Filtern.`, `In der Adresse nicht berücksichtigt: {list}` and `{facet}: {value} entfernen`; the `noscript` note `Suche, Filter und Sortierung brauchen JavaScript. Ohne JavaScript zeigt diese Seite ihre Vorschriften nach ID. Weitere Listen gibt es nach Reaktionstyp, Schlagwort oder Autor.`; and on term pages `Nur Vorschriften des Reaktionstyps <label>`, `Nur Vorschriften mit dem Schlagwort <tag>` or `Nur Vorschriften von <author>`, with the link `Alle Vorschriften anzeigen`;
- on the home page: the lede `Die Synthesevorschriften der Arbeitsgruppe, in Org oder Markdown geschrieben und nach einem gemeinsamen Schema geprüft.`, the headings `Zuletzt geändert` and `Übersicht`, the link `Alle Vorschriften, zuletzt geänderte zuerst`, and the entries `Alle Vorschriften`, `Entwürfe`, `Reaktionstypen`, `Schlagwörter` and `Autoren`;
- front-matter numbers (molecular weight, yield) with a decimal comma, and counts with German digit grouping.

The site script holds no language: the copy button carries its messages in `data-copied` and `data-selected`, and the catalogue carries its texts in `data-text-*` attributes.

#### Scenario: Both languages have every string
- **WHEN** a test loads both i18n files, scans the layouts for `T "<key>"` and reads the `title_key` of every page of `site/content/`
- **THEN** both files have the same keys with non-empty string values, every used key is present, and `site/content/` holds no file with a language code

#### Scenario: German page shell
- **WHEN** a test scans every HTML page of a build of a copy of the test collection `tests/fixtures/collection/` in locale `de`
- **THEN** each has `<html lang="de">`, the German skip link, exactly one `nav` in the site header with the German navigation, and the German footer, and `public/de/` and `public/en/` do not exist
- **AND** every page but the catalogue and term pages has the header search with the label `Vorschriften durchsuchen` and the button `Suchen`

#### Scenario: German page titles
- **WHEN** the same test reads the five site pages `/procedures/`, `/reaction_types/`, `/tags/`, `/authors/` and `/help/`
- **THEN** their `h1` and `<title>` carry the German titles

#### Scenario: German metadata panel
- **WHEN** a test reads `public/procedures/osdb-0002/index.html` of that build
- **THEN** its panel labels are, in order, `ID`, `Produkt`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ansatzgröße`, `Ausbeute`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Erstellt`, `Geändert`, `Vorstufen`, the molecular weight reads `180,16 g/mol`, the reaction type is a link to `/reaction_types/acylation/` reading `Acylierung`, and the status badge reads `Entwurf`

#### Scenario: German catalogue and home page
- **WHEN** a test reads `public/procedures/index.html`, `public/tags/cinnamate/index.html` and `public/index.html` of that build
- **THEN** the catalogue's `h1` is `Vorschriften`, its count reads `8 Vorschriften`, its facets, sort and view options, `data-text-*` attributes and `noscript` note carry the German texts, and its status facet reads `Entwurf`, `geprüft` and `zurückgezogen`
- **AND** the term page's scope reads `Nur Vorschriften mit dem Schlagwort cinnamate` with the link `Alle Vorschriften anzeigen`
- **AND** the home page has the German headings and entries, and, since every German variant has the same `lastmod`, its recent list is OSDB-0001 to OSDB-0005 in ID order

#### Scenario: German catalogue in a browser
- **WHEN** the orchestrator uses the catalogue of a German build in a browser (manual verification, tasks.md section 6)
- **THEN** its counts, chips, loading text, empty-result and error messages, and the ignored-parameters notice are German

### Requirement: German reaction-type labels
Every entry of `site/data/reaction_types.toml` SHALL have, besides `label`, a non-empty string `label_de`. A German site shows `label_de` wherever an English one shows `label`; an entry without `label_de` shows `label`. The reaction-type lists of `/reaction_types/` and of the catalogue's reaction-type facet are ordered by the shown label. The validator refuses, as a configuration error, a vocabulary with a `label_<language>` that is not a non-empty string.

#### Scenario: Vocabulary with German labels
- **WHEN** a test loads the shipped vocabulary, and runs the validator with a vocabulary whose entry has `label_de = " "`
- **THEN** every shipped entry has a non-empty `label_de`, and the validator exits 2 naming `label_de`

#### Scenario: German labels for reaction types
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html`, the reaction-type list of `public/reaction_types/index.html` and the reaction-type facet of `public/procedures/index.html`, of a German build
- **THEN** the term page's `h1` is `Aldolkondensation` and its title `Aldolkondensation | OrgSynDB`
- **AND** both lists show the German labels in alphabetical order

### Requirement: Choosing the variant to publish
For each procedure ID, the build SHALL publish exactly one variant: the file tagged with the site's language; else the untagged file; else a file tagged with another language, in the order `de`, `en`. `pipeline.choose_variants(files, language)` makes the choice from `(path, front matter)` pairs and returns the chosen pairs by ID. `pipeline.stage_content(chosen, target)` empties `target` (`build/content/procedures/`) and copies each chosen file there as `<base name>.md`; a file whose name has a code and whose front matter has no `language` gets `language = "<code>"` as its first front-matter line. Hugo reads procedures from that directory only. `pdf` renders the chosen files, each to `pdf/<source stem>.pdf`.

#### Scenario: Choosing the variant to publish
- **WHEN** a test calls `choose_variants` for site language `de` on `x.md`; on `x.md` and `x.de.md`; on `x.md` and `x.en.md`; on `x.en.md` alone; and for `en` on `x.md` and `x.de.md`, and on `x.en.md` and `x.de.md`
- **THEN** it chooses `x.md`, `x.de.md`, `x.md`, `x.en.md`, `x.md` and `x.en.md`

#### Scenario: Staging the chosen variants
- **WHEN** a test stages a tagged file without `language`, a tagged file with it and an untagged file into a directory holding a stale file
- **THEN** the directory holds exactly the three base names with `.md`, the first copy has `language = "<code>"` after its opening `+++`, and the others are byte-identical to their sources

#### Scenario: Choosing the variant to publish (test collection)
- **WHEN** a test builds a copy of the test collection `tests/fixtures/collection/` in locale `de`
- **THEN** the eight `.de` variants are published, one page per ID at `/procedures/<slug>/`

#### Scenario: Every procedure in every locale
- **WHEN** a test removes `md/procedures/OSDB-0001-salicylic-acid.de.md` and `md/procedures/OSDB-0004-4-acetylbiphenyl.de.md` from a copy of the test collection, adds the baseline as `md/procedures/OSDB-0100-baseline.en.md`, and builds it in locale `de`
- **THEN** nine procedures are published, OSDB-0001 from the untagged English file, OSDB-0100 from the `.en` file, the German home page's browse list gives `Alle Vorschriften` with the count `(9)`, and the catalogue lists nine rows, each ID once

### Requirement: German search index
Pagefind SHALL index the procedure pages under the site's language.

#### Scenario: German search index
- **WHEN** a test searches the `de` index of a German build of a copy of the test collection `tests/fixtures/collection/` under Node, through the catalogue's searcher and with plain Pagefind searches
- **THEN** the searcher finds exactly OSDB-0001 and OSDB-0008 for `Verseifung` and finds OSDB-0008 for `Zimtsäure`, the filter names are exactly `id`, and every result title is a published title
