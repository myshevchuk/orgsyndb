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

The screen stylesheet gives `.table-scroll` `overflow-x: auto`, so a wide table scrolls inside its own container. The base stylesheet gives `.num` cells `white-space: nowrap` and right alignment. From 55rem up, the screen stylesheet gives `.procedure-header` the two columns of `.procedure`, so that the structure figure in the header stands above the metadata margin. Below 55rem, it gives `.home-layout` and `.catalogue-layout` the single column `minmax(0, 1fr)`, and `.procedure` and `.procedure-header` `display: block`.

#### Scenario: Reagents tables are wrapped and marked
- **WHEN** a test scans every procedure page after a theme build
- **THEN** the table under the `Reagents` heading is the only child of a `div.table-scroll` with the three attributes, its header cells read `Reagent`, `CAS`, `MW (g/mol)`, `Amount`, `mmol` and `Equiv`, and exactly the cells of columns 2, 3, 5 and 6 carry `class="num"`

#### Scenario: Desktop workspace
- **WHEN** a browser displays the home page and `/procedures/` at 1280 CSS pixels or wider
- **THEN** the home page shows the recent list and the browse list in adjacent columns
- **AND** the catalogue shows the facets as a sidebar beside the results, and its table uses the remaining width

#### Scenario: Procedure reference and text
- **WHEN** a browser displays a procedure at 1280 CSS pixels or wider
- **THEN** the procedure header is a title block: the ID line, the title, the key facts and the actions on the left, the structure figure on the right at the width of the margin column, and a rule across both beneath them
- **AND** below it the body occupies a reading column on the left and the metadata a margin column on the right, without a panel border or background
- **AND** prose has a bounded reading measure and wide tables scroll locally
- **AND** the details stay first in the article's document order, so print and the search index show them before the body

#### Scenario: Print keeps document flow
- **WHEN** a procedure is printed or rendered to an A4 PDF
- **THEN** the header with its key facts and structure, the details and the body retain their single-column order

#### Scenario: Narrow windows stack the columns
- **WHEN** a test reads the declarations that `screen.css` applies to a window 500 CSS pixels wide
- **THEN** `.home-layout` and `.catalogue-layout` have `grid-template-columns: minmax(0, 1fr)`, and `.procedure` and `.procedure-header` have `display: block`
- **AND** a browser at that width shows the home page's recent list above its browse list, the catalogue's results with the facets behind the Filters toggle and the table scrolling in its own container, and a procedure's header with its structure, its details and its body in a single column, in that order

### Requirement: Procedure page structure
Each procedure page's `main` element SHALL contain, in document order:
1. the sample banner, when the requirement "Sample banner" applies;
2. `header.procedure-header`, holding:
   - `p.procedure-id`, containing the ID in an element with `data-pagefind-meta="id"`, then the status badge `span.badge.badge--<status>` whose text is the status, then, when the status is `checked` and the procedure sets `checked_by`, the sign-off `span.sign-off` with the text `by <names>`, the names joined by `, `, so that the line reads `OSDB-0921 checked by B. Example`;
   - the `h1` with the title;
   - `dl.key-facts`, holding a `dt`/`dd` pair `Scale` and a pair `Yield`, with whitespace after each `</dt>`. With one product the `Yield` value is `<n> %`; with several it lists every product as `<n> % <name>`, in `products` order, joined by `, `, where `<name>` is the compound's shown name (localization "German compound names"). For a general procedure the `Yield` value is the range of the yields of all its entries' products, `<min>–<max> %`, or `<n> %` when they are all equal;
   - the print facts of the print-layout spec;
   - `p.actions`, holding `button.print-button` with `type="button"`, the attribute `data-print`, the text `Print / Save as PDF` and the attribute `hidden`;
   - the structure figures of the requirement "Structure image slot";
3. `article.procedure`, the only element with `data-pagefind-body`, holding in order:
   - the details wrapper, holding the metadata panel;
   - the rendered body;
   - the index-terms element and then the SMILES index element of the site-search spec.

