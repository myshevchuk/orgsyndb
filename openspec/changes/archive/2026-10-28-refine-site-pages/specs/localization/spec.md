## MODIFIED Requirements

### Requirement: Interface strings
Every text that a layout shows SHALL come from the interface strings of the site's language, `site/i18n/de.toml` or `site/i18n/en.toml`, looked up with `T`; a page of `site/content/` names its title by a `title_key` front-matter value, a key of those files. The two files have the same keys, and every value is a non-empty string. The English strings are the texts that the site-theme, site-catalogue and print-layout specs name; a German site shows the German string in their place. In particular a German site shows:
- the skip link `Zum Inhalt springen`, the navigation `Vorschriften`, `Reaktionstypen`, `Hilfe` (in a `nav` with `aria-label="Website"`), the header search field labelled `Vorschriften durchsuchen` with the placeholder `Produkt, CAS, SMILES oder Stichwort` and the button `Suchen`, and the footer `OrgSynDB · interne Vorschriften · Stand <time>`;
- the page titles `Vorschriften`, `Reaktionstypen`, `Schlagwörter`, `Autoren` and `Hilfe`;
- the panel labels `Produkt`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ansatzgröße`, `Ausbeute`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Geprüft von`, `Erstellt`, `Geändert`, `Vorstufen`, `Verwendet in`;
- the status `Entwurf`, `Geprüft` or `Zurückgezogen` for `draft`, `checked` or `retired`, while the badge class stays `badge--<status>`;
- the banner `Beispieldaten – Mengenangaben nicht experimentell überprüft.`, the button `Drucken / Als PDF speichern`, the copy button `Kopieren` with the messages `Kopiert` and `Markiert: Strg+C drücken`, and the placeholder `Keine Strukturformel`;
- in the catalogue: the count `<n> Vorschriften` (`1 Vorschrift`) and `{shown} von {total} Vorschriften`; the heading and toggle `Filter`; the facets `Reaktionstyp`, `Status`, `Schlagwort` and `Autor`; the directory links `Alle Reaktionstypen`, `Alle Schlagwörter` and `Alle Autoren`; `Alles zurücksetzen`; `Sortieren nach` with `Relevanz`, `ID`, `Titel (A–Z)`, `Erstellt (neueste zuerst)` and `Geändert (neueste zuerst)`; `Ansicht` with `Tabelle` and `Details`; the script texts `Suche läuft …`, `Suche nicht verfügbar`, `Der Suchindex konnte nicht geladen werden; die Suche wurde nicht angewendet.`, `Liste ohne Suche anzeigen`, `Keine Vorschrift passt zu Suche und Filtern.`, `In der Adresse nicht berücksichtigt: {list}` and `{facet}: {value} entfernen`; the `noscript` note `Suche, Filter und Sortierung brauchen JavaScript. Ohne JavaScript zeigt diese Seite ihre Vorschriften nach ID. Weitere Listen gibt es nach Reaktionstyp, Schlagwort oder Autor.`; and on term pages `Nur Vorschriften des Reaktionstyps <label>`, `Nur Vorschriften mit dem Schlagwort <tag>` or `Nur Vorschriften von <author>`, with the link `Alle Vorschriften anzeigen`, and the header search field labelled `Vorschriften des Reaktionstyps <label> durchsuchen`, `Vorschriften mit dem Schlagwort <tag> durchsuchen` or `Vorschriften von <author> durchsuchen` with the placeholder `Diese Vorschriften durchsuchen`;
- on the home page: the `h1` `Synthesevorschriften`, the lede `Die Vorschriften der Arbeitsgruppe, in Org oder Markdown nach einem gemeinsamen Schema geschrieben.`, the headings `Zuletzt geändert`, `Noch nicht geprüft` and `Übersicht`, the links `Alle Vorschriften, zuletzt geänderte zuerst` and `Alle Entwürfe`, and the entries `Alle Vorschriften`, `Reaktionstypen`, `Schlagwörter` and `Autoren`;
- front-matter numbers (molecular weight, yield) with a decimal comma, and counts with German digit grouping.

The site script holds no language: the copy button carries its messages in `data-copied` and `data-selected`, and the catalogue carries its texts in `data-text-*` attributes.

#### Scenario: Both languages have every string
- **WHEN** a test loads both i18n files, scans the layouts for `T "<key>"` and reads the `title_key` of every page of `site/content/`
- **THEN** both files have the same keys with non-empty string values, every used key is present, and `site/content/` holds no file with a language code

