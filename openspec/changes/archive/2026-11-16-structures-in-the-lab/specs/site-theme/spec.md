## MODIFIED Requirements

### Requirement: Theme sources and constraints
The site SHALL be rendered by a theme written for this repository, made of these sources and no others:
- layouts in `site/layouts/`;
- stylesheets in `site/assets/css/`;
- scripts in `site/assets/js/`;
- structure images the build stages from the registry (compound-registry "Structure images"), and scheme images in the collection's `static/structures/`.

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

### Requirement: Structure image slot
A procedure that sets `scheme_image` (procedure-schema "Scheme image") SHALL end its header with one `figure.structure` holding an `img` whose `src` resolves to the published copy of the collection's `static/<scheme_image>` and whose `alt` is `Scheme of <title>`. Otherwise a specific procedure's header SHALL end with one `figure.structure` per product whose compound sets `structure_image`, in `products` order, each holding an `img` whose `src` resolves to the published copy of the image the build staged as `<structure_image>`, and whose `alt` is `Structure of <name>`, the compound's shown name. When no product's compound sets one, and always for a general procedure without `scheme_image`, the header ends with a `figure.structure.structure--placeholder` holding `div.structure__slot` with the text `No structure image`. The print stylesheet hides the placeholder.

#### Scenario: Image and placeholder
- **WHEN** a test scans `procedures/osdb-0003/index.html` and `procedures/osdb-0002/index.html` after a theme build
- **THEN** the first has an `img` whose resolved `src` is `public/substances/isopentyl-acetate/structure.svg`, which exists, with `alt` `Structure of Isopentyl acetate`
- **AND** the second has the placeholder figure and no `img`

#### Scenario: One figure per product with an image
- **WHEN** a test scans `procedures/osdb-0907/index.html` after the two-product build of the requirement "Procedure page structure", in which only `trans-stilbene` sets `structure_image`
- **THEN** its header ends with exactly one `figure.structure`, holding an `img` with `alt` `Structure of trans-Stilbene`, and has no placeholder

#### Scenario: Scheme image of a general procedure
- **WHEN** a test scans the page of the test collection's general procedure, which sets `scheme_image`, and the page of the fixture `tests/fixtures/general/OSDB-0140-general.md`, which does not, after a theme build that adds the latter
- **THEN** the first header ends with one figure whose `img` has the `alt` `Scheme of <title>` and the second with the placeholder, although its products' compounds set structure images

### Requirement: Structure images are safe SVG
Every `.svg` file under the demo collection's `static/structures/` and under `webapp/demo/substances/`, beside the demo registry, SHALL be a hand-written SVG that meets all of the following:
- It parses as XML with the root element `{http://www.w3.org/2000/svg}svg`.
- The root has a `viewBox`, `role="img"` and a child `title` with non-empty text.
- The first drawing element is a `rect` filling the view box with `fill="#fff"`.
- Every `stroke` and `fill` value other than that rectangle's is `#000` or `none`.
- No element is `script`, `foreignObject`, `image` or `use`.
- No attribute is `href` or `xlink:href`.
- No `style` attribute or element contains `url(`.
- No attribute value begins with `http:`, `https:` or `//`.

#### Scenario: Shipped structure images
- **WHEN** a test parses every `.svg` file under `examples/demo/static/structures/` and `webapp/demo/substances/` with `xml.etree.ElementTree`
- **THEN** each directory holds at least one, `aryl-ketone-reduction.svg` and `isopentyl-acetate/structure.svg` among them, and each meets every rule above

### Requirement: Compound pages
The site SHALL publish, for every compound of the registry, a page at `/compounds/<key>/`, made by a Hugo content adapter in `site/content/compounds/` from `site.Data.compounds` (site-build "Hugo configuration"). The page's display title is the compound's shown name (localization "German compound names"), and its `main` holds, in this order:
- the `h1` with that name;
- when the substance has a structure image (compound-registry "Structure images"), a `figure.structure` holding an `img` whose `src` resolves to the published image and whose `alt` is `Structure of <name>`; otherwise no figure and no placeholder;
- a `dl.compound-facts` with the pairs `Formula`, `MW`, `CAS` and `SMILES`, each only when the substance has it, written as the metadata panel writes them, the SMILES with its copy button, followed by one pair for each registry field the substance has, in the registry fields' order, its label and value written as compound-fields "Field display" states, with whitespace after each `</dt>`;
- `section.compound-made-by`, only when some published procedure has the compound among its products, with the `h2` `Made by` and a `ul` holding one `li` per such procedure, by ID, or, for a general procedure, one per entry that makes the compound, in entry order: an `a` linking the procedure page with the text `<ID> <title>`, then, for a general procedure, ` · entry <n>`, then ` · `, the yield of this compound in that procedure or entry as `<n> %`, then ` · ` and the procedure's status badge;
- `section.compound-used-in`, only when some published procedure has the compound among its `substrates`, with the `h2` `Used in` and a `ul` holding one `li` per such procedure, by ID: an `a` linking the procedure page with the text `<ID> <title>`, then ` · ` and its status badge;
- `section.compound-sequences`, as synthesis-sequences "Sequences beside procedures and compounds" states;
- `section.compound-routes`, as synthesis-routes "Routes on compound pages" states.

A compound page carries no `data-pagefind-body`, so the search index holds procedures only, and it loads no script but `site.js`.

#### Scenario: A page per compound
- **WHEN** a test scans `public/compounds/` after a theme build in locale `en`
- **THEN** every key of the test collection's registry has a page `compounds/<key>/index.html` whose `h1` is the compound's `name` and whose facts equal the registry's values, the registry fields the substance has following `SMILES` in their order, and no other compound page exists; the page of `new-compound-7` has no `Formula`, `MW` or `SMILES` pair

#### Scenario: Made by and used in
- **WHEN** a test reads the pages of `salicylic-acid` and `methyl-salicylate` after the same build
- **THEN** the first's `Made by` list holds OSDB-0001 with `80 %` and its `Used in` list holds OSDB-0002
- **AND** the second has no `section.compound-made-by`, and its `Used in` list holds OSDB-0001

#### Scenario: Made by an entry of a general procedure
- **WHEN** a test reads the page of `1-biphenyl-4-yl-ethanol` after the same build
- **THEN** its `Made by` list holds OSDB-0005 with `90 %`, and the demo's general procedure with ` · entry 1 · ` and that entry's yield

#### Scenario: Compound pages are not indexed
- **WHEN** a test scans every compound page after the same build
- **THEN** none has an element with `data-pagefind-body`, and the image of `isopentyl-acetate` resolves to `public/substances/isopentyl-acetate/structure.svg`
