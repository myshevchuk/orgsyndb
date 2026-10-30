## ADDED Requirements

### Requirement: Procedure section tabs
The catalogue at `/procedures/`, the taxonomy pages `/reaction_types/`, `/tags/` and `/authors/`, and every term page SHALL have, as the first element of `main`, a `nav.section-tabs` carrying `aria-label="Procedures"`. It holds a `ul` whose `li` entries each hold one link, in this order: `/procedures/` with the text `All procedures`, `/reaction_types/` with `Reaction types`, `/tags/` with `Tags` and `/authors/` with `Authors`. The link whose URL is the page's own URL carries `aria-current="page"`; on a term page the link of its taxonomy carries `aria-current="true"`. No other tab carries `aria-current`, and no other page has a `nav.section-tabs`.

On screen the tabs form one row above the page's `h1`, wrapping on narrow windows, and the current tab is marked by more than colour alone.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

#### Scenario: Tabs on the listing pages
- **WHEN** a test scans `/procedures/`, the three taxonomy pages and every term page after a theme build in locale `en`
- **THEN** each page's `main` begins with `nav.section-tabs` carrying `aria-label="Procedures"`, whose links are the four stated targets and texts in order
- **AND** `/procedures/` and each taxonomy page mark their own tab with `aria-current="page"`, each term page marks its taxonomy's tab with `aria-current="true"`, and no other tab carries `aria-current`

#### Scenario: No tabs elsewhere
- **WHEN** a test scans every other HTML file under `public/` except files under `public/pagefind/`, after the same build
- **THEN** none has a `nav.section-tabs`

#### Scenario: Tabs in a browser
- **WHEN** the orchestrator opens `/procedures/`, `/tags/` and a reaction-type term page in a browser at 1280 and at 500 CSS pixels, light and dark (manual verification, tasks.md section 3)
- **THEN** the tabs sit in one row above the `h1`, wrap at 500 pixels without horizontal scrolling, and the current tab is underlined as well as coloured

## MODIFIED Requirements

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` holding, in this order:
  - `a.site-title`, linking `/` with the text `OrgSynDB`;
  - a `nav` element carrying `aria-label="Site"`, which links, in this order, to `/procedures/` and `/help/`, with the texts `Procedures` and `Help`. The header holds no other `nav`;
  - `form.site-search` with `role="search"` and `method="get"`, holding one `input` with `type="search"` and `name="q"`, and a `button` with `type="submit"` and the text `Search`. On the catalogue and term pages it is the catalogue's search form, with the `action`, attributes and texts that site-catalogue "Catalogue controls" gives. On every other page its `action` resolves to `/procedures/`, and its input carries `aria-label="Search procedures"` and the placeholder `Product, CAS, SMILES or keyword`;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures · built <time>`, where `<time>` is a `time` element whose `datetime` is the time the site was built, as an RFC 3339 date-time, and whose text is that time as `YYYY-MM-DD HH:MM`. Every page of one build shows the same time.

The navigation link whose URL is the page's own URL carries `aria-current="page"`. Otherwise the link of the section the page lies in carries `aria-current="true"`: every procedure page, `/reaction_types/`, `/tags/`, `/authors/` and their term pages lie in `/procedures/`; every help page lies in `/help/`. No other navigation link carries `aria-current`. Every page has exactly one `input` with `name="q"`: the header's.

On screen, the site title and the navigation sit at the start of the header row and the search form at its end, so that the header has the same height, and its title, navigation and search form the same positions, on every page at a given window width. Every page's `h1` has the same font size.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, the interface string named by the page's `title_key` where it has one, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build in locale `en`
- **THEN** each has the skip link, the site title, the site header with the two navigation links in order and then `form.site-search`, one `main#main`, the footer text with its `time`, the same on every page, both `meta` elements, exactly one `h1`, no heading-level jump greater than one, and exactly one `input[name=q]`, the header's
- **AND** on every page except `/procedures/` and the term pages the form's `action` resolves to `/procedures/` and its input has the stated `aria-label` and placeholder

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build in locale `en`
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

#### Scenario: Current section in the navigation
- **WHEN** a test scans the home page, `/procedures/`, a procedure page, the three taxonomy pages, a term page of each taxonomy, the help index and a help page after a theme build
- **THEN** the home page marks no navigation link; `/procedures/` marks its own link with `aria-current="page"`; the procedure page, the three taxonomy pages and the three term pages mark `/procedures/` with `aria-current="true"`; `/help/` marks its own link with `page`; and the help page `/help/schema/` marks `/help/` with `true`

#### Scenario: The header does not move between pages
- **WHEN** the orchestrator measures the header and the `h1` of the home page, `/procedures/`, a term page, a procedure page and the help index in a browser at 1280 and at 500 CSS pixels (manual verification, tasks.md section 3)
- **THEN** at each width the header has the same height, the site title, the navigation and the search form the same positions and sizes, and the `h1` the same font size on every page

### Requirement: Taxonomy and term pages
For each taxonomy, `reaction_types`, `tags` and `authors`, the site SHALL publish:
- **A taxonomy page.** It is a compact directory: its `h1` is `Reaction types`, `Tags` or `Authors`, followed by a `ul.term-list` with one `li` per term in use, ordered by the link text, holding a link to the term page and then ` ` and `span.count` reading `(<n>)`, `n` the term's procedure count. The link text is the vocabulary label for reaction types, the tag for tags, and the author's name as written for authors.
- **A term page per term.** It is a catalogue page with the term as its fixed scope (site-catalogue "Catalogue pages" and "Fixed scope on term pages"). Its `h1` is the same text as the term's link.

Each directory is linked from the section tabs, from the home page's browse list and from its catalogue facet; the metadata panel's reaction-type, tag and author links lead to the term pages.

#### Scenario: Every term page lists the right procedures
- **WHEN** a test scans every term page under `public/reaction_types/`, `public/tags/` and `public/authors/` after a theme build, and computes each term's procedures from the content files' `reaction_types`, `tags` and `authors`
- **THEN** each term in the front matter has a term page, its catalogue table's rows are exactly that term's IDs in ascending order, and the taxonomy page links it with the correct count and text, in order
