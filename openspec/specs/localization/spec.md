# localization Specification

## Purpose
Define the site's one language and its interface strings, procedure variants by language code and the choice of the variant to publish, the language field, German procedures, stubs and PDFs, and the German authoring documents.
## Requirements
### Requirement: Site language
The site SHALL be built in one language, named by `locale` in `site/hugo.toml`, which is `"de"` in the shipped file. The language is the locale's first subtag, lowercased (`de` for `de` or `de-AT`), and must be `de` or `en`; any other locale makes the build fail with a message naming the file. `pipeline.site_language(site)` returns it. `site/hugo.toml` has no `languages` table and no `defaultContentLanguage`; the overlay sets `defaultContentLanguage` to the language. The site has no language switch, no `/de/` or `/en/` directory, and every page has `<html lang="<language>">`.

#### Scenario: Site locale
- **WHEN** a test loads `site/hugo.toml` and calls `site_language` on it and on files whose locale is `de-AT`, `en_GB`, `fr` or missing
- **THEN** the shipped locale is `de` with no `languages` or `defaultContentLanguage` key, `site_language` returns `de`, `de` and `en` for the first three, and raises ValueError for the last two

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

### Requirement: German reaction-type labels
Every entry of `site/data/reaction_types.toml` SHALL have, besides `label`, a non-empty string `label_de`. A German site shows `label_de` wherever an English one shows `label`; an entry without `label_de` shows `label`. The reaction-type lists of `/reaction_types/` and of the catalogue's reaction-type facet are ordered by the shown label. The validator refuses, as a configuration error, a vocabulary with a `label_<language>` that is not a non-empty string.

#### Scenario: Vocabulary with German labels
- **WHEN** a test loads the shipped vocabulary, and runs the validator with a vocabulary whose entry has `label_de = " "`
- **THEN** every shipped entry has a non-empty `label_de`, and the validator exits 2 naming `label_de`

