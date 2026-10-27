## MODIFIED Requirements

### Requirement: Interface strings
Every text that a layout shows SHALL come from the interface strings of the site's language, `site/i18n/de.toml` or `site/i18n/en.toml`, looked up with `T`; a page of `site/content/` names its title by a `title_key` front-matter value, a key of those files. The two files have the same keys, and every value is a non-empty string. The English strings are the texts that the site-theme, site-search and print-layout specs name; a German site shows the German string in their place. In particular a German site shows:
- the skip link `Zum Inhalt springen`, the navigation `Vorschriften`, `Reaktionstypen`, `Schlagwörter`, `Autoren`, `Hilfe` (in a `nav` with `aria-label="Website"`), and the footer `OrgSynDB · interne Vorschriften`;
- the page titles `Alle Vorschriften`, `Alle Vorschriften nach Datum`, `Reaktionstypen`, `Schlagwörter`, `Autoren`, `Suche` and `Hilfe`;
- the panel labels `ID`, `Produkt`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ansatzgröße`, `Ausbeute`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Geprüft von`, `Erstellt`, `Geändert`, `Vorstufen`, `Verwendet in`;
- the status `Entwurf`, `geprüft` or `zurückgezogen` for `draft`, `checked` or `retired`, while the badge class stays `badge--<status>`;
- the banner `Beispieldaten – Mengenangaben nicht experimentell überprüft.`, the button `Drucken / Als PDF speichern`, the copy button `Kopieren` with the messages `Kopiert` and `Markiert: Strg+C drücken`, and the placeholder `Keine Strukturformel`;
- the Pagefind filter names `Status`, `Reaktionstyp`, `Schlagwort` and `Autor`;
- front-matter numbers (molecular weight, yield) with a decimal comma.

The site script holds no language: the copy button carries its messages in `data-copied` and `data-selected`.

#### Scenario: Both languages have every string
- **WHEN** a test loads both i18n files, scans the layouts for `T "<key>"` and reads the `title_key` of every page of `site/content/`
- **THEN** both files have the same keys with non-empty string values, every used key is present, and `site/content/` holds no file with a language code

#### Scenario: German page shell
- **WHEN** a test scans every HTML page of a build of a copy of the test collection `tests/fixtures/collection/` in locale `de`
- **THEN** each has `<html lang="de">`, the German skip link, exactly one `nav` in the site header with the German navigation, and the German footer, and `public/de/` and `public/en/` do not exist

#### Scenario: German page titles
- **WHEN** the same test reads the seven site pages
- **THEN** their `h1` and `<title>` carry the German titles

#### Scenario: German metadata panel
- **WHEN** a test reads `public/procedures/osdb-0002/index.html` of that build
- **THEN** its panel labels are, in order, `ID`, `Produkt`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ansatzgröße`, `Ausbeute`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Erstellt`, `Geändert`, `Vorstufen`, the molecular weight reads `180,16 g/mol`, the reaction type is a link to `/reaction_types/acylation/` reading `Acylierung` with `data-pagefind-filter="Reaktionstyp"`, and the status badge reads `Entwurf`