#### Scenario: Header and body in order
- **WHEN** a test scans `procedures/osdb-0002/index.html` and `procedures/osdb-0001/index.html` after a theme build
- **THEN** each has the elements in the stated order, the `h1`, the visible ID, the key facts and the structure figure lie outside the `article`, and the `article` contains the `Summary` heading after the metadata panel

#### Scenario: Key facts and sign-off
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build, and `procedures/osdb-0921/index.html` and `procedures/osdb-0923/index.html` after a build that adds the catalogue fixtures to the test collection
- **THEN** OSDB-0002's key facts are `Scale` `20 mmol` and `Yield` `75 %`, and it has no sign-off
- **AND** the ID line of OSDB-0921, which is checked by B. Example, reads `OSDB-0921 checked by B. Example`, and OSDB-0923, a draft, has no sign-off

#### Scenario: Yields of two products
- **WHEN** a test scans `procedures/osdb-0907/index.html` after a theme build that adds the two-product fixture `tests/fixtures/theme/OSDB-0907-two-products.md`, with `scale = "10 mmol"` and the products `trans-stilbene` at 45 % and `cis-stilbene` at 30 %, to the test collection, with the compound files it names copied from the fixture registry `tests/fixtures/compounds/`
- **THEN** its key facts are `Scale` `10 mmol` and `Yield` `45 % trans-Stilbene, 30 % cis-Stilbene`

#### Scenario: Yields of a general procedure
- **WHEN** a test scans the page of the test collection's general procedure after a theme build in locale `en`
- **THEN** its `Yield` key fact is the range from the lowest to the highest yield of its entries' products, written `<min>–<max> %`

### Requirement: Metadata panel
The metadata panel SHALL be a `dl.metadata`, the first element of the details wrapper at the start of `article.procedure`. It holds one `dt`/`dd` pair per field, with these labels in this order, each pair present only when the field is set. The panel repeats nothing the procedure header shows: the ID is in the header's ID line, the scale and yields are its key facts, and the checkers of a checked procedure are its sign-off. A compound's name is its shown name (localization "German compound names").
- `Product`, or `Products` when the procedure has several: one `a.compound` per product, in `products` order, linking `/compounds/<key>/` with the compound's name as text, joined by `, `;
- `Formula`, only when the procedure has one product: the compound's formula, where each digit run is wrapped in `<sub>`;
- `MW`, likewise, as `<mw> g/mol`;
- `CAS`, likewise, when the compound sets it;
- `SMILES`, likewise, as a `<code data-smiles>` with the string, followed by `button.copy-button` with `type="button"`, `data-copy-smiles`, the text `Copy` and `hidden`;
- `Starting materials`: one `a.compound` per entry of `substrates`, in its order, linking the compound's page with its name as text, joined by `, `;
- `Reaction type`, as a link to the term page whose text is the vocabulary label;
- `Tags`, as one link per tag to its term page, with the tag as text;
- `Authors`, as one link per author to the author's term page, with the name as text;
- `Checked by`, as the names joined by `, `, not linked, only when the status is not `checked`;
- `Created`, as `<time datetime="<RFC 3339 date>">YYYY-MM-DD HH:MM</time>`;
- `Modified`, the same for `lastmod`;
- `Precursors`, as in the requirement "Precursor and used-in links";
- `Used in`, as in the same requirement;
- `Sequences`, as synthesis-sequences "Sequences beside procedures and compounds" states.

Whitespace separates every `</dt>` from the following `<dd>` in the published HTML.

#### Scenario: Panel of the Markdown seed
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build
- **THEN** the `dt` texts are, in order, `Product`, `Formula`, `MW`, `CAS`, `SMILES`, `Starting materials`, `Reaction type`, `Tags`, `Authors`, `Created`, `Modified`, `Precursors` and `Sequences`
- **AND** the values include an `a.compound` to `/compounds/acetylsalicylic-acid/` with the text `Acetylsalicylic acid`, `C9H8O4` with three `<sub>` elements, `180.16 g/mol`, `50-78-2`, `CC(=O)Oc1ccccc1C(=O)O` in `code[data-smiles]`, `a.compound` links `Salicylic acid` and `Acetic anhydride` under `Starting materials`, a link with text `Acylation`, links `sample-data` and `acetylation`, links `A. Example` and `C. Example`, and `<time datetime="2026-10-19T23:46:11+02:00">`

