## ADDED Requirements

<!-- "Integration test" is defined in the org-export spec. A "theme build"
is an integration test that runs tools/build.fish build on a temporary
repository copy holding the shipped org/ and md/ trees, plus the fixtures a
scenario names, copied from tests/fixtures/theme/ into org/procedures/ or
md/procedures/. "Procedure page" means public/procedures/<slug>/index.html.
"Scan" means parsing with Python's html.parser, without running any
JavaScript. "Shipped procedures" are the content files of build/export/ and
md/procedures/ in that copy. -->

### Requirement: Theme sources and constraints
The site SHALL be rendered by a theme written for this repository, made of these sources and no others:
- layouts in `site/layouts/`;
- stylesheets in `site/assets/css/`;
- scripts in `site/assets/js/`;
- structure images in `site/static/structures/`.

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
- a `header.site-header` with a `nav` element carrying `aria-label="Site"`. The nav links to `/procedures/`, `/reaction_types/`, `/tags/`, `/authors/` and `/search/`, with the texts `Procedures`, `Reaction types`, `Tags`, `Authors` and `Search`.
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures`.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build
- **THEN** each has the skip link, the site header with the five navigation links, one `main#main`, the footer text, both `meta` elements, exactly one `h1`, and no heading-level jump greater than one

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

### Requirement: Stylesheets by medium
The theme SHALL build three stylesheets with Hugo Pipes functions available in the standard Hugo build (`resources.Get`, `resources.Concat`, `minify`, `fingerprint`), and link them from every page in this order:
1. **base**, from `site/assets/css/tokens.css` and `base.css`, with no `media` attribute;
2. **screen**, from `site/assets/css/screen.css`, with `media="screen"`;
3. **print**, from `site/assets/css/print.css`, with `media="print"`.

Further rules:
- The search page links `/pagefind/pagefind-ui.css` as well, and no page links any other stylesheet.
- The string `prefers-color-scheme` occurs in `screen.css` and in no other source stylesheet.
- No source stylesheet declares the `color-scheme` or `clip-path` property; `prefers-color-scheme` in a media query is not such a declaration.

#### Scenario: Three links on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build
- **THEN** each has exactly the three site stylesheet links in order, with the stated `media` values, plus `pagefind-ui.css` on `search/index.html` only
- **AND** each of the three site stylesheets resolves to a file under `public/css/`, and `pagefind-ui.css`, which the Pagefind bundle provides and which is exempt from that rule, resolves to `public/pagefind/pagefind-ui.css`

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

`screen.css` sets Pagefind's UI variables `--pagefind-ui-primary`, `--pagefind-ui-text`, `--pagefind-ui-background`, `--pagefind-ui-border`, `--pagefind-ui-tag` and `--pagefind-ui-font` from these tokens.

#### Scenario: Contrast in both schemes
- **WHEN** a test parses the custom properties of both sets from the source files and computes the WCAG relative-luminance contrast of each listed pair
- **THEN** every token is defined in both sets, and every pair meets its threshold

### Requirement: Measure, responsiveness and tables
The theme SHALL limit running text to a measure of about 70 characters (`--measure: 70ch` in `tokens.css`), and lay out every page for a viewport 360 CSS pixels wide without horizontal page scrolling. Every Markdown table SHALL be rendered by `site/layouts/_markup/render-table.html` as follows:
- The `<table>` is the only child of a `div.table-scroll` with `tabindex="0"`, `role="region"` and a non-empty `aria-label`.
- Each header cell is a `th` with `scope="col"`.
- Every cell of a column whose header text is `CAS`, `MW (g/mol)`, `mmol` or `Equiv` carries `class="num"`.
- A newline separates adjacent cells in the output.

The screen stylesheet gives `.table-scroll` `overflow-x: auto`, so a wide table scrolls inside its own container. The base stylesheet gives `.num` cells `white-space: nowrap` and right alignment.

