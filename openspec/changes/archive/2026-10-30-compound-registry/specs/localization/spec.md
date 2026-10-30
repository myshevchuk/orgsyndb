## ADDED Requirements

### Requirement: German compound names
A compound's shown name SHALL be its `name_de` on a German site when the compound sets it, and its `name` otherwise; on an English site it is its `name`. Every place the site names a compound uses the shown name: the compound's page and its `<title>`, the compound directory and its order, the metadata panel, the key facts, the catalogue's Details view, the structure `alt` texts and the index terms.

#### Scenario: German names on a German site
- **WHEN** a test reads `public/compounds/salicylic-acid/index.html`, `public/compounds/index.html` and `public/procedures/osdb-0001/index.html` of a build of the test collection in locale `de`
- **THEN** the compound page's `h1` is `Salicylsäure`, the directory links it as `Salicylsäure`, ordered among the German names, and the procedure's `Product` link reads `Salicylsäure`

#### Scenario: A compound without a German name
- **WHEN** a test builds a copy of the test collection in locale `de` after removing `name_de` from `compounds/acetone.toml`
- **THEN** `public/compounds/acetone/index.html` has the `h1` equal to that file's `name`

## MODIFIED Requirements

### Requirement: Procedure variants
A procedure file's name MAY carry a language code, `de` or `en`, before its suffix: `OSDB-0001-x.de.md`, `OSDB-0001-x.en.org`. Files with the same `id` are variants of one procedure; an ID may occur once per code and once without one. Every variant SHALL have the same base name (the name without code and suffix) and the same value, or absence, of `status`, `reaction_types`, `tags`, `products` and `substrates` as the reference variant: the untagged file, else the `.de` file. Numbers compare by value, so `85` and `85.0` agree; other values compare by value and type. A mismatch is an error on the other variant, under the field's name (`file_name` for the base name), naming the reference's path. Any other field, and the body, may differ.

#### Scenario: A translation shares its ID and facts
- **WHEN** a run examines the baseline as `OSDB-0100-baseline.md` and, as `OSDB-0100-baseline.de.md`, the baseline with German headings and a different title, hazards, authors and `scale = "25,0 mmol"`
- **THEN** it exits 0 and prints nothing
- **AND** when the German file instead changes a product's `yield_percent`, `status` or `tags`, or adds `substrates`, it reports an error under `products`, `status`, `tags` or `substrates` on the German file, naming `OSDB-0100-baseline.md`

#### Scenario: A translation shares its ID and facts (integer and float)
- **WHEN** a run examines an untagged file whose product has `yield_percent = 85`, and its `.de` variant with `85.0`
- **THEN** it exits 0 and prints nothing, while `yield_percent = true` in the variant is still an error

#### Scenario: A translation shares its ID and facts (no untagged file)
- **WHEN** a run examines `OSDB-0100-baseline.de.md` and an `OSDB-0100-baseline.en.md` whose product has a different `yield_percent`
- **THEN** it reports exactly one error, field `products`, on the `.en` file, naming `OSDB-0100-baseline.de.md`

#### Scenario: Variants share a base name
- **WHEN** a run examines `OSDB-0100-baseline.md` and `OSDB-0100-other.de.md` with the same ID
- **THEN** it reports exactly one error, field `file_name`, on the German file, containing `OSDB-0100-baseline.de.md`

