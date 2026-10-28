# site-theme Specification

## Purpose
Define the custom OrgSynDB theme: the page kinds and their content, the procedure metadata panel, precursor and used-in links, the sample banner, light and dark colour schemes, the desktop layout and accessibility basics, without third-party themes or frameworks.
## Requirements
### Requirement: Theme sources and constraints
The site SHALL be rendered by a theme written for this repository, made of these sources and no others:
- layouts in `site/layouts/`;
- stylesheets in `site/assets/css/`;
- scripts in `site/assets/js/`;
- structure images in the collection's `static/structures/`.

The following apply:
- `site/hugo.toml` sets no `theme` key, and no `themes/` directory exists under `site/`.
- No CSS or JavaScript framework or library is included, apart from the Pagefind bundle that `build` generates.
- No web font is used: no stylesheet contains `@font-face`, and no file under `public/` ends in `.woff`, `.woff2`, `.ttf`, `.otf` or `.eot`. Font stacks name system fonts and end in a generic family.
- Every `<script>` element has a `src` attribute beginning with `/js/` or `/pagefind/` before `relativeURLs` rewriting. No HTML attribute name begins with `on`.

#### Scenario: No third-party theme and no web fonts
- **WHEN** a theme build completes and a test reads `site/hugo.toml`, lists `site/`, and scans every CSS file and every file name under `public/`
- **THEN** there is no `theme` key and no `themes/` directory, no CSS file contains `@font-face`, and no published file has a font suffix

#### Scenario: Only external, local scripts
- **WHEN** a test scans every HTML file under `public/` after a theme build
- **THEN** every `<script>` has a `src` that resolves to a file under `public/js/` or `public/pagefind/`, and no element has an attribute whose name begins with `on`

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` holding, in this order:
  - `a.site-title`, linking `/` with the text `OrgSynDB`;
  - a `nav` element carrying `aria-label="Site"`, which links, in this order, to `/procedures/`, `/reaction_types/` and `/help/`, with the texts `Procedures`, `Reaction types` and `Help`. The header holds no other `nav`;
  - `form.site-search` with `role="search"` and `method="get"`, holding one `input` with `type="search"` and `name="q"`, and a `button` with `type="submit"` and the text `Search`. On the catalogue and term pages it is the catalogue's search form, with the `action`, attributes and texts that site-catalogue "Catalogue controls" gives. On every other page its `action` resolves to `/procedures/`, and its input carries `aria-label="Search procedures"` and the placeholder `Product, CAS, SMILES or keyword`;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures`.

The navigation link whose URL is the page's own URL carries `aria-current="page"`. Otherwise the link of the section the page lies in carries `aria-current="true"`: every procedure page, `/tags/`, `/authors/` and their term pages lie in `/procedures/`; every reaction-type term page lies in `/reaction_types/`; every help page lies in `/help/`. No other navigation link carries `aria-current`. Every page has exactly one `input` with `name="q"`: the header's.

On screen, the site title and the navigation sit at the start of the header row and the search form at its end, so that the header has the same height, and its title, navigation and search form the same positions, on every page at a given window width. Every page's `h1` has the same font size.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, the interface string named by the page's `title_key` where it has one, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build in locale `en`
- **THEN** each has the skip link, the site title, the site header with the three navigation links in order and then `form.site-search`, one `main#main`, the footer text, both `meta` elements, exactly one `h1`, no heading-level jump greater than one, and exactly one `input[name=q]`, the header's
- **AND** on every page except `/procedures/` and the term pages the form's `action` resolves to `/procedures/` and its input has the stated `aria-label` and placeholder

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build in locale `en`
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

#### Scenario: Current section in the navigation
- **WHEN** a test scans the home page, `/procedures/`, a procedure page, the three taxonomy pages, a term page of each taxonomy, the help index and a help page after a theme build
- **THEN** the home page marks no navigation link; `/procedures/` marks its own link with `aria-current="page"`; the procedure page, `/tags/`, `/authors/`, the tag term page and the author term page mark `/procedures/` with `aria-current="true"`; `/reaction_types/` marks its own link with `page` and its term page with `true`; `/help/` marks its own link with `page`; and the help page `/help/schema/` marks `/help/` with `true`