#### Scenario: German page shell
- **WHEN** a test scans every HTML page of a build of a copy of the test collection `tests/fixtures/collection/` in locale `de`
- **THEN** each has `<html lang="de">`, the German skip link, exactly one `nav` in the site header with the German navigation, and the German footer, and `public/de/` and `public/en/` do not exist
- **AND** every page has the header search with the button `Suchen`, labelled `Vorschriften durchsuchen` everywhere but on the term pages

#### Scenario: German page titles
- **WHEN** the same test reads the five site pages `/procedures/`, `/reaction_types/`, `/tags/`, `/authors/` and `/help/`
- **THEN** their `h1` and `<title>` carry the German titles

#### Scenario: German metadata panel
- **WHEN** a test reads `public/procedures/osdb-0002/index.html` of that build
- **THEN** its panel labels are, in order, `Produkt`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ansatzgröße`, `Ausbeute`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Erstellt`, `Geändert`, `Vorstufen`, the molecular weight reads `180,16 g/mol`, the reaction type is a link to `/reaction_types/acylation/` reading `Acylierung`, and the status badge reads `Entwurf`

#### Scenario: German catalogue and home page
- **WHEN** a test reads `public/procedures/index.html`, `public/tags/cinnamate/index.html` and `public/index.html` of that build
- **THEN** the catalogue's `h1` is `Vorschriften`, its count reads `8 Vorschriften`, its facets, sort and view options, `data-text-*` attributes and `noscript` note carry the German texts, and its status facet reads `Entwurf`, `Geprüft` and `Zurückgezogen`
- **AND** the term page's scope reads `Nur Vorschriften mit dem Schlagwort cinnamate` with the link `Alle Vorschriften anzeigen`, and its header search field is labelled `Vorschriften mit dem Schlagwort cinnamate durchsuchen` with the placeholder `Diese Vorschriften durchsuchen`
- **AND** the home page has the German `h1`, headings, entries and links, and, since every German variant has the same `lastmod`, its recent list is OSDB-0001 to OSDB-0005 in ID order

#### Scenario: German catalogue in a browser
- **WHEN** the orchestrator uses the catalogue of a German build in a browser (manual verification, tasks.md section 6)
- **THEN** its counts, chips, loading text, empty-result and error messages, and the ignored-parameters notice are German

### Requirement: Choosing the variant to publish
For each procedure ID, the build SHALL publish exactly one variant: the file tagged with the site's language; else the untagged file; else a file tagged with another language, in the order `de`, `en`. `pipeline.choose_variants(files, language)` makes the choice from `(path, front matter)` pairs and returns the chosen pairs by ID. `pipeline.stage_content(chosen, target)` empties `target` (`build/content/procedures/`) and copies each chosen file there as `<base name>.md`, with its note references linked by `pipeline.link_notes` (site-theme "Note references"); a file whose name has a code and whose front matter has no `language` gets `language = "<code>"` as its first front-matter line. Hugo reads procedures from that directory only. `pdf` renders the chosen files, each to `pdf/<source stem>.pdf`.

#### Scenario: Choosing the variant to publish
- **WHEN** a test calls `choose_variants` for site language `de` on `x.md`; on `x.md` and `x.de.md`; on `x.md` and `x.en.md`; on `x.en.md` alone; and for `en` on `x.md` and `x.de.md`, and on `x.en.md` and `x.de.md`
- **THEN** it chooses `x.md`, `x.de.md`, `x.md`, `x.en.md`, `x.md` and `x.en.md`

#### Scenario: Staging the chosen variants
- **WHEN** a test stages a tagged file without `language`, a tagged file with it and an untagged file into a directory holding a stale file
- **THEN** the directory holds exactly the three base names with `.md`, the first copy has `language = "<code>"` after its opening `+++`, and the others, which have no notes list, are byte-identical to their sources

#### Scenario: Choosing the variant to publish (test collection)
- **WHEN** a test builds a copy of the test collection `tests/fixtures/collection/` in locale `de`
- **THEN** the eight `.de` variants are published, one page per ID at `/procedures/<slug>/`

#### Scenario: Every procedure in every locale
- **WHEN** a test removes `md/procedures/OSDB-0001-salicylic-acid.de.md` and `md/procedures/OSDB-0004-4-acetylbiphenyl.de.md` from a copy of the test collection, adds the baseline as `md/procedures/OSDB-0100-baseline.en.md`, and builds it in locale `de`
- **THEN** nine procedures are published, OSDB-0001 from the untagged English file, OSDB-0100 from the `.en` file, the German home page's browse list gives `Alle Vorschriften` with the count `(9)`, and the catalogue lists nine rows, each ID once
