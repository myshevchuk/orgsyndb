## MODIFIED Requirements

### Requirement: Interface strings
Every text that a layout shows SHALL come from the interface strings of the site's language, `site/i18n/de.toml` or `site/i18n/en.toml`, looked up with `T`; a page of `site/content/` names its title by a `title_key` front-matter value, a key of those files. The two files have the same keys, and every value is a non-empty string. The English strings are the texts that the site-theme, site-search and print-layout specs name; a German site shows the German string in their place. In particular a German site shows:
- the skip link `Zum Inhalt springen`, the navigation `Vorschriften`, `Reaktionstypen`, `Schlagwörter`, `Autoren`, `Suche` (in a `nav` with `aria-label="Website"`), and the footer `OrgSynDB · interne Vorschriften`;
- the page titles `Alle Vorschriften`, `Alle Vorschriften nach Datum`, `Reaktionstypen`, `Schlagwörter`, `Autoren` and `Suche`;
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
- **WHEN** the same test reads the six site pages
- **THEN** their `h1` and `<title>` carry the German titles

#### Scenario: German metadata panel
- **WHEN** a test reads `public/procedures/osdb-0002/index.html` of that build
- **THEN** its panel labels are, in order, `ID`, `Produkt`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ansatzgröße`, `Ausbeute`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Erstellt`, `Geändert`, `Vorstufen`, the molecular weight reads `180,16 g/mol`, the reaction type is a link to `/reaction_types/acylation/` reading `Acylierung` with `data-pagefind-filter="Reaktionstyp"`, and the status badge reads `Entwurf`

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
- **THEN** nine procedures are published, OSDB-0001 from the untagged English file, OSDB-0100 from the `.en` file, and the German home page says `Alle 9 Vorschriften`

### Requirement: German search index
Pagefind SHALL index the procedure pages under the site's language.

#### Scenario: German search index
- **WHEN** a test queries the `de` index of a German build of a copy of the test collection `tests/fixtures/collection/` under Node
- **THEN** `Verseifung` finds exactly OSDB-0001 and OSDB-0008, the filter `Reaktionstyp` = `Hydrolyse` finds the same two, the filter names are `Autor`, `Reaktionstyp`, `Schlagwort` and `Status`, and every result title is a published title

### Requirement: German PDFs
A German site's procedure PDFs SHALL show German first-page facts and footer: `· Status <German status> · zuletzt geändert <time>` and `Seite <i> von <n>`.

#### Scenario: German first page
- **WHEN** a test runs `pdf` on a copy of the test collection `tests/fixtures/collection/` in locale `de`
- **THEN** `pdf/` holds exactly `<stem>.pdf` for each published file, `pdf/OSDB-0002-aspirin.de.pdf` starts with `http://127.0.0.1:8000/procedures/osdb-0002/ · OSDB-0002 · Status Entwurf · zuletzt geändert`, and every page has the line `Seite <i> von <n>`