### Requirement: Interface strings
Every text that a layout shows SHALL come from the interface strings of the site's language, `site/i18n/de.toml` or `site/i18n/en.toml`, looked up with `T`; a page of `site/content/` names its title by a `title_key` front-matter value, a key of those files. The two files have the same keys, and every value is a non-empty string. The English strings are the texts that the site-theme, site-catalogue and print-layout specs name; a German site shows the German string in their place. In particular a German site shows:
- the skip link `Zum Inhalt springen`, the navigation `Vorschriften`, `Verbindungen`, `Hilfe` (in a `nav` with `aria-label="Website"`), the header search field labelled `Vorschriften durchsuchen` with the placeholder `Produkt, CAS, SMILES oder Stichwort` and the button `Suchen`, and the footer `OrgSynDB · interne Vorschriften · Stand <time>`;
- the page titles `Vorschriften`, `Reaktionstypen`, `Schlagwörter`, `Autoren`, `Verbindungen` and `Hilfe`;
- the section tabs `Alle Vorschriften`, `Reaktionstypen`, `Schlagwörter` and `Autoren` (in a `nav` with `aria-label="Vorschriften"`);
- the panel and key-fact labels `Produkt`, `Produkte`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ausgangsstoffe`, `Ansatzgröße`, `Ausbeute`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Geprüft von`, `Erstellt`, `Geändert`, `Vorstufen`, `Verwendet in`, and the sign-off `von <names>`;
- on compound pages the headings `Hergestellt nach` and `Verwendet in`, and in the compound directory the header cells `Verbindung`, `Summenformel`, `Molmasse`, `CAS`, `Hergestellt nach` and `Verwendet in`;
- the status `Entwurf`, `Geprüft` or `Zurückgezogen` for `draft`, `checked` or `retired`, while the badge class stays `badge--<status>`;
- the banner `Beispieldaten – Mengenangaben nicht experimentell überprüft.`, the button `Drucken / Als PDF speichern`, the copy button `Kopieren` with the messages `Kopiert` and `Markiert: Strg+C drücken`, and the placeholder `Keine Strukturformel`;
- in the catalogue: the count `<n> Vorschriften` (`1 Vorschrift`) and `{shown} von {total} Vorschriften`; the heading and toggle `Filter`; the facets `Reaktionstyp`, `Status`, `Schlagwort` and `Autor`; the directory links `Alle Reaktionstypen`, `Alle Schlagwörter` and `Alle Autoren`; `Alles zurücksetzen`; `Sortieren nach` with `Relevanz`, `ID`, `Titel (A–Z)`, `Erstellt (neueste zuerst)` and `Geändert (neueste zuerst)`; `Ansicht` with `Tabelle` and `Details`; the script texts `Suche läuft …`, `Suche nicht verfügbar`, `Der Suchindex konnte nicht geladen werden; die Suche wurde nicht angewendet.`, `Liste ohne Suche anzeigen`, `Keine Vorschrift passt zu Suche und Filtern.`, `In der Adresse nicht berücksichtigt: {list}` and `{facet}: {value} entfernen`; the `noscript` note `Suche, Filter und Sortierung brauchen JavaScript. Ohne JavaScript zeigt diese Seite ihre Vorschriften nach ID. Weitere Listen gibt es nach Reaktionstyp, Schlagwort oder Autor.`; and on term pages `Nur Vorschriften des Reaktionstyps <label>`, `Nur Vorschriften mit dem Schlagwort <tag>` or `Nur Vorschriften von <author>`, with the link `Alle Vorschriften anzeigen`, and the header search field labelled `Vorschriften des Reaktionstyps <label> durchsuchen`, `Vorschriften mit dem Schlagwort <tag> durchsuchen` or `Vorschriften von <author> durchsuchen` with the placeholder `Diese Vorschriften durchsuchen`;
- on the home page: the `h1` `Synthesevorschriften`, the lede `Die Vorschriften der Arbeitsgruppe, in Org oder Markdown nach einem gemeinsamen Schema geschrieben.`, the headings `Zuletzt geändert`, `Noch nicht geprüft` and `Übersicht`, the links `Alle Vorschriften, zuletzt geänderte zuerst` and `Alle Entwürfe`, and the entries `Alle Vorschriften`, `Reaktionstypen`, `Schlagwörter`, `Autoren` and `Verbindungen`;
- front-matter numbers (molecular weight, yield) with a decimal comma, and counts with German digit grouping.

The site script holds no language: the copy button carries its messages in `data-copied` and `data-selected`, and the catalogue carries its texts in `data-text-*` attributes.

#### Scenario: Both languages have every string
- **WHEN** a test loads both i18n files, scans the layouts for `T "<key>"` and reads the `title_key` of every page of `site/content/`
- **THEN** both files have the same keys with non-empty string values, every used key is present, and `site/content/` holds no file with a language code

#### Scenario: German page shell
- **WHEN** a test scans every HTML page of a build of a copy of the test collection `tests/fixtures/collection/` in locale `de`
- **THEN** each has `<html lang="de">`, the German skip link, exactly one `nav` in the site header with the German navigation, the German section tabs where the page has them, and the German footer, and `public/de/` and `public/en/` do not exist
- **AND** every page has the header search with the button `Suchen`, labelled `Vorschriften durchsuchen` everywhere but on the term pages

#### Scenario: German page titles
- **WHEN** the same test reads the six site pages `/procedures/`, `/reaction_types/`, `/tags/`, `/authors/`, `/compounds/` and `/help/`
- **THEN** their `h1` and `<title>` carry the German titles

#### Scenario: German metadata panel
- **WHEN** a test reads `public/procedures/osdb-0002/index.html` of that build
- **THEN** its panel labels are, in order, `Produkt`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ausgangsstoffe`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Erstellt`, `Geändert`, `Vorstufen`, its product link reads `Acetylsalicylsäure`, its key facts are `Ansatzgröße` `20 mmol` and `Ausbeute` `75 %`, the molecular weight reads `180,16 g/mol`, the reaction type is a link to `/reaction_types/acylation/` reading `Acylierung`, and the status badge reads `Entwurf`

#### Scenario: German catalogue and home page
- **WHEN** a test reads `public/procedures/index.html`, `public/tags/cinnamate/index.html` and `public/index.html` of that build
- **THEN** the catalogue's `h1` is `Vorschriften`, its count reads `8 Vorschriften`, its facets, sort and view options, `data-text-*` attributes and `noscript` note carry the German texts, and its status facet reads `Entwurf`, `Geprüft` and `Zurückgezogen`
- **AND** the term page's scope reads `Nur Vorschriften mit dem Schlagwort cinnamate` with the only link `Alle Vorschriften anzeigen`, and its header search field is labelled `Vorschriften mit dem Schlagwort cinnamate durchsuchen` with the placeholder `Diese Vorschriften durchsuchen`
- **AND** the home page has the German `h1`, headings, entries and links, and, since every German variant has the same `lastmod`, its recent list is OSDB-0001 to OSDB-0005 in ID order

#### Scenario: German catalogue in a browser
- **WHEN** the orchestrator uses the catalogue of a German build in a browser (manual verification, tasks.md section 6)
- **THEN** its counts, chips, loading text, empty-result and error messages, and the ignored-parameters notice are German
