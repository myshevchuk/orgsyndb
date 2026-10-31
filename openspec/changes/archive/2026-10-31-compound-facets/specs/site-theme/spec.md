## MODIFIED Requirements

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` holding, in this order:
  - `a.site-title`, linking `/` with the text `OrgSynDB`;
  - a `nav` element carrying `aria-label="Site"`, which links, in this order, to `/procedures/`, `/compounds/`, `/sequences/` and `/help/`, with the texts `Procedures`, `Compounds`, `Sequences` and `Help`. The header holds no other `nav`;
  - `form.site-search` with `role="search"` and `method="get"`, holding one `input` with `type="search"` and `name="q"`, and a `button` with `type="submit"` and the text `Search`. On the catalogue, the term pages and `/general-procedures/` it is the catalogue's search form, with the `action`, attributes and texts that site-catalogue "Catalogue controls" gives, and on `/compounds/` it is the compound catalogue's, as site-catalogue "Compound catalogue" gives. On every other page its `action` resolves to `/procedures/`, and its input carries `aria-label="Search procedures"` and the placeholder `Product, CAS, SMILES or keyword`;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures · built <time>`, where `<time>` is a `time` element whose `datetime` is the time the site was built, as an RFC 3339 date-time, and whose text is that time as `YYYY-MM-DD HH:MM`. Every page of one build shows the same time.

The navigation link whose URL is the page's own URL carries `aria-current="page"`. Otherwise the link of the section the page lies in carries `aria-current="true"`: every procedure page, `/general-procedures/`, `/reaction_types/`, `/tags/`, `/authors/` and their term pages lie in `/procedures/`; every compound page lies in `/compounds/`; every sequence page lies in `/sequences/`; every help page lies in `/help/`. No other navigation link carries `aria-current`. Every page has exactly one `input` with `name="q"`: the header's.

On screen, the site title and the navigation sit at the start of the header row and the search form at its end, so that the header has the same height, and its title, navigation and search form the same positions, on every page at a given window width. Every page's `h1` has the same font size.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, the interface string named by the page's `title_key` where it has one, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build in locale `en`
- **THEN** each has the skip link, the site title, the site header with the four navigation links in order and then `form.site-search`, one `main#main`, the footer text with its `time`, the same on every page, both `meta` elements, exactly one `h1`, no heading-level jump greater than one, and exactly one `input[name=q]`, the header's
- **AND** on every page except `/procedures/`, `/general-procedures/`, `/compounds/` and the term pages the form's `action` resolves to `/procedures/` and its input has the stated `aria-label` and placeholder

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build in locale `en`
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

#### Scenario: Current section in the navigation
- **WHEN** a test scans the home page, `/procedures/`, a procedure page, the three taxonomy pages, a term page of each taxonomy, `/compounds/`, a compound page, `/sequences/`, a sequence page, the help index and a help page after a theme build
- **THEN** the home page marks no navigation link; `/procedures/` marks its own link with `aria-current="page"`; the procedure page, the three taxonomy pages and the three term pages mark `/procedures/` with `aria-current="true"`; `/compounds/` marks its own link with `page` and the compound page marks it with `true`; `/sequences/` marks its own link with `page` and the sequence page marks it with `true`; `/help/` marks its own link with `page`; and the help page `/help/schema/` marks `/help/` with `true`

#### Scenario: The header does not move between pages
- **WHEN** the orchestrator measures the header and the `h1` of the home page, `/procedures/`, a term page, a procedure page and the help index in a browser at 1280 and at 500 CSS pixels (manual verification, tasks.md section 3)
- **THEN** at each width the header has the same height, the site title, the navigation and the search form the same positions and sizes, and the `h1` the same font size on every page

### Requirement: Compound directory
The page `/compounds/` SHALL be the compound catalogue (site-catalogue "Compound catalogue"), whose results end with a `table.compound-table` with the header cells `Compound`, `Formula`, `MW` and `CAS`, then one header cell for each field the collection declares with `column = true`, in declared order, holding the field's shown label, then `Made by` and `Used in`, and one body row per compound of the registry, ordered by shown name. A row holds a link to the compound's page with its shown name, the formula with each digit run in `<sub>`, `<mw> g/mol`, the CAS number or an empty cell, for each column field the compound's value written as compound-fields "Field display" states or an empty cell when the compound does not set it, and the numbers of published procedures that make it and that use it. The header and body cells of a `number` field carry the class `num`. Without JavaScript the page shows the complete table and no control.

#### Scenario: Every compound is listed
- **WHEN** a test scans `public/compounds/index.html` after a theme build in locale `en`
- **THEN** its rows are the registry's compounds, each once, ordered by name, with the stated cells, and their counts equal those computed from the published content files
- **AND** its header cells are `Compound`, `Formula`, `MW`, `CAS`, the labels of the column fields that the test collection's `orgsyndb.toml` declares, in declared order, `Made by` and `Used in`

#### Scenario: Number and boolean columns
- **WHEN** a test builds a copy of the test collection in locale `en` after adding `column = true` to the declarations of `stock` and `in_house` in its `orgsyndb.toml`, and scans `public/compounds/index.html`
- **THEN** the header cells `Stock` and `Made in house` follow `Chemical class`, the header and body cells of `Stock` carry the class `num` and those of `Made in house` do not, a compound that sets neither field has an empty cell in both columns, `ethyl-triphenylphosphoranylidene-acetate` reads `12.5 g`, and a compound with `in_house = false` reads `No`

