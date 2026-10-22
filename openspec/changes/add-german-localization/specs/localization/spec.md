## ADDED Requirements

### Requirement: Site languages
The site SHALL be built in English and German. `site/hugo.toml` sets `defaultContentLanguage = "en"`, `defaultContentLanguageInSubdir = false`, `disableDefaultLanguageRedirect = true`, and exactly two languages: `en` with `label = "English"`, `locale = "en"` and `weight = 1`, and `de` with `label = "Deutsch"`, `locale = "de"` and `weight = 2`. English pages keep the URLs that the other specs give; each German page has the same path under `/de/`. Every page that `site/content/` defines in English, by a file `X.md`, has a German twin `X.de.md`, and the `tags` and `authors` taxonomies have German list titles.

#### Scenario: Language configuration
- **WHEN** a test loads `site/hugo.toml` with `tomllib` and lists `site/content/`
- **THEN** the language keys have the stated values, and every `X.md` has an `X.de.md`, including `tags/_index.de.md` and `authors/_index.de.md`

### Requirement: Interface strings
Every text that a layout shows SHALL come from the interface strings of the page's language, `site/i18n/en.toml` or `site/i18n/de.toml`, looked up with `T`. The two files have the same keys, and every value is a non-empty string. The English strings are the texts that the site-theme, site-search and print-layout specs name; on a German page each such text is replaced by its German string. In particular a German page shows:
- the skip link `Zum Inhalt springen`, the navigation `Vorschriften`, `Reaktionstypen`, `Schlagwörter`, `Autoren`, `Suche` (in a `nav` with `aria-label="Website"`), and the footer `OrgSynDB · interne Vorschriften`;
- the panel labels `ID`, `Produkt`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ansatzgröße`, `Ausbeute`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Geprüft von`, `Erstellt`, `Geändert`, `Vorstufen`, `Verwendet in`;
- the status `Entwurf`, `geprüft` or `zurückgezogen` for `draft`, `checked` or `retired`, while the badge class stays `badge--<status>`;
- the banner `Beispieldaten – Mengenangaben nicht experimentell überprüft.`, the button `Drucken / Als PDF speichern`, the copy button `Kopieren` with the messages `Kopiert` and `Markiert: Strg+C drücken`, and the placeholder `Keine Strukturformel`;
- the Pagefind filter names `Status`, `Reaktionstyp`, `Schlagwort` and `Autor`;
- numbers of the front matter (molecular weight, yield) with a decimal comma.

The site script holds no language: the copy button carries its messages in `data-copied` and `data-selected`.

#### Scenario: Both languages have every string
- **WHEN** a test loads both i18n files and scans the layouts for `T "<key>"`
- **THEN** both files have the same keys with non-empty string values, and every key the layouts use is present

#### Scenario: German page shell
- **WHEN** a test scans every HTML page under `public/de/` after a build of the demo collection
- **THEN** each has `<html lang="de">`, the German skip link, the German navigation linking the five pages under `/de/`, and the German footer
- **AND** every other page except the Pagefind bundle has `<html lang="en">`

#### Scenario: German metadata panel
- **WHEN** a test reads `public/de/procedures/osdb-0002/index.html`
- **THEN** its panel labels are, in order, `ID`, `Produkt`, `Summenformel`, `Molmasse`, `CAS`, `SMILES`, `Ansatzgröße`, `Ausbeute`, `Reaktionstyp`, `Schlagwörter`, `Autoren`, `Erstellt`, `Geändert`, `Vorstufen`, the molecular weight reads `180,16 g/mol`, the reaction type is a link to `/de/reaction_types/acylation/` reading `Acylierung` with `data-pagefind-filter="Reaktionstyp"`, and the status badge reads `Entwurf`

### Requirement: German reaction-type labels
Every entry of `site/data/reaction_types.toml` SHALL have, besides `label`, a non-empty string `label_de`. A German page shows `label_de` wherever an English page shows `label`; an entry without `label_de` shows `label`. The reaction-type lists of the home page and of `/reaction_types/` are ordered by the label of the page's language. The validator refuses, as a configuration error, a vocabulary with a `label_<language>` that is not a non-empty string.