#### Scenario: Panel labels follow the canonical order on every page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** each page's `dt` texts are a subsequence of the canonical label list in its order, they include every label whose field the content file sets, except `Checked by` where the status is `checked`, with `Product` for one product and `Products` for several, and `Formula`, `MW` and `SMILES` exactly when there is one product, no page has an `ID`, `Scale` or `Yield` label, and whitespace follows every `</dt>`

#### Scenario: A product named like its procedure is linked
- **WHEN** a test scans `procedures/osdb-0001/index.html`, whose title and product name are both `Salicylic acid`, after a theme build
- **THEN** its panel's `Product` pair holds one `a.compound` to `/compounds/salicylic-acid/` with the text `Salicylic acid`

#### Scenario: Panel of a procedure with two products
- **WHEN** a test scans `procedures/osdb-0907/index.html` after the two-product build of the requirement "Procedure page structure"
- **THEN** its panel has a `Products` pair with the `a.compound` links `trans-Stilbene` and `cis-Stilbene`, in that order, and no `Product`, `Formula`, `MW`, `CAS` or `SMILES` pair

### Requirement: Precursor and used-in links
A procedure's precursors SHALL be the other published procedures that have among their products a compound of its `substrates`, and the procedures it is used in SHALL be the other published procedures that have among their `substrates` a compound of its products. The `Precursors` value holds one `a.precursor` per precursor and the `Used in` value one `a.used-in` per procedure it is used in, each linking that procedure's page with the text `<ID> <title>`, ordered by ID. A procedure with no precursor has no `Precursors` pair, and one used in no other procedure has no `Used in` pair.

#### Scenario: Links resolve in both directions
- **WHEN** a test scans every procedure page after a theme build, resolves each `a.precursor` and `a.used-in` `href` against the page's URL, and derives the precursor relation from the content files' `products` and `substrates`
- **THEN** every link resolves to an existing procedure page
- **AND** for every pair where A is a precursor of B, B's page has an `a.precursor` to A and A's page has an `a.used-in` to B
- **AND** no other `a.precursor` or `a.used-in` exists

#### Scenario: The shipped chains
- **WHEN** the same test reads the pages of OSDB-0001, 0002, 0004, 0005, 0007, 0008 and 0009
- **THEN** OSDB-0002, 0005, 0008 and 0009 each have one `a.precursor`, to OSDB-0001, 0004, 0007 and 0004 respectively
- **AND** OSDB-0001 and 0007 each have one `a.used-in`, back to OSDB-0002 and 0008, and OSDB-0004 has two, to OSDB-0005 and OSDB-0009

#### Scenario: A second route
- **WHEN** a test scans the pages of OSDB-0001, OSDB-0002 and OSDB-0908 after a theme build that adds `tests/fixtures/theme/OSDB-0908-second-route.md`, which makes `salicylic-acid` and names no substrate the demo procedures make, with the compound files it names copied from the fixture registry
- **THEN** OSDB-0002 has two `a.precursor`, to OSDB-0001 and OSDB-0908, in that order, and OSDB-0908 has one `a.used-in`, to OSDB-0002

### Requirement: Sample banner
A procedure page SHALL carry exactly one `p.sample-banner` with `role="note"` and the text `Sample data — quantities not experimentally verified.` when `sample-data` is among the procedure's tags, and none otherwise. The banner is the first child of `main`, lies outside `article.procedure`, and is not hidden by the print stylesheet.

#### Scenario: Every sample shows the banner
- **WHEN** a test scans every procedure page whose content file's tags include `sample-data`, after a theme build
- **THEN** each has exactly one banner with that text, outside the indexed body

#### Scenario: A procedure without the tag has none
- **WHEN** a theme build includes `tests/fixtures/theme/OSDB-0906-quoted-title.md`, whose tags do not include `sample-data`
- **THEN** `procedures/osdb-0906/index.html` has no `p.sample-banner`

