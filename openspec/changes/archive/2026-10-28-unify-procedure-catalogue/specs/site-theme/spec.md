## MODIFIED Requirements

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` holding:
  - `a.site-title`, linking `/` with the text `OrgSynDB`;
  - a `nav` element carrying `aria-label="Site"`, which links, in this order, to `/procedures/`, `/reaction_types/` and `/help/`, with the texts `Procedures`, `Reaction types` and `Help`. The header holds no other `nav`;
  - on every page except the catalogue and term pages (site-catalogue "Catalogue pages"), after the `nav`, `form.site-search` with `role="search"`, `method="get"` and an `action` resolving to `/procedures/`, holding one `input` with `type="search"`, `name="q"`, `aria-label="Search procedures"` and the placeholder `Search procedures`, and a `button` with `type="submit"` and the text `Search`;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures`.

The navigation link whose URL is the page's own URL carries `aria-current="page"`. Otherwise the link of the section the page lies in carries `aria-current="true"`: every procedure page, `/tags/`, `/authors/` and their term pages lie in `/procedures/`; every reaction-type term page lies in `/reaction_types/`; every help page lies in `/help/`. No other navigation link carries `aria-current`. Every page has exactly one `input` with `name="q"`.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, the interface string named by the page's `title_key` where it has one, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build in locale `en`
- **THEN** each has the skip link, the site title, the site header with the three navigation links in order, one `main#main`, the footer text, both `meta` elements, exactly one `h1`, no heading-level jump greater than one, and exactly one `input[name=q]`
- **AND** the header holds `form.site-search` with the stated attributes on every page except `/procedures/` and the term pages, and on those it holds no form

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build in locale `en`
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

#### Scenario: Current section in the navigation
- **WHEN** a test scans the home page, `/procedures/`, a procedure page, the three taxonomy pages, a term page of each taxonomy, the help index and a help page after a theme build
- **THEN** the home page marks no navigation link; `/procedures/` marks its own link with `aria-current="page"`; the procedure page, `/tags/`, `/authors/`, the tag term page and the author term page mark `/procedures/` with `aria-current="true"`; `/reaction_types/` marks its own link with `page` and its term page with `true`; `/help/` marks its own link with `page`; and the help page `/help/schema/` marks `/help/` with `true`

### Requirement: Stylesheets by medium
The theme SHALL build three stylesheets with Hugo Pipes functions available in the standard Hugo build (`resources.Get`, `resources.Concat`, `minify`, `fingerprint`), and link them from every page in this order:
1. **base**, from `site/assets/css/tokens.css` and `base.css`, with no `media` attribute;
2. **screen**, from `site/assets/css/screen.css`, with `media="screen"`;
3. **print**, from `site/assets/css/print.css`, with `media="print"`.

Further rules:
- No page links any other stylesheet.
- The string `prefers-color-scheme` occurs in `screen.css` and in no other source stylesheet.
- No source stylesheet declares the `color-scheme` or `clip-path` property; `prefers-color-scheme` in a media query is not such a declaration.

#### Scenario: Three links on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build
- **THEN** each has exactly the three site stylesheet links in order, with the stated `media` values, and no other stylesheet link
- **AND** each of the three resolves to a file under `public/css/`

#### Scenario: Dark mode only on screen
- **WHEN** a test reads the four source stylesheets
- **THEN** `prefers-color-scheme: dark` occurs only in `screen.css`, and none of them has a declaration whose property is `color-scheme` or `clip-path`

### Requirement: Colour tokens and contrast
The theme's colours SHALL be CSS custom properties written as six-digit hex values:
- the light set, on `:root` in `site/assets/css/tokens.css`;
- the dark set, on `:root` inside `@media (prefers-color-scheme: dark)` in `site/assets/css/screen.css`.

Both sets define `--bg`, `--fg`, `--muted`, `--border`, `--surface`, `--link`, `--focus`, `--banner-bg`, `--banner-fg`, `--draft-bg`, `--draft-fg`, `--checked-bg`, `--checked-fg`, `--retired-bg` and `--retired-fg`. In each set, these pairs meet the WCAG 2 contrast ratio:
- at least 4.5:1 for each text pair: `--fg`/`--bg`, `--muted`/`--bg`, `--link`/`--bg`, `--fg`/`--surface`, `--muted`/`--surface`, `--link`/`--surface`, `--banner-fg`/`--banner-bg`, `--draft-fg`/`--draft-bg`, `--checked-fg`/`--checked-bg` and `--retired-fg`/`--retired-bg`;
- at least 3:1 for `--focus`/`--bg`.