#### Scenario: Vocabulary with German labels
- **WHEN** a test loads the shipped vocabulary, and runs the validator with a vocabulary whose entry has `label_de = " "`
- **THEN** every shipped entry has a non-empty `label_de`, and the validator exits 2 naming `label_de`

#### Scenario: German labels for reaction types
- **WHEN** a test reads `public/de/reaction_types/aldol-condensation/index.html`, and the reaction-type lists of `public/de/index.html` and `public/de/reaction_types/index.html`
- **THEN** its `h1` is `Aldolkondensation` and its title `Aldolkondensation | OrgSynDB`
- **AND** both lists show the German labels in alphabetical order

### Requirement: Translations
A procedure file SHALL be in the language named by the code before its suffix: `OSDB-NNNN-slug.de.md` and `OSDB-NNNN-slug.de.org` are German, a name without a code is English. A German file whose ID also has an English file is that file's translation. It has the English file's base name `OSDB-NNNN-slug`, and the same value, or absence, of `status`, `reaction_types`, `tags`, `yield_percent`, `precursors`, `structure_image`, `product.formula`, `product.mw`, `product.smiles` and `product.cas`. Any other field, and the body, may differ. A mismatch is an error on the translation, under the field's name (`file_name` for the base name), naming the original's path. A German file without an English file is a German-only procedure and is not compared.

#### Scenario: A translation shares its ID and facts
- **WHEN** a run examines the baseline as `OSDB-0100-baseline.md` and, as `OSDB-0100-baseline.de.md`, the baseline with German headings and a different title, product name, hazards, authors and `scale = "25,0 mmol"`
- **THEN** it exits 0 and prints nothing
- **AND** when the German file instead changes `yield_percent`, `status`, `tags`, `product.mw` or adds `precursors`, it reports an error under that field on the German file, naming `OSDB-0100-baseline.md`

#### Scenario: A translation is named after its original
- **WHEN** a run examines `OSDB-0100-baseline.md` and a German `OSDB-0100-other.de.md` with the same ID
- **THEN** it reports exactly one error, field `file_name`, on the German file, containing `OSDB-0100-baseline.de.md`

#### Scenario: Precursors in any language
- **WHEN** an English procedure lists as precursor an ID that only a German file carries
- **THEN** the run reports no `precursors` problem

### Requirement: German procedures
A German procedure SHALL meet the body-section rules of the procedure-schema spec with the German section names `Zusammenfassung`, `Reagenzien`, `Durchführung`, `Aufarbeitung und Reinigung`, `Charakterisierung`, `Anmerkungen`, `Gefahren und Entsorgung` and `Literatur`. Its Reagents table has the columns `Reagenz | CAS | M (g/mol) | Menge | mmol | Äquiv.`, and the table hook marks the cells of `M (g/mol)` and `Äquiv.` as numeric, like those of `MW (g/mol)` and `Equiv`.

#### Scenario: A German procedure has German sections
- **WHEN** a run examines the baseline with German headings as `OSDB-0100-baseline.de.md`, and then the unchanged baseline under that name
- **THEN** the first run is clean, and the second reports one `missing section` warning for each German section name

### Requirement: Language switch and cross-language links
The site header of a page that has a translation SHALL contain a `nav.language-switch` with one link per translation, whose `hreflang` and `lang` are the translation's language and whose text is its label (`English`, `Deutsch`). A page without a translation has no language switch. Precursor and used-in links take the page of each ID in the current language, and otherwise the page in the other language, with `hreflang` set to that language. Lists, taxonomy pages and the search index of a language hold only the procedures of that language.

#### Scenario: Language switch
- **WHEN** a test reads every English procedure page of the demo collection and its German translation, and the English home page
- **THEN** each English procedure page links to `/de/procedures/<slug>/` with `hreflang="de"` and the text `Deutsch`, each German one back to `/procedures/<slug>/` with `hreflang="en"` and `English`, and the home page to `/de/`