#### Scenario: Reagents tables are wrapped and marked
- **WHEN** a test scans every procedure page after a theme build
- **THEN** the table under the `Reagents` heading is the only child of a `div.table-scroll` with the three attributes, its header cells read `Reagent`, `CAS`, `MW (g/mol)`, `Amount`, `mmol` and `Equiv`, and exactly the cells of columns 2, 3, 5 and 6 carry `class="num"`

#### Scenario: Phone-width review
- **WHEN** the orchestrator views a procedure page, the all-procedures list and the search page at 390 CSS pixels wide (manual verification, tasks.md section 9)
- **THEN** no page scrolls sideways, and the long sample's Reagents table scrolls inside its container

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
The metadata panel SHALL be a `dl.metadata`, the first child of `article.procedure`. It holds one `dt`/`dd` pair per field, with these labels in this order, each pair present only when the field is set:
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
When a procedure sets `structure_image`, its page SHALL contain, after the metadata panel, a `figure.structure` holding an `img` whose `src` resolves to the published copy of `site/static/<structure_image>`, and whose `alt` is `Structure of <product name>`. Otherwise the page contains a `figure.structure.structure--placeholder` holding `div.structure__slot` with the text `No structure image`. The print stylesheet hides the placeholder.

#### Scenario: Image and placeholder
- **WHEN** a test scans `procedures/osdb-0003/index.html` and `procedures/osdb-0002/index.html` after a theme build
- **THEN** the first has an `img` whose resolved `src` is `public/structures/osdb-0003.svg`, which exists, with `alt` `Structure of Isopentyl acetate`
- **AND** the second has the placeholder figure and no `img`

### Requirement: Structure images are safe SVG
Every `.svg` file under `site/static/structures/` SHALL be a hand-written SVG that meets all of the following:
- It parses as XML with the root element `{http://www.w3.org/2000/svg}svg`.
- The root has a `viewBox`, `role="img"` and a child `title` with non-empty text.
- The first drawing element is a `rect` filling the view box with `fill="#fff"`.
- Every `stroke` and `fill` value other than that rectangle's is `#000` or `none`.
- No element is `script`, `foreignObject`, `image` or `use`.
- No attribute is `href` or `xlink:href`.
- No `style` attribute or element contains `url(`.
- No attribute value begins with `http:`, `https:` or `//`.

#### Scenario: Shipped structure images
- **WHEN** a test parses every `.svg` file under `site/static/structures/` with `xml.etree.ElementTree`
- **THEN** at least one file exists, `osdb-0003.svg` among them, and each meets every rule above

### Requirement: Procedure lists and their order
The site SHALL publish two lists of all procedures, each a table with the column headers `ID`, `Procedure`, `Reaction type`, `Status`, `Created` and `Modified`, and one row per procedure. The `ID` and `Procedure` cells link to the procedure page, and the `Reaction type` cell shows the vocabulary label.
- `/procedures/` lists the procedures by `id` ascending.
- `/procedures-by-date/` lists them by `date` descending, and procedures with equal `date` by `id` ascending.

Each list links to the other, and marks its own order's link with `aria-current="page"`. Neither needs JavaScript.

#### Scenario: Both orders
- **WHEN** a test scans `public/procedures/index.html` and `public/procedures-by-date/index.html` after a theme build, and computes both orders from the content files' front matter
- **THEN** the IDs in the rows of each table equal the computed order, and each page has a link to the other page's URL and an `aria-current="page"` link to its own

### Requirement: Home page
The home page SHALL contain:
- an introductory paragraph;
- a search form with `role="search"`, `method="get"` and an `action` resolving to `/search/`, holding a labelled input with `name="q"` and a submit button. The button is visible and works without JavaScript: it carries no `hidden` attribute, and submitting loads `/search/?q=<term>`;
- a `Recent procedures` heading followed by the procedure table of the first five procedures in the `/procedures-by-date/` order;
- a `Browse by reaction type` heading followed by a list linking each reaction-type term page, with the vocabulary label and the procedure count;
- a `Browse by tag` heading followed by a list linking each tag term page, with the tag and the count;
- a link to `/procedures/`.