#### Scenario: German labels for reaction types
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html`, the reaction-type list of `public/reaction_types/index.html` and the reaction-type facet of `public/procedures/index.html`, of a German build
- **THEN** the term page's `h1` is `Aldolkondensation` and its title `Aldolkondensation | OrgSynDB`
- **AND** both lists show the German labels in alphabetical order

### Requirement: Procedure variants
A procedure file's name MAY carry a language code, `de` or `en`, before its suffix: `OSDB-0001-x.de.md`, `OSDB-0001-x.en.org`. Files with the same `id` are variants of one procedure; an ID may occur once per code and once without one. Every variant SHALL have the same base name (the name without code and suffix) and the same value, or absence, of `status`, `reaction_types`, `tags`, `yield_percent`, `precursors`, `structure_image`, `product.formula`, `product.mw`, `product.smiles` and `product.cas` as the reference variant: the untagged file, else the `.de` file. Numbers compare by value, so `85` and `85.0` agree; other values compare by value and type. A mismatch is an error on the other variant, under the field's name (`file_name` for the base name), naming the reference's path. Any other field, and the body, may differ. A precursor may be any procedure ID, whatever the languages of its variants.

#### Scenario: A translation shares its ID and facts
- **WHEN** a run examines the baseline as `OSDB-0100-baseline.md` and, as `OSDB-0100-baseline.de.md`, the baseline with German headings and a different title, product name, hazards, authors and `scale = "25,0 mmol"`
- **THEN** it exits 0 and prints nothing
- **AND** when the German file instead changes `yield_percent`, `status`, `tags`, `product.mw` or adds `precursors`, it reports an error under that field on the German file, naming `OSDB-0100-baseline.md`

#### Scenario: A translation shares its ID and facts (integer and float)
- **WHEN** a run examines an untagged file with `yield_percent = 85` and `mw = 88`, and its `.de` variant with `85.0` and `88.0`
- **THEN** it exits 0 and prints nothing, while `yield_percent = true` in the variant is still an error

#### Scenario: A translation shares its ID and facts (no untagged file)
- **WHEN** a run examines `OSDB-0100-baseline.de.md` and an `OSDB-0100-baseline.en.md` with a different `yield_percent`
- **THEN** it reports exactly one error, field `yield_percent`, on the `.en` file, naming `OSDB-0100-baseline.de.md`

#### Scenario: Variants share a base name
- **WHEN** a run examines `OSDB-0100-baseline.md` and `OSDB-0100-other.de.md` with the same ID
- **THEN** it reports exactly one error, field `file_name`, on the German file, containing `OSDB-0100-baseline.de.md`

#### Scenario: Precursors in any language
- **WHEN** an untagged procedure lists as precursor an ID that only a `.de` file carries
- **THEN** the run reports no `precursors` problem

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

### Requirement: The language field
A procedure MAY carry the front-matter field `language`, `"de"` or `"en"`; any other value is an error. When the file name has a code, the field SHALL name the same language. A procedure page whose `language` differs from the site's carries `lang="<language>"` on `header.procedure-header` and on `article.procedure`.

#### Scenario: The language field
- **WHEN** a run examines an untagged file with `language = "de"` and German headings; one with `language = "fr"`; a `.de` file with `language = "en"`; and an untagged file with `language = "de"` and English headings
- **THEN** the first is clean, the second and third give one `language` error each, and the fourth warns `missing section "Zusammenfassung"`

#### Scenario: A procedure in another language is marked
- **WHEN** the partial build above publishes OSDB-0100 from its `.en` file and OSDB-0001 from its untagged file
- **THEN** OSDB-0100's header and article carry `lang="en"`, and OSDB-0001's article carries no `lang`

### Requirement: German procedures
A procedure in German SHALL meet the body-section rules of the procedure-schema spec with the German section names `Zusammenfassung`, `Reagenzien`, `Durchführung`, `Aufarbeitung und Reinigung`, `Charakterisierung`, `Anmerkungen`, `Gefahren und Entsorgung` and `Literatur`. A file's section set is that of its code, else of its `language`, else the set that gives the fewer problems. Its Reagents table has the columns `Reagenz | CAS | M (g/mol) | Menge | mmol | Äquiv.`, and the table hook marks the cells of `M (g/mol)` and `Äquiv.` as numeric, like those of `MW (g/mol)` and `Equiv`.

#### Scenario: A German procedure has German sections
- **WHEN** a run examines the baseline with German headings as `OSDB-0100-baseline.de.md`, and then the unchanged baseline under that name
- **THEN** the first run is clean, and the second reports one `missing section` warning for each German section name

#### Scenario: Sections of a file without a language code
- **WHEN** a run examines the untagged baseline with English headings, with German headings, and with German headings whose `Anmerkungen` is renamed
- **THEN** the first two are clean, and the third gives exactly one warning, `missing section "Anmerkungen"`

### Requirement: German search index
Pagefind SHALL index the procedure pages under the site's language.

#### Scenario: German search index
- **WHEN** a test searches the `de` index of a German build of a copy of the test collection `tests/fixtures/collection/` under Node, through the catalogue's searcher and with plain Pagefind searches
- **THEN** the searcher finds exactly OSDB-0001 and OSDB-0008 for `Verseifung` and finds OSDB-0008 for `Zimtsäure`, the filter names are exactly `id`, and every result title is a published title

### Requirement: Stubs in a language
`tools/orgsyndb new` SHALL accept `--lang LANG`, where `LANG` is `de` or `en`; any other value is a usage error (exit 2) naming `--lang`. With `--lang`, it fills `templates/procedure.<LANG>.org` (or `.md` with `--md`), the English template for `en`, exactly as it fills the English template, and names the file `OSDB-NNNN-<slug>.<LANG>.org` or `.md`. Without `--lang` it behaves as before. The slug of a German title has `ä`, `ö`, `ü`, `ß` (and capitals) written out as `ae`, `oe`, `ue`, `ss` before the ASCII folding. The German templates carry the same keyword or anchor lines as the English ones, German comments and the German section headings. Once their placeholders are filled, the German Markdown template validates cleanly, and the German Org template passes the export's Org checks (org-export "Org sources and their problems").

#### Scenario: German stub
- **WHEN** a test calls `new_procedure` with `language` `de` at `2026-10-19T17:42:05+02:00` for the Org title `Größe Säure`, and then for the Markdown title `Ölsäure`, in an empty collection
- **THEN** it creates `org/procedures/OSDB-0001-groesse-saeure.de.org` and `md/procedures/OSDB-0002-oelsaeure.de.md`
- **AND** the Org stub has `#+TITLE: Größe Säure`, `#+CREATED: [2026-10-19 Mon 17:42:05]` and `* Zusammenfassung`, and the Markdown stub validates without any problem line