#### Scenario: Untranslated procedure
- **WHEN** a test removes `OSDB-0001-salicylic-acid.de.org` and `OSDB-0004-4-acetylbiphenyl.de.org` from a copy of the demo collection and builds it
- **THEN** `public/de/procedures/osdb-0001/` does not exist, the English OSDB-0001 page has no language switch, the German home says `Alle 6 Vorschriften`, and the German OSDB-0002 and OSDB-0005 pages link their precursors to `/procedures/osdb-0001/` and `/procedures/osdb-0004/` with `hreflang="en"`

### Requirement: German search index
Pagefind SHALL index the German pages as language `de`, separately from the English ones, and the search page of each language searches its own index.

#### Scenario: German search index
- **WHEN** a test queries the German index of a demo build under Node
- **THEN** `Verseifung` finds exactly OSDB-0001 and OSDB-0008, the filter `Reaktionstyp` = `Hydrolyse` finds the same two, the filter names are `Autor`, `Reaktionstyp`, `Schlagwort` and `Status`, and every result title is a German title

### Requirement: German stubs
`tools/orgsyndb new` SHALL accept `--lang LANG`, where `LANG` is `en` (the default) or `de`; any other value is a usage error (exit 2) naming `--lang`. With `--lang de` it fills `templates/procedure.de.org`, or `templates/procedure.de.md` with `--md`, exactly as it fills the English template, and names the file `OSDB-NNNN-<slug>.de.org` or `.de.md`. The slug of a German title has `ä`, `ö`, `ü`, `ß` (and capitals) written out as `ae`, `oe`, `ue`, `ss` before the ASCII folding. The German templates carry the same keyword or anchor lines as the English ones, German comments and the German section headings, and validate cleanly once their placeholders are filled.

#### Scenario: German stub
- **WHEN** a test runs `pipeline.py new --lang de --now 2026-10-19T17:42:05+02:00 "Größe Säure"` and then `new --md --lang de` with `Ölsäure` in an empty collection
- **THEN** it creates `org/procedures/OSDB-0001-groesse-saeure.de.org` and `md/procedures/OSDB-0002-oelsaeure.de.md`, the Org stub has `#+TITLE: Größe Säure` and `* Zusammenfassung`, and both validate without any problem line

#### Scenario: German templates
- **WHEN** a test fills `templates/procedure.de.md` with `OSDB-0001` and validates it as `OSDB-0001-vorlage.de.md`, and compares the keyword lines of the two Org templates
- **THEN** the run is clean, the Markdown headings are the eight German sections in order, and both Org templates have the same keyword lines in the same order

### Requirement: Translated PDFs
`pdf` SHALL render a translation's page under `public/de/procedures/<slug>/` to `pdf/<stem>.pdf`, where the stem keeps the language code, as in `pdf/OSDB-0002-aspirin.de.pdf`. Its first-page facts and footer are in German: `· Status <German status> · zuletzt geändert <time>` and `Seite <i> von <n>`.

#### Scenario: PDF of a translation
- **WHEN** a test calls `pdf_jobs` for `md/procedures/OSDB-0002-aspirin.de.md` with slug `osdb-0002`
- **THEN** the job renders `public/de/procedures/osdb-0002/index.html` to `pdf/OSDB-0002-aspirin.de.pdf`

#### Scenario: German first page
- **WHEN** a test reads the first page text of `pdf/OSDB-0002-aspirin.de.pdf` after a PDF build of the demo collection
- **THEN** it contains `http://127.0.0.1:8000/de/procedures/osdb-0002/ · OSDB-0002 · Status Entwurf · zuletzt geändert` and every page has the line `Seite <i> von <n>`

### Requirement: German authoring documentation
The application SHALL ship German versions of the co-worker guide, the Org guide and the schema reference: `docs/AUTHORING.de.md`, `docs/AUTHORING-ORG.de.org` and `docs/SCHEMA.de.md`. Each covers the same steps and rules as its English original, plus writing a German procedure or a translation. The README stays English and links both versions.

#### Scenario: German guides exist
- **WHEN** a reviewer lists `docs/` and reads the README
- **THEN** the three German documents exist, and the README links them under its authoring references