### Requirement: Structure image slot
A procedure that sets `scheme_image` (procedure-schema "Scheme image") SHALL end its header with one `figure.structure` holding an `img` whose `src` resolves to the published copy of the collection's `static/<scheme_image>` and whose `alt` is `Scheme of <title>`. Otherwise a specific procedure's header SHALL end with one `figure.structure` per product whose compound sets `structure_image`, in `products` order, each holding an `img` whose `src` resolves to the published copy of the collection's `static/<structure_image>`, and whose `alt` is `Structure of <name>`, the compound's shown name. When no product's compound sets one, and always for a general procedure without `scheme_image`, the header ends with a `figure.structure.structure--placeholder` holding `div.structure__slot` with the text `No structure image`. The print stylesheet hides the placeholder.

#### Scenario: Image and placeholder
- **WHEN** a test scans `procedures/osdb-0003/index.html` and `procedures/osdb-0002/index.html` after a theme build
- **THEN** the first has an `img` whose resolved `src` is `public/structures/isopentyl-acetate.svg`, which exists, with `alt` `Structure of Isopentyl acetate`
- **AND** the second has the placeholder figure and no `img`

#### Scenario: One figure per product with an image
- **WHEN** a test scans `procedures/osdb-0907/index.html` after the two-product build of the requirement "Procedure page structure", in which only `trans-stilbene` sets `structure_image`
- **THEN** its header ends with exactly one `figure.structure`, holding an `img` with `alt` `Structure of trans-Stilbene`, and has no placeholder

#### Scenario: Scheme image of a general procedure
- **WHEN** a test scans the page of the test collection's general procedure, which sets `scheme_image`, and the page of the fixture `tests/fixtures/general/OSDB-0140-general.md`, which does not, after a theme build that adds the latter
- **THEN** the first header ends with one figure whose `img` has the `alt` `Scheme of <title>` and the second with the placeholder, although its products' compounds set structure images

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
- **THEN** at least one file exists, `isopentyl-acetate.svg` among them, and each meets every rule above

### Requirement: Home page
The home page's `main` SHALL contain, in this order:
- `div.home-intro`, holding the `h1` `Synthetic procedures` and a `p.lede` with the text `The group's procedures, written in Org or Markdown to one schema.`;
- `div.home-layout`, holding, in this order:
  - `section.home-recent`, with the `h2` `Recently updated`, then an `ol.recent-list` with one `li` per procedure for the first five published procedures, or all when there are fewer, ordered by `lastmod` as an instant, newest first, and by `id` ascending for equal instants. Each `li` holds an `a` linking the procedure page whose text is `<id> <title>`, then `<time datetime="<RFC 3339 lastmod>">YYYY-MM-DD</time>`. After the list, a `p` links `/procedures/?sort=modified` with the text `All procedures, recently updated first`;
  - `section.home-unchecked`, only when some published procedure has the status `draft`, with the `h2` `Not yet checked`, then an `ol.unchecked-list` with one `li` per draft for the first five drafts by `id` ascending, or all when there are fewer: the drafts the catalogue lists first under `/procedures/?status=draft`. Each `li` holds an `a` linking the procedure page whose text is `<id> <title>`, then `<time datetime="<RFC 3339 date>">YYYY-MM-DD</time>` of its creation. After the list, a `p` holds a link to `/procedures/?status=draft` with the text `All draft procedures`, then ` ` and a `span.count` reading `(<n>)`, `n` the number of drafts;
  - `section.home-browse`, with the `h2` `Browse`, then a `ul.browse-list` whose `li` entries hold, in this order, a link and then ` ` and a `span.count` reading `(<n>)`: `All procedures` to `/procedures/`, `n` the number of published procedures; `Reaction types` to `/reaction_types/`, `Tags` to `/tags/` and `Authors` to `/authors/`, each `n` the number of terms of that taxonomy in use; `Compounds` to `/compounds/`, `n` the number of compounds in the registry; `Sequences` to `/sequences/`, `n` the number of published sequences.