No stylesheet sets a `--pagefind-ui-` variable.

#### Scenario: Contrast in both schemes
- **WHEN** a test parses the custom properties of both sets from the source files and computes the WCAG relative-luminance contrast of each listed pair
- **THEN** every token is defined in both sets, every pair meets its threshold, and no source stylesheet declares a property beginning with `--pagefind-ui-`

### Requirement: Measure and tables
The screen layout SHALL prioritize desktop browsers with a shell up to 96rem wide, set in the system sans-serif stack; printed pages keep the text face of `tokens.css`. Running procedure paragraphs and lists SHALL keep a reading measure up to 78ch, while procedure tables SHALL use their available column width. Narrower windows SHALL stack the columns in document order, and wide tables SHALL scroll within their own containers. Every Markdown table SHALL be rendered by `site/layouts/_markup/render-table.html` as follows:
- The `<table>` is the only child of a `div.table-scroll` with `tabindex="0"`, `role="region"` and a non-empty `aria-label`.
- Each header cell is a `th` with `scope="col"`.
- Every cell of a column whose header text is `CAS`, `MW (g/mol)`, `mmol` or `Equiv` carries `class="num"`.
- A newline separates adjacent cells in the output.

The screen stylesheet gives `.table-scroll` `overflow-x: auto`, so a wide table scrolls inside its own container. The base stylesheet gives `.num` cells `white-space: nowrap` and right alignment. Below 55rem, the screen stylesheet gives `.home-layout` and `.catalogue-layout` the single column `minmax(0, 1fr)` and `.procedure` `display: block`.

#### Scenario: Reagents tables are wrapped and marked
- **WHEN** a test scans every procedure page after a theme build
- **THEN** the table under the `Reagents` heading is the only child of a `div.table-scroll` with the three attributes, its header cells read `Reagent`, `CAS`, `MW (g/mol)`, `Amount`, `mmol` and `Equiv`, and exactly the cells of columns 2, 3, 5 and 6 carry `class="num"`

#### Scenario: Desktop workspace
- **WHEN** a browser displays the home page and `/procedures/` at 1280 CSS pixels or wider
- **THEN** the home page shows the recent list and the browse list in adjacent columns
- **AND** the catalogue shows the facets as a sidebar beside the results, and its table uses the remaining width

#### Scenario: Procedure reference and text
- **WHEN** a browser displays a procedure at 1280 CSS pixels or wider
- **THEN** the body occupies a reading column on the left and the structure and metadata occupy a margin column on the right, without a panel border or background
- **AND** prose has a bounded reading measure and wide tables scroll locally
- **AND** the details stay first in document order, so print and the search index show them before the body

#### Scenario: Print keeps document flow
- **WHEN** a procedure is printed or rendered to an A4 PDF
- **THEN** the details, structure and body retain their single-column order

#### Scenario: Narrow windows stack the columns
- **WHEN** a test reads the declarations that `screen.css` applies to a window 500 CSS pixels wide
- **THEN** `.home-layout` and `.catalogue-layout` have `grid-template-columns: minmax(0, 1fr)` and `.procedure` has `display: block`
- **AND** a browser at that width shows the home page's recent list above its browse list, the catalogue's results with the facets behind the Filters toggle and the table scrolling in its own container, and a procedure's details, structure and body in a single column, in that order

### Requirement: Home page
The home page's `main` SHALL contain, in this order:
- `div.home-intro`, holding the `h1` `OrgSynDB` and a `p.lede` with the text `The group's synthetic procedures, written in Org or Markdown and checked against one schema.`;
- `div.home-layout`, holding:
  - `section.home-recent`, with the `h2` `Recently updated`, then an `ol.recent-list` with one `li` per procedure for the first five published procedures, or all when there are fewer, ordered by `lastmod` as an instant, newest first, and by `id` ascending for equal instants. Each `li` holds an `a` linking the procedure page whose text is `<id> <title>`, then `<time datetime="<RFC 3339 lastmod>">YYYY-MM-DD</time>`. After the list, a `p` links `/procedures/?sort=modified` with the text `All procedures, recently updated first`;
  - `section.home-browse`, with the `h2` `Browse`, then a `ul.browse-list` whose `li` entries hold, in this order, a link and then ` ` and a `span.count` reading `(<n>)`: `All procedures` to `/procedures/`, `n` the number of published procedures; `Draft procedures` to `/procedures/?status=draft`, `n` the number whose `status` is `draft`; `Reaction types` to `/reaction_types/`, `Tags` to `/tags/` and `Authors` to `/authors/`, each `n` the number of terms of that taxonomy in use.