#### Scenario: German templates
- **WHEN** a test fills `templates/procedure.de.md` with `OSDB-0001` and validates it as `OSDB-0001-vorlage.de.md`, and compares the keyword lines of the two Org templates
- **THEN** the run is clean, the Markdown headings are the eight German sections in order, and both Org templates have the same keyword lines in the same order

#### Scenario: German Org template passes the Org checks
- **WHEN** an ERT test copies `templates/procedure.de.org` to a temporary directory as `OSDB-0001-vorlage.de.org`, replacing every `OSDB-0000` with `OSDB-0001` and every `osdb-0000` with `osdb-0001`, and calls `osdb-org-examine` on that directory
- **THEN** it returns no problem and one source, whose stem is `OSDB-0001-vorlage.de`, so that its export is named `OSDB-0001-vorlage.de.md`

### Requirement: German PDFs
A German site's procedure PDFs SHALL show German first-page facts and footer: `· Status <German status> · zuletzt geändert <time>` and `Seite <i> von <n>`.

#### Scenario: German first page
- **WHEN** a test runs `pdf` on a copy of the test collection `tests/fixtures/collection/` in locale `de`
- **THEN** `pdf/` holds exactly `<stem>.pdf` for each published file, `pdf/OSDB-0002-aspirin.de.pdf` starts with `http://127.0.0.1:8000/procedures/osdb-0002/ · OSDB-0002 · Status Entwurf · zuletzt geändert`, and every page has the line `Seite <i> von <n>`

### Requirement: German authoring documentation
The application SHALL ship German versions of the co-worker guide, the Org guide and the schema reference: `docs/AUTHORING.de.md`, `docs/AUTHORING-ORG.de.org` and `docs/SCHEMA.de.md`. Each covers the same steps and rules as its English original. The README stays English and links both versions.

#### Scenario: German guides exist
- **WHEN** a reviewer lists `docs/` and reads the README
- **THEN** the three German documents exist, and the README links them under its authoring references

### Requirement: German style guide and glossary
The application SHALL ship `docs/STYLE.de.md`, a style guide for the text of German procedures, and `docs/GLOSSARY.de.md`, a glossary for it. Both are written in German for native and non-native authors. English appears only in the glossary tables, as each entry's English equivalent; the running text of both documents contains no English sentences or glosses. The style guide SHALL cover at least: the instruction form of the steps in `Durchführung` and `Aufarbeitung und Reinigung`; the tense and voice of observations and of `Charakterisierung`; numbers, units and abbreviations; current spelling and nomenclature against the historical spellings of older German literature; and the established German term against the anglicism or calque. It SHALL name the twentieth-century German practical textbooks and handbooks it rests on, and cite them where a rule is drawn from them. The glossary SHALL hold at least 500 entries, counting terms, fixed phrases and reusable sentences specific to organic synthesis, grouped by topic; every entry gives its English equivalent, and every entry for a form to avoid names the form to use instead. The README lists both documents under its authoring references; `docs/AUTHORING.de.md` and `docs/AUTHORING-ORG.de.org` point to the style guide where they ask for the procedure text, and `docs/AUTHORING.md` and `docs/AUTHORING-ORG.org` point to it in their sections on writing in German, so that each German guide still covers the same rules as its English original.

#### Scenario: Style guide and glossary exist
- **WHEN** a reviewer lists `docs/` and reads the README and the four authoring guides
- **THEN** `docs/STYLE.de.md` and `docs/GLOSSARY.de.md` exist, the README links both under its authoring references, each German authoring guide links the style guide in its section on writing the procedure text, and each English authoring guide links it in its section on writing in German

#### Scenario: Style guide covers its topics and sources
- **WHEN** a reviewer reads `docs/STYLE.de.md`
- **THEN** it has a section for each topic the requirement lists, names the historical German sources it rests on with enough bibliographic detail to find them, and contains no English sentences or glosses

#### Scenario: Glossary size and shape
- **WHEN** a reviewer counts the entries of `docs/GLOSSARY.de.md`
- **THEN** there are at least 500, every entry has a German form and an English equivalent, and every entry marked as a form to avoid names its replacement