The counts are computed from the published procedures and the registry, and written with the site language's digit grouping. The home page's `main` holds no form, no `input` and no procedure table. On screen, from 70rem up, the recent and unchecked lists form the first column and the browse list the second.

#### Scenario: Home page content
- **WHEN** a test scans `public/index.html` of a theme build that adds the catalogue fixtures to the test collection, in locale `en`
- **THEN** the `h1` is `Synthetic procedures`, and the recent list holds the first five procedures in the computed order, each ID once, with the stated link texts and dates, and two fixtures whose `lastmod` is the same instant are ordered by ID
- **AND** the unchecked list holds the first five drafts by ID with their creation dates, and its link reads the number of drafts computed from the published content files
- **AND** the browse list has the six entries in order, with the stated targets, and counts equal to those computed from the published content files and the registry
- **AND** `main` has the links to `/procedures/?sort=modified` and `/procedures/?status=draft`, and no `form`, `input` or `table`

#### Scenario: Nothing waits for a check
- **WHEN** a test scans `public/index.html` of a theme build of a collection whose procedures are all `checked`
- **THEN** it has no `section.home-unchecked` and no link to `/procedures/?status=draft`

### Requirement: Taxonomy and term pages
For each taxonomy, `reaction_types`, `tags` and `authors`, the site SHALL publish:
- **A taxonomy page.** It is a compact directory: its `h1` is `Reaction types`, `Tags` or `Authors`, followed by a `ul.term-list` with one `li` per term in use, ordered by the link text, holding a link to the term page and then ` ` and `span.count` reading `(<n>)`, `n` the term's procedure count. The link text is the vocabulary label for reaction types, the tag for tags, and the author's name as written for authors.
- **A term page per term.** It is a catalogue page with the term as its fixed scope (site-catalogue "Catalogue pages" and "Fixed scope on term pages"). Its `h1` is the same text as the term's link.

Each directory is linked from the section tabs, from the home page's browse list and from its catalogue facet; the metadata panel's reaction-type, tag and author links lead to the term pages.

#### Scenario: Every term page lists the right procedures
- **WHEN** a test scans every term page under `public/reaction_types/`, `public/tags/` and `public/authors/` after a theme build, and computes each term's procedures from the content files' `reaction_types`, `tags` and `authors`
- **THEN** each term in the front matter has a term page, its catalogue table's rows are exactly that term's IDs in ascending order, and the taxonomy page links it with the correct count and text, in order

### Requirement: Content does not need JavaScript
Every procedure, catalogue, taxonomy, term, compound, sequence, help and home page SHALL show all of its content without running JavaScript. Scripts add only these:
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
- **WHEN** a theme build includes `tests/fixtures/theme/OSDB-0904-twin.org` in `org/procedures/` and `tests/fixtures/theme/OSDB-0905-twin.md` in `md/procedures/`, which hold the same title, dates, metadata, tags, products, substrates and body
- **THEN** after `OSDB-0904`, `osdb-0904`, `OSDB-0905` and `osdb-0905` are replaced by `OSDB-NNNN` and `osdb-nnnn`, `procedures/osdb-0904/index.html` and `procedures/osdb-0905/index.html` are byte-identical

### Requirement: Note references
A reference to a note in a procedure's body SHALL link to that note. `pipeline.link_notes(text)` returns the text of a Markdown procedure file with the changes below, and `pipeline.stage_content` applies it to every file it stages, so that Org and Markdown sources get the same links:
- **The notes list** is the first ordered list after the level-2 heading of the notes section, `Notes` or `Anmerkungen`, compared as validation compares section headings (attribute block and closing `#` removed, case ignored), and before the next level-2 heading. The list ends at its first line that follows a blank line and is neither indented nor an item of the list.
- **Anchors.** The text of each top-level item of the notes list starts with `<span id="note-<n>"></span>`, where `n` is the number the item is rendered with: the list's first number, then one more for each further item.
- **References.** Outside fenced code blocks and code spans, each `(Note <n>)` or `(Anmerkung <n>)`, with any run of whitespace between the word and the number, becomes `([<word><whitespace><n>](#note-<n>))` when the notes list has an item `n`. Any other reference is left as it is.