#### Scenario: The header does not move between pages
- **WHEN** the orchestrator measures the header and the `h1` of the home page, `/procedures/`, a term page, a procedure page and the help index in a browser at 1280 and at 500 CSS pixels (manual verification, tasks.md section 3)
- **THEN** at each width the header has the same height, the site title, the navigation and the search form the same positions and sizes, and the `h1` the same font size on every page

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

### Requirement: Procedure page structure
Each procedure page's `main` element SHALL contain, in document order:
1. the sample banner, when the requirement "Sample banner" applies;
2. `header.procedure-header`, holding:
   - `p.procedure-id`, containing the ID in an element with `data-pagefind-meta="id"`, and the status badge `span.badge.badge--<status>` whose text is the status;
   - the `h1` with the title;
   - the print facts of the print-layout spec;
   - `p.actions`, holding `button.print-button` with `type="button"`, the attribute `data-print`, the text `Print / Save as PDF` and the attribute `hidden`;
3. `article.procedure`, the only element with `data-pagefind-body`, holding in order:
   - the metadata panel;
   - the structure figure;
   - the rendered body;
   - the SMILES index element of the site-search spec.

#### Scenario: Header and body in order
- **WHEN** a test scans `procedures/osdb-0002/index.html` and `procedures/osdb-0001/index.html` after a theme build
- **THEN** each has the elements in the stated order, the `h1` and the ID lie outside the `article`, and the `article` contains the `Summary` heading after the metadata panel

### Requirement: Metadata panel
The metadata panel SHALL be a `dl.metadata`, the first element of the details wrapper at the start of `article.procedure`. It holds one `dt`/`dd` pair per field, with these labels in this order, each pair present only when the field is set:
- `ID`;
- `Product` (the `product.name`);
- `Formula`, where each digit run is wrapped in `<sub>`;
- `MW`, as `<mw> g/mol`;
- `CAS`;
- `SMILES`, as a `<code data-smiles>` with the string, followed by `button.copy-button` with `type="button"`, `data-copy-smiles`, the text `Copy` and `hidden`;
- `Scale`;
- `Yield`, as `<n> %`;
- `Reaction type`, as a link to the term page whose text is the vocabulary label;
- `Tags`, as one link per tag to its term page, with the tag as text;
- `Authors`, as one link per author to the author's term page, with the name as text;
- `Checked by`, as the names joined by `, `, not linked;
- `Created`, as `<time datetime="<RFC 3339 date>">YYYY-MM-DD HH:MM</time>`;
- `Modified`, the same for `lastmod`;
- `Precursors`, as in the requirement "Precursor and used-in links";
- `Used in`, as in the same requirement.

Whitespace separates every `</dt>` from the following `<dd>` in the published HTML.

#### Scenario: Panel of the Markdown seed
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build
- **THEN** the `dt` texts are, in order, `ID`, `Product`, `Formula`, `MW`, `CAS`, `SMILES`, `Scale`, `Yield`, `Reaction type`, `Tags`, `Authors`, `Created`, `Modified` and `Precursors`
- **AND** the values include `OSDB-0002`, `Acetylsalicylic acid`, `C9H8O4` with three `<sub>` elements, `180.16 g/mol`, `50-78-2`, `CC(=O)Oc1ccccc1C(=O)O` in `code[data-smiles]`, `20 mmol`, `75 %`, a link with text `Acylation`, links `sample-data` and `acetylation`, links `A. Example` and `C. Example`, and `<time datetime="2026-10-19T23:46:11+02:00">`

#### Scenario: Panel labels follow the canonical order on every page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** each page's `dt` texts are a subsequence of the canonical label list in its order, they include every label whose field the content file sets, and whitespace follows every `</dt>`

### Requirement: Precursor and used-in links
For each ID in a procedure's `precursors`, the `Precursors` value SHALL contain an `a.precursor` that links to that procedure's page, with the text `<ID> <title>`. The `Used in` value SHALL contain one `a.used-in` for every procedure whose `precursors` contains this procedure's `id`, linking to its page with the text `<ID> <title>`, ordered by ID. A procedure that no other lists has no `Used in` pair.