The counts are computed from the published procedures and written with the site language's digit grouping. The home page's `main` holds no form, no `input` and no procedure table.

#### Scenario: Home page content
- **WHEN** a test scans `public/index.html` of a theme build that adds the catalogue fixtures to the test collection, in locale `en`
- **THEN** the recent list holds the first five procedures in the computed order, each ID once, with the stated link texts and dates, and two fixtures whose `lastmod` is the same instant are ordered by ID
- **AND** the browse list has the five entries in order, with the stated targets, and counts equal to those computed from the published content files
- **AND** `main` has the link to `/procedures/?sort=modified`, and no `form`, `input` or `table`

### Requirement: Taxonomy and term pages
For each taxonomy, `reaction_types`, `tags` and `authors`, the site SHALL publish:
- **A taxonomy page.** It is a compact directory: its `h1` is `Reaction types`, `Tags` or `Authors`, followed by a `ul.term-list` with one `li` per term in use, ordered by the link text, holding a link to the term page and then ` ` and `span.count` reading `(<n>)`, `n` the term's procedure count. The link text is the vocabulary label for reaction types, the tag for tags, and the author's name as written for authors.
- **A term page per term.** It is a catalogue page with the term as its fixed scope (site-catalogue "Catalogue pages" and "Fixed scope on term pages"). Its `h1` is the same text as the term's link.

Each directory is linked from the home page's browse list, from its catalogue facet, and from the scope line of its term pages; the metadata panel's reaction-type, tag and author links lead to the term pages.

#### Scenario: Every term page lists the right procedures
- **WHEN** a test scans every term page under `public/reaction_types/`, `public/tags/` and `public/authors/` after a theme build, and computes each term's procedures from the content files' `reaction_types`, `tags` and `authors`
- **THEN** each term in the front matter has a term page, its catalogue table's rows are exactly that term's IDs in ascending order, and the taxonomy page links it with the correct count and text, in order

### Requirement: Content does not need JavaScript
Every procedure, catalogue, taxonomy, term, help and home page SHALL show all of its content without running JavaScript. Scripts add only these:
- `site/assets/js/site.js` reveals and wires the print button (`window.print()`) and the SMILES copy button.
- `site.js` replaces the print-facts URL with `location.href` when the protocol is `http:` or `https:`.
- The copy button writes the SMILES string with the Clipboard API. When that fails or is unavailable, it selects the SMILES text instead.
- The catalogue script, on the catalogue and term pages, reveals the catalogue's controls and runs its search, filters, sorting and views (site-catalogue).

In the published HTML, the print button (`data-print`) and the SMILES copy button (`data-copy-smiles`) carry `hidden`, and only `site.js` reveals them. No other button carries `hidden`. Every button of a catalogue lies inside an element that carries `data-catalogue-controls` and `hidden`, which only the catalogue script reveals. The header search's submit button is visible and works without JavaScript.

#### Scenario: Static HTML holds the content
- **WHEN** a test scans every procedure page after a theme build, without running scripts
- **THEN** the metadata values, the rendered body sections and the links are present in the HTML, every `button` with `data-print` or `data-copy-smiles` has the `hidden` attribute, and no other `button` on any page under `public/` has it
- **AND** every `button` of a page's `div.catalogue` lies inside an element with `data-catalogue-controls` and `hidden`

#### Scenario: Buttons work in a browser
- **WHEN** the orchestrator opens a procedure page in a browser with JavaScript (manual verification, tasks.md section 6)
- **THEN** the print button is visible and opens the print dialog, the Copy button copies or selects the SMILES string, and with JavaScript disabled neither button is shown and the page is otherwise unchanged
- **AND** with JavaScript disabled, submitting the header search of a procedure page loads `/procedures/?q=<term>`, which shows the `noscript` note and every procedure by ID, and no catalogue control

## REMOVED Requirements

### Requirement: Procedure lists and their order
**Reason**: `/procedures/` is the catalogue, which lists every procedure by ID without JavaScript and offers every order through its sort select (site-catalogue). `/procedures-by-date/`, the list tools and the sort links are gone; the home page links the catalogue sorted by modification date.