A text without a notes list is returned unchanged. On screen, the note an address targets is highlighted.

#### Scenario: Notes and references are linked
- **WHEN** a test calls `link_notes` on a text whose `## Notes {#notes}` section holds an ordered list of two items, the first continued on an indented line, followed by a paragraph, and whose body refers to `(Note 1)`, to `(Note` and `2)` across a line break, to `(Note 3)`, and to `(Note 1)` in a fenced code block and in a code span
- **THEN** the two items start with the anchors `note-1` and `note-2`, the first two references link to them, keeping the line break, and `(Note 3)`, the code block, the code span and the paragraph after the list are unchanged

#### Scenario: German notes, other numbering
- **WHEN** a test calls `link_notes` on a text with `## Anmerkungen` and a list whose items are all numbered `1.`, on a text whose notes list starts at `3.`, and on a text without a notes section
- **THEN** the first gets `note-1` and `note-2` and links `(Anmerkung 2)`, the second numbers its anchors from `note-3`, and the third is returned unchanged

#### Scenario: Linked notes on a procedure page
- **WHEN** a test scans `procedures/osdb-0003/index.html` after a theme build in locale `en`
- **THEN** its body has links `Note 1` and `Note 2` to `#note-1` and `#note-2`, and the first two items of the list after the `Notes` heading hold the elements with those IDs

### Requirement: Procedure section tabs
The catalogue at `/procedures/`, the general-procedures view `/general-procedures/`, the taxonomy pages `/reaction_types/`, `/tags/` and `/authors/`, and every term page SHALL have, as the first element of `main`, a `nav.section-tabs` carrying `aria-label="Procedures"`. It holds a `ul` whose `li` entries each hold one link, in this order: `/procedures/` with the text `All procedures`, `/general-procedures/` with `General procedures`, `/reaction_types/` with `Reaction types`, `/tags/` with `Tags` and `/authors/` with `Authors`. The link whose URL is the page's own URL carries `aria-current="page"`; on a term page the link of its taxonomy carries `aria-current="true"`. No other tab carries `aria-current`, and no other page has a `nav.section-tabs`.

On screen the tabs form one row above the page's `h1`, wrapping on narrow windows, and the current tab is marked by more than colour alone.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

#### Scenario: Tabs on the listing pages
- **WHEN** a test scans `/procedures/`, `/general-procedures/`, the three taxonomy pages and every term page after a theme build in locale `en`
- **THEN** each page's `main` begins with `nav.section-tabs` carrying `aria-label="Procedures"`, whose links are the five stated targets and texts in order
- **AND** `/procedures/`, `/general-procedures/` and each taxonomy page mark their own tab with `aria-current="page"`, each term page marks its taxonomy's tab with `aria-current="true"`, and no other tab carries `aria-current`

#### Scenario: No tabs elsewhere
- **WHEN** a test scans every other HTML file under `public/` except files under `public/pagefind/`, after the same build
- **THEN** none has a `nav.section-tabs`

#### Scenario: Tabs in a browser
- **WHEN** the orchestrator opens `/procedures/`, `/tags/` and a reaction-type term page in a browser at 1280 and at 500 CSS pixels, light and dark (manual verification, tasks.md section 3)
- **THEN** the tabs sit in one row above the `h1`, wrap at 500 pixels without horizontal scrolling, and the current tab is underlined as well as coloured