#### Scenario: Home page content
- **WHEN** a test scans `public/index.html` after a theme build
- **THEN** the form, with a `button` or `input` of `type="submit"` that has no `hidden` attribute, the five recent rows in the computed order, one reaction-type link per reaction type in use, with its label and count, one tag link per tag in use, with its count, and the link to `/procedures/` are present

### Requirement: Taxonomy and term pages
For each taxonomy, `reaction_types`, `tags` and `authors`, the site SHALL publish:
- **A taxonomy page.** It lists every term in use, linking the term page with the procedure count. The link text is the vocabulary label for reaction types, the tag for tags, and the author's name as written for authors.
- **A term page per term.** Its `h1` is the same text, followed by the procedure table of exactly the procedures carrying that term, by `id` ascending.

The taxonomy pages' `h1` texts are `Reaction types`, `Tags` and `Authors`.

#### Scenario: Every term page lists the right procedures
- **WHEN** a test scans every term page under `public/reaction_types/`, `public/tags/` and `public/authors/` after a theme build, and computes each term's procedures from the content files' `reaction_types`, `tags` and `authors`
- **THEN** each term in the front matter has a term page, its table rows are exactly that term's IDs in ascending order, and the taxonomy page links it with the correct count and text

### Requirement: Content does not need JavaScript
Every procedure, list, taxonomy, term and home page SHALL show all of its content without running JavaScript. Scripts add only these:
- `site/assets/js/site.js` reveals and wires the print button (`window.print()`) and the SMILES copy button.
- `site.js` replaces the print-facts URL with `location.href` when the protocol is `http:` or `https:`.
- The copy button writes the SMILES string with the Clipboard API. When that fails or is unavailable, it selects the SMILES text instead.
- The search page's scripts run the search, as in the site-search spec.

The JavaScript-enhancement buttons, the print button (`data-print`) and the SMILES copy button (`data-copy-smiles`), carry `hidden` in the published HTML, and only the script reveals them. No other button is hidden: the home page's search submit button in particular stays visible and works without JavaScript.

#### Scenario: Static HTML holds the content
- **WHEN** a test scans every procedure page after a theme build, without running scripts
- **THEN** the metadata values, the rendered body sections and the links are present in the HTML, every `button` with `data-print` or `data-copy-smiles` has the `hidden` attribute, and no other `button` on any page under `public/` has it

#### Scenario: Buttons work in a browser
- **WHEN** the orchestrator opens a procedure page in a browser with JavaScript (manual verification, tasks.md section 9)
- **THEN** the print button is visible and opens the print dialog, the Copy button copies or selects the SMILES string, and with JavaScript disabled neither button is shown and the page is otherwise unchanged
- **AND** with JavaScript disabled, the home page's Search button is visible and submitting the form loads `/search/?q=<term>`, which shows the `noscript` text

### Requirement: Org and Markdown sources render alike
A procedure SHALL render to the same HTML whichever source format it was written in. Two procedures with the same content, one exported from Org and one written in Markdown, give pages that are byte-identical once their IDs and slugs are replaced by a common placeholder.

#### Scenario: Twin fixtures
- **WHEN** a theme build includes `tests/fixtures/theme/OSDB-0904-twin.org` in `org/procedures/` and `tests/fixtures/theme/OSDB-0905-twin.md` in `md/procedures/`, which hold the same title, dates, metadata, tags, precursor and body
- **THEN** after `OSDB-0904`, `osdb-0904`, `OSDB-0905` and `osdb-0905` are replaced by `OSDB-NNNN` and `osdb-nnnn`, `procedures/osdb-0904/index.html` and `procedures/osdb-0905/index.html` are byte-identical