#### Scenario: Links resolve in both directions
- **WHEN** a test scans every procedure page after a theme build, resolves each `a.precursor` and `a.used-in` `href` against the page's URL, and builds the precursor relation from the content files' front matter
- **THEN** every link resolves to an existing procedure page
- **AND** for every pair where A is a precursor of B, B's page has an `a.precursor` to A and A's page has an `a.used-in` to B
- **AND** no other `a.precursor` or `a.used-in` exists

#### Scenario: The shipped chains
- **WHEN** the same test reads the pages of OSDB-0001, 0002, 0004, 0005, 0007 and 0008
- **THEN** OSDB-0002, 0005 and 0008 each have one `a.precursor`, to OSDB-0001, 0004 and 0007 respectively
- **AND** OSDB-0001, 0004 and 0007 each have one `a.used-in`, back to OSDB-0002, 0005 and 0008 respectively

### Requirement: Sample banner
A procedure page SHALL carry exactly one `p.sample-banner` with `role="note"` and the text `Sample data — quantities not experimentally verified.` when `sample-data` is among the procedure's tags, and none otherwise. The banner is the first child of `main`, lies outside `article.procedure`, and is not hidden by the print stylesheet.

#### Scenario: Every sample shows the banner
- **WHEN** a test scans every procedure page whose content file's tags include `sample-data`, after a theme build
- **THEN** each has exactly one banner with that text, outside the indexed body

#### Scenario: A procedure without the tag has none
- **WHEN** a theme build includes `tests/fixtures/theme/OSDB-0906-quoted-title.md`, whose tags do not include `sample-data`
- **THEN** `procedures/osdb-0906/index.html` has no `p.sample-banner`

### Requirement: Structure image slot
When a procedure sets `structure_image`, its page SHALL contain, after the metadata panel, a `figure.structure` holding an `img` whose `src` resolves to the published copy of the collection's `static/<structure_image>`, and whose `alt` is `Structure of <product name>`. Otherwise the page contains a `figure.structure.structure--placeholder` holding `div.structure__slot` with the text `No structure image`. The print stylesheet hides the placeholder.

#### Scenario: Image and placeholder
- **WHEN** a test scans `procedures/osdb-0003/index.html` and `procedures/osdb-0002/index.html` after a theme build
- **THEN** the first has an `img` whose resolved `src` is `public/structures/osdb-0003.svg`, which exists, with `alt` `Structure of Isopentyl acetate`
- **AND** the second has the placeholder figure and no `img`

### Requirement: Structure images are safe SVG
Every `.svg` file under the demo collection's `static/structures/` SHALL be a hand-written SVG that meets all of the following:
- It parses as XML with the root element `{http://www.w3.org/2000/svg}svg`.
- The root has a `viewBox`, `role="img"` and a child `title` with non-empty text.
- The first drawing element is a `rect` filling the view box with `fill="#fff"`.
- Every `stroke` and `fill` value other than that rectangle's is `#000` or `none`.
- No element is `script`, `foreignObject`, `image` or `use`.
- No attribute is `href` or `xlink:href`.
- No `style` attribute or element contains `url(`.
- No attribute value begins with `http:`, `https:` or `//`.

#### Scenario: Shipped structure images
- **WHEN** a test parses every `.svg` file under `examples/demo/static/structures/` with `xml.etree.ElementTree`
- **THEN** at least one file exists, `osdb-0003.svg` among them, and each meets every rule above

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

### Requirement: Org and Markdown sources render alike
A procedure SHALL render to the same HTML whichever source format it was written in. Two procedures with the same content, one exported from Org and one written in Markdown, give pages that are byte-identical once their IDs and slugs are replaced by a common placeholder.

#### Scenario: Twin fixtures
- **WHEN** a theme build includes `tests/fixtures/theme/OSDB-0904-twin.org` in `org/procedures/` and `tests/fixtures/theme/OSDB-0905-twin.md` in `md/procedures/`, which hold the same title, dates, metadata, tags, precursor and body
- **THEN** after `OSDB-0904`, `osdb-0904`, `OSDB-0905` and `osdb-0905` are replaced by `OSDB-NNNN` and `osdb-nnnn`, `procedures/osdb-0904/index.html` and `procedures/osdb-0905/index.html` are byte-identical