### Requirement: Compound pages
The site SHALL publish, for every compound of the registry, a page at `/compounds/<key>/`, made by a Hugo content adapter in `site/content/compounds/` from `site.Data.compounds` (site-build "Hugo configuration"). The page's display title is the compound's shown name (localization "German compound names"), and its `main` holds, in this order:
- the `h1` with that name;
- when the compound sets `structure_image`, a `figure.structure` holding an `img` whose `src` resolves to the published image and whose `alt` is `Structure of <name>`; otherwise no figure and no placeholder;
- a `dl.compound-facts` with the pairs `Formula`, `MW`, `CAS` (only when set) and `SMILES`, written as the metadata panel writes them, the SMILES with its copy button, followed by one pair for each field the collection declares and the compound sets, in declared order, its label and value written as compound-fields "Field display" states, with whitespace after each `</dt>`;
- `section.compound-made-by`, only when some published procedure has the compound among its products, with the `h2` `Made by` and a `ul` holding one `li` per such procedure, by ID, or, for a general procedure, one per entry that makes the compound, in entry order: an `a` linking the procedure page with the text `<ID> <title>`, then, for a general procedure, ` · entry <n>`, then ` · `, the yield of this compound in that procedure or entry as `<n> %`, then ` · ` and the procedure's status badge;
- `section.compound-used-in`, only when some published procedure has the compound among its `substrates`, with the `h2` `Used in` and a `ul` holding one `li` per such procedure, by ID: an `a` linking the procedure page with the text `<ID> <title>`, then ` · ` and its status badge.

- `section.compound-sequences`, as synthesis-sequences "Sequences beside procedures and compounds" states.

A compound page carries no `data-pagefind-body`, so the search index holds procedures only, and it loads no script but `site.js`.

#### Scenario: A page per compound
- **WHEN** a test scans `public/compounds/` after a theme build in locale `en`
- **THEN** every key of the test collection's registry has a page `compounds/<key>/index.html` whose `h1` is the compound's `name` and whose facts equal the registry's values, the declared fields the compound sets following `SMILES` in declared order, and no other compound page exists

#### Scenario: Made by and used in
- **WHEN** a test reads the pages of `salicylic-acid` and `methyl-salicylate` after the same build
- **THEN** the first's `Made by` list holds OSDB-0001 with `80 %` and its `Used in` list holds OSDB-0002
- **AND** the second has no `section.compound-made-by`, and its `Used in` list holds OSDB-0001

#### Scenario: Made by an entry of a general procedure
- **WHEN** a test reads the page of `1-biphenyl-4-yl-ethanol` after the same build
- **THEN** its `Made by` list holds OSDB-0005 with `90 %`, and the demo's general procedure with ` · entry 1 · ` and that entry's yield

#### Scenario: Compound pages are not indexed
- **WHEN** a test scans every compound page after the same build
- **THEN** none has an element with `data-pagefind-body`, and the image of `isopentyl-acetate` resolves to `public/structures/isopentyl-acetate.svg`

### Requirement: Compound directory
The page `/compounds/` SHALL be the compound catalogue (site-catalogue "Compound catalogue"), whose results end with a `table.compound-table` with the header cells `Compound`, `Formula`, `MW` and `CAS`, then one header cell for each field the collection declares with `column = true`, in declared order, holding the field's shown label, then `Made by` and `Used in`, and one body row per compound of the registry, ordered by shown name. A row holds a link to the compound's page with its shown name, the formula with each digit run in `<sub>`, `<mw> g/mol`, the CAS number or an empty cell, for each column field the compound's value written as compound-fields "Field display" states or an empty cell when the compound does not set it, and the numbers of published procedures that make it and that use it. The header and body cells of a `number` field carry the class `num`. Without JavaScript the page shows the complete table and no control.

#### Scenario: Every compound is listed
- **WHEN** a test scans `public/compounds/index.html` after a theme build in locale `en`
- **THEN** its rows are the registry's compounds, each once, ordered by name, with the stated cells, and their counts equal those computed from the published content files
- **AND** its header cells are `Compound`, `Formula`, `MW`, `CAS`, the labels of the column fields that the test collection's `orgsyndb.toml` declares, in declared order, `Made by` and `Used in`

#### Scenario: Number and boolean columns
- **WHEN** a test builds a copy of the test collection in locale `en` after adding `column = true` to the declarations of `stock` and `in_house` in its `orgsyndb.toml`, and scans `public/compounds/index.html`
- **THEN** the header cells `Stock` and `Made in house` follow `Chemical class`, the header and body cells of `Stock` carry the class `num` and those of `Made in house` do not, a compound that sets neither field has an empty cell in both columns, `ethyl-triphenylphosphoranylidene-acetate` reads `12.5 g`, and a compound with `in_house = false` reads `No`

