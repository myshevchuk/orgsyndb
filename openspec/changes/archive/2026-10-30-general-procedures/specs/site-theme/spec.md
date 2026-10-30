## MODIFIED Requirements

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` holding, in this order:
  - `a.site-title`, linking `/` with the text `OrgSynDB`;
  - a `nav` element carrying `aria-label="Site"`, which links, in this order, to `/procedures/`, `/compounds/` and `/help/`, with the texts `Procedures`, `Compounds` and `Help`. The header holds no other `nav`;
  - `form.site-search` with `role="search"` and `method="get"`, holding one `input` with `type="search"` and `name="q"`, and a `button` with `type="submit"` and the text `Search`. On the catalogue, the term pages and `/general-procedures/` it is the catalogue's search form, with the `action`, attributes and texts that site-catalogue "Catalogue controls" gives. On every other page its `action` resolves to `/procedures/`, and its input carries `aria-label="Search procedures"` and the placeholder `Product, CAS, SMILES or keyword`;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures · built <time>`, where `<time>` is a `time` element whose `datetime` is the time the site was built, as an RFC 3339 date-time, and whose text is that time as `YYYY-MM-DD HH:MM`. Every page of one build shows the same time.

The navigation link whose URL is the page's own URL carries `aria-current="page"`. Otherwise the link of the section the page lies in carries `aria-current="true"`: every procedure page, `/general-procedures/`, `/reaction_types/`, `/tags/`, `/authors/` and their term pages lie in `/procedures/`; every compound page lies in `/compounds/`; every help page lies in `/help/`. No other navigation link carries `aria-current`. Every page has exactly one `input` with `name="q"`: the header's.

On screen, the site title and the navigation sit at the start of the header row and the search form at its end, so that the header has the same height, and its title, navigation and search form the same positions, on every page at a given window width. Every page's `h1` has the same font size.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, the interface string named by the page's `title_key` where it has one, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build in locale `en`
- **THEN** each has the skip link, the site title, the site header with the three navigation links in order and then `form.site-search`, one `main#main`, the footer text with its `time`, the same on every page, both `meta` elements, exactly one `h1`, no heading-level jump greater than one, and exactly one `input[name=q]`, the header's
- **AND** on every page except `/procedures/`, `/general-procedures/` and the term pages the form's `action` resolves to `/procedures/` and its input has the stated `aria-label` and placeholder

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build in locale `en`
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

#### Scenario: Current section in the navigation
- **WHEN** a test scans the home page, `/procedures/`, a procedure page, the three taxonomy pages, a term page of each taxonomy, `/compounds/`, a compound page, the help index and a help page after a theme build
- **THEN** the home page marks no navigation link; `/procedures/` marks its own link with `aria-current="page"`; the procedure page, the three taxonomy pages and the three term pages mark `/procedures/` with `aria-current="true"`; `/compounds/` marks its own link with `page` and the compound page marks it with `true`; `/help/` marks its own link with `page`; and the help page `/help/schema/` marks `/help/` with `true`

#### Scenario: The header does not move between pages
- **WHEN** the orchestrator measures the header and the `h1` of the home page, `/procedures/`, a term page, a procedure page and the help index in a browser at 1280 and at 500 CSS pixels (manual verification, tasks.md section 3)
- **THEN** at each width the header has the same height, the site title, the navigation and the search form the same positions and sizes, and the `h1` the same font size on every page

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

### Requirement: Compound pages
The site SHALL publish, for every compound of the registry, a page at `/compounds/<key>/`, made by a Hugo content adapter in `site/content/compounds/` from `site.Data.compounds` (site-build "Hugo configuration"). The page's display title is the compound's shown name (localization "German compound names"), and its `main` holds, in this order:
- the `h1` with that name;
- when the compound sets `structure_image`, a `figure.structure` holding an `img` whose `src` resolves to the published image and whose `alt` is `Structure of <name>`; otherwise no figure and no placeholder;
- a `dl.compound-facts` with the pairs `Formula`, `MW`, `CAS` (only when set) and `SMILES`, written as the metadata panel writes them, the SMILES with its copy button, and whitespace after each `</dt>`;
- `section.compound-made-by`, only when some published procedure has the compound among its products, with the `h2` `Made by` and a `ul` holding one `li` per such procedure, by ID, or, for a general procedure, one per entry that makes the compound, in entry order: an `a` linking the procedure page with the text `<ID> <title>`, then, for a general procedure, ` · entry <n>`, then ` · `, the yield of this compound in that procedure or entry as `<n> %`, then ` · ` and the procedure's status badge;
- `section.compound-used-in`, only when some published procedure has the compound among its `substrates`, with the `h2` `Used in` and a `ul` holding one `li` per such procedure, by ID: an `a` linking the procedure page with the text `<ID> <title>`, then ` · ` and its status badge.

A compound page carries no `data-pagefind-body`, so the search index holds procedures only, and it loads no script but `site.js`.

#### Scenario: A page per compound
- **WHEN** a test scans `public/compounds/` after a theme build in locale `en`
- **THEN** every key of the test collection's registry has a page `compounds/<key>/index.html` whose `h1` is the compound's `name` and whose facts equal the registry's values, and no other compound page exists

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
