## MODIFIED Requirements

### Requirement: Measure and tables
The screen layout SHALL prioritize desktop browsers with a shell up to 96rem wide, set in the system sans-serif stack; printed pages keep the text face of `tokens.css`. Running procedure paragraphs and lists SHALL keep a reading measure up to 78ch, while procedure tables SHALL use their available column width. Narrower windows SHALL stack the columns in document order, and wide tables SHALL scroll within their own containers. Every Markdown table SHALL be rendered by `site/layouts/_markup/render-table.html` as follows:
- The `<table>` is the only child of a `div.table-scroll` with `tabindex="0"`, `role="region"` and a non-empty `aria-label`.
- Each header cell is a `th` with `scope="col"`.
- Every cell of a column whose header text is `CAS`, `MW (g/mol)`, `mmol` or `Equiv` carries `class="num"`.
- A newline separates adjacent cells in the output.

The screen stylesheet gives `.table-scroll` `overflow-x: auto`, so a wide table scrolls inside its own container. The base stylesheet gives `.num` cells `white-space: nowrap` and right alignment. Below 55rem, the screen stylesheet gives `.home-layout` and `.catalogue-layout` the single column `minmax(0, 1fr)`. Where a procedure page's widgets stand is the stylesheet's to decide; it is not fixed here.

#### Scenario: Reagents tables are wrapped and marked
- **WHEN** a test scans every procedure page after a theme build
- **THEN** the table under the `Reagents` heading is the only child of a `div.table-scroll` with the three attributes, its header cells read `Reagent`, `CAS`, `MW (g/mol)`, `Amount`, `mmol` and `Equiv`, and exactly the cells of columns 2, 3, 5 and 6 carry `class="num"`

#### Scenario: Desktop workspace
- **WHEN** a browser displays the home page and `/procedures/` at 1280 CSS pixels or wider
- **THEN** the home page shows the recent list and the browse list in adjacent columns
- **AND** the catalogue shows the facets as a sidebar beside the results, and its table uses the remaining width

#### Scenario: Procedure widgets on a wide screen
- **WHEN** the orchestrator opens a procedure and a general procedure in a browser at 1440 CSS pixels (manual verification, tasks.md section 4)
- **THEN** the page has no horizontal scroll, prose keeps a bounded measure, and wide tables, the scope table among them, scroll inside their own containers instead of being clipped
- **AND** the details wrapper stays first in the article's document order, so print and the search index show it before the body

#### Scenario: Print keeps document flow
- **WHEN** a procedure is printed or rendered to an A4 PDF
- **THEN** the header with its key facts, the details widgets with the structure, the scope of a general procedure and the body sections keep their single-column document order

#### Scenario: Narrow windows stack the columns
- **WHEN** a test reads the declarations that `screen.css` applies to a window 500 CSS pixels wide
- **THEN** `.home-layout` and `.catalogue-layout` have `grid-template-columns: minmax(0, 1fr)`
- **AND** a browser at that width shows the home page's recent list above its browse list, the catalogue's results with the facets behind the Filters toggle and the table scrolling in its own container, and a procedure's header, its details widgets and its body widgets in a single column, in that order, without horizontal scrolling

### Requirement: Procedure page structure
Each procedure page's `main` element SHALL contain, in document order:
1. the sample banner, when the requirement "Sample banner" applies;
2. `header.procedure-header`, holding:
   - `p.procedure-id`, containing the ID in an element with `data-pagefind-meta="id"`, then the status badge `span.badge.badge--<status>` whose text is the status, then, when the status is `checked` and the procedure sets `checked_by`, the sign-off `span.sign-off` with the text `by <names>`, the names joined by `, `, so that the line reads `OSDB-0921 checked by B. Example`;
   - the `h1` with the title;
   - `dl.key-facts`, holding a `dt`/`dd` pair `Scale` and a pair `Yield`, with whitespace after each `</dt>`. With one product the `Yield` value is `<n> %`; with several it lists every product as `<n> % <name>`, in `products` order, joined by `, `, where `<name>` is the compound's shown name (localization "German compound names"). For a general procedure the `Yield` value is the range of the yields of all its entries' products, `<min>–<max> %`, or `<n> %` when they are all equal;
   - the print facts of the print-layout spec;
   - `p.actions`, holding `button.print-button` with `type="button"`, the attribute `data-print`, the text `Print / Save as PDF` and the attribute `hidden`;
3. `article.procedure`, the only element with `data-pagefind-body`, holding in order:
   - the details wrapper `div.procedure-details`, holding the widgets of the requirement "Metadata panel";
   - for a general procedure, its scope (general-procedures "Scope table on the page");
   - the rendered body, its sections wrapped as the requirement "Procedure body sections" states;
   - the index-terms element and then the SMILES index element of the site-search spec.

#### Scenario: Header and body in order
- **WHEN** a test scans `procedures/osdb-0002/index.html` and `procedures/osdb-0001/index.html` after a theme build
- **THEN** each has the elements in the stated order, the `h1`, the visible ID and the key facts lie outside the `article`, the header holds no `figure`, and the `article` contains the `Summary` heading after the metadata panel

#### Scenario: Key facts and sign-off
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build, and `procedures/osdb-0921/index.html` and `procedures/osdb-0923/index.html` after a build that adds the catalogue fixtures to the test collection
- **THEN** OSDB-0002's key facts are `Scale` `20 mmol` and `Yield` `75 %`, and it has no sign-off
- **AND** the ID line of OSDB-0921, which is checked by B. Example, reads `OSDB-0921 checked by B. Example`, and OSDB-0923, a draft, has no sign-off

#### Scenario: Yields of two products
- **WHEN** a test scans `procedures/osdb-0907/index.html` after a theme build that adds the two-product fixture `tests/fixtures/theme/OSDB-0907-two-products.md`, with `scale = "10 mmol"` and the products `trans-stilbene` at 45 % and `cis-stilbene` at 30 %, to a copy of the test collection whose registry gains the substances it names from the fixture registry `tests/fixtures/registry.json`
- **THEN** its key facts are `Scale` `10 mmol` and `Yield` `45 % trans-Stilbene, 30 % cis-Stilbene`

#### Scenario: Yields of a general procedure
- **WHEN** a test scans the page of the test collection's general procedure after a theme build in locale `en`
- **THEN** its `Yield` key fact is the range from the lowest to the highest yield of its entries' products, written `<min>–<max> %`

### Requirement: Metadata panel
The details wrapper at the start of `article.procedure` SHALL hold up to three widgets, in this order, each a `section.widget` whose `div.widget__head` holds its `h2` and whose `div.widget__body` holds one `dl.metadata`:
1. the compound widget, headed `Compound` when the procedure has one product and `Products` when it has several, holding the structure figures (requirement "Structure image slot") and the pairs `Product` or `Products`, `Formula`, `MW`, `CAS` and `SMILES`; it is always present;
2. the details widget, headed `Details`, holding the pairs `Reaction type`, `Tags`, `Authors`, `Checked by`, the declared procedure fields, `Created` and `Modified`, present when it has a pair;
3. the context widget, headed `Synthesis context`, holding the pairs `Starting materials`, `Precursors`, `Used in` and `Sequences`, present when it has a pair.

Each of the three `div.widget__head` carries `data-pagefind-ignore`, so that the widget titles are not indexed.

The metadata panel is the `dt`/`dd` pairs of these lists, read in document order. It holds one pair per field, with these labels in this order, each pair present only when the field is set. The panel repeats nothing the procedure header shows: the ID is in the header's ID line, the scale and yields are its key facts, and the checkers of a checked procedure are its sign-off. A compound's name is its shown name (localization "German compound names"). The compound widget's facts follow the order of the same facts in the lab's compound widget (lab-registry "Registry pages"): formula, molar mass, CAS number, SMILES.
- `Product`, or `Products` when the procedure has several: one `a.compound` per product, in `products` order, linking the substance's lab page `/lab/registry/substances/<key>/` (lab-registry "Registry pages") with the compound's name as text, each followed by its note of compound-fields "Values beside compound links" when it has one, joined by `, `;
- `Formula`, only when the procedure has one product: the compound's formula, where each digit run is wrapped in `<sub>`;
- `MW`, likewise, as `<mw> g/mol`;
- `CAS`, likewise, when the compound sets it;
- `SMILES`, likewise, as a `<code data-smiles>` with the string, followed by `button.copy-button` with `type="button"`, `data-copy-smiles`, the text `Copy` and `hidden`;
- `Reaction type`, as a link to the term page whose text is the vocabulary label;
- `Tags`, as one link per tag to its term page, with the tag as text;
- `Authors`, as one link per author to the author's term page, with the account's name as text (procedure-authors "Author data for the site");
- `Checked by`, as the names joined by `, `, not linked, only when the status is not `checked`;
- each procedure field the collection declares (procedure-fields "Procedure field declarations") that the procedure sets, in declared order, labelled with the field's shown label (procedure-fields "Procedure field data"), its value written as compound-fields "Field display" writes a value;
- `Created`, as `<time datetime="<RFC 3339 date>">YYYY-MM-DD HH:MM</time>`;
- `Modified`, the same for `lastmod`;
- `Starting materials`: one `a.compound` per entry of `substrates`, in its order, linking the compound's page with its name as text, each followed by its note as for `Product`, joined by `, `;
- `Precursors`, as in the requirement "Precursor and used-in links";
- `Used in`, as in the same requirement;
- `Sequences`, as synthesis-sequences "Sequences beside procedures and compounds" states.

Whitespace separates every `</dt>` from the following `<dd>` in the published HTML.

#### Scenario: Panel of the Markdown seed
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build
- **THEN** the widgets are headed `Compound`, `Details` and `Synthesis context`, and the `dt` texts are, in order, `Product`, `Formula`, `MW`, `CAS`, `SMILES`, then `Reaction type`, `Tags`, `Authors`, `Lab notebook`, `Project`, `Working time`, `Inert atmosphere`, `Created`, `Modified`, then `Starting materials`, `Precursors` and `Sequences`
- **AND** the values include an `a.compound` to `/lab/registry/substances/acetylsalicylic-acid/` with the text `Acetylsalicylic acid`, `C9H8O4` with three `<sub>` elements, `180.16 g/mol`, `50-78-2`, `CC(=O)Oc1ccccc1C(=O)O` in `code[data-smiles]`, `a.compound` links `Salicylic acid` and `Acetic anhydride` under `Starting materials`, a link with text `Acylation`, links `sample-data` and `acetylation`, links `Katrin Lehmann` and `Anna Schmidt` to `/authors/klehmann/` and `/authors/aschmidt/`, the texts `AE-1/2`, `Teaching › First-year practical`, `2.5 h` and `No`, and `<time datetime="2026-10-19T23:46:11+02:00">`

#### Scenario: Panel labels follow the canonical order on every page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** each page's `dt` texts are a subsequence of the canonical label list in its order, the declared procedure fields' shown labels standing in it, in declared order, between `Checked by` and `Created`; each label stands in the widget the requirement assigns it to; they include every label whose field the content file sets, except `Checked by` where the status is `checked`, with `Product` for one product and `Products` for several, and `Formula`, `MW` and `SMILES` exactly when there is one product, no page has an `ID`, `Scale` or `Yield` label, and whitespace follows every `</dt>`

#### Scenario: A product named like its procedure is linked
- **WHEN** a test scans `procedures/osdb-0001/index.html`, whose title and product name are both `Salicylic acid`, after a theme build
- **THEN** its panel's `Product` pair holds one `a.compound` to `/lab/registry/substances/salicylic-acid/` with the text `Salicylic acid`

#### Scenario: Panel of a procedure with two products
- **WHEN** a test scans `procedures/osdb-0907/index.html` after the two-product build of the requirement "Procedure page structure"
- **THEN** its compound widget is headed `Products` and its panel has a `Products` pair with the `a.compound` links `trans-Stilbene` and `cis-Stilbene`, in that order, and no `Product`, `Formula`, `MW`, `CAS` or `SMILES` pair

#### Scenario: Declared fields in the German panel
- **WHEN** a test reads `procedures/osdb-0002/index.html` of a build of the test collection in locale `de`
- **THEN** its panel holds the pairs `Laborjournal` `AE-1/2`, `Projekt` `Lehre › Grundpraktikum`, `Arbeitszeit` `2,5 h` and `Schutzgas` `Nein`, in this order, between the `Autoren` pair and the `Erstellt` pair

#### Scenario: Compound rows in the lab's order
- **WHEN** a test reads the compound widget of `procedures/osdb-0002/index.html` after a theme build in locale `en`, and the row labels of the template `webapp/registry/templates/registry/substance.html`
- **THEN** the procedure's labels `Formula`, `MW`, `CAS` and `SMILES` stand in the order of the substance page's rows `Formula`, `Molar mass`, `CAS number` and `SMILES`

#### Scenario: No context widget without links
- **WHEN** a test scans every procedure page after a theme build
- **THEN** a page has a context widget exactly when it has one of the pairs `Starting materials`, `Precursors`, `Used in` and `Sequences`, and every page has exactly one compound widget, first in the details wrapper

### Requirement: Structure image slot
The structure figures SHALL stand in the compound widget (requirement "Metadata panel"), between its title bar and its body. A procedure that sets `scheme_image` (procedure-schema "Scheme image") has there one `figure.structure` holding an `img` whose `src` resolves to the published copy of the collection's `static/<scheme_image>` and whose `alt` is `Scheme of <title>`. Otherwise a specific procedure has there one `figure.structure` per product whose compound sets `structure_image`, in `products` order, each holding an `img` whose `src` resolves to the published copy of the image the build staged as `<structure_image>`, and whose `alt` is `Structure of <name>`, the compound's shown name. When no product's compound sets one, and always for a general procedure without `scheme_image`, it has a `figure.structure.structure--placeholder` holding `div.structure__slot` with the text `No structure image`. Every figure carries `data-pagefind-ignore`, so that the search index gains no `alt` text. The print stylesheet hides the placeholder.

#### Scenario: Image and placeholder
- **WHEN** a test scans `procedures/osdb-0003/index.html` and `procedures/osdb-0002/index.html` after a theme build
- **THEN** the first has, in its compound widget, a `figure.structure` carrying `data-pagefind-ignore` with an `img` whose resolved `src` is `public/substances/isopentyl-acetate/structure.svg`, which exists, with `alt` `Structure of Isopentyl acetate`
- **AND** the second has the placeholder figure and no `img`

#### Scenario: One figure per product with an image
- **WHEN** a test scans `procedures/osdb-0907/index.html` after the two-product build of the requirement "Procedure page structure", in which only `trans-stilbene` sets `structure_image`
- **THEN** its compound widget holds exactly one `figure.structure`, holding an `img` with `alt` `Structure of trans-Stilbene`, and has no placeholder

#### Scenario: Scheme image of a general procedure
- **WHEN** a test scans the page of the test collection's general procedure, which sets `scheme_image`, and the page of the fixture `tests/fixtures/general/OSDB-0140-general.md`, which does not, after a theme build that adds the latter
- **THEN** the first page's compound widget holds one figure whose `img` has the `alt` `Scheme of <title>` and the second with the placeholder, although its products' compounds set structure images

## ADDED Requirements

### Requirement: Procedure body sections
Each level-2 section of a procedure's rendered body SHALL be a `section.widget.procedure-section` inside `div.procedure-content`, in the body's order: its `div.widget__head` holds the section's `h2`, unchanged and keeping its `id`, and its `div.widget__body` holds everything that follows the heading up to the next level-2 heading or the end of the body. Content before the first level-2 heading stays outside any section, before them. A section whose heading text is one of the procedure sections that validation requires, in English or in German (procedure-validation, `tools/validate.py` `SECTIONS_BY_LANGUAGE`), carries `data-section` with its role, by position in that list, the heading text compared as validation compares section names (case ignored, runs of whitespace as one space): `summary`, `reagents`, `procedure`, `workup`, `characterization`, `notes`, `hazards` and `references`; any other section carries none.

A general procedure's scope (general-procedures "Scope table on the page") is a widget too: its `section.scope` carries the class `widget`, its `h2` stands in a `div.widget__head` and its table in a `div.widget__body`.

The screen stylesheet lays the widgets out; print keeps their document order, and the widgets' frames are not printed.

#### Scenario: Sections of the Markdown seed
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build in locale `en`
- **THEN** `div.procedure-content` holds eight `section.widget.procedure-section`, whose `h2` texts are the eight sections in order and whose `data-section` values are `summary`, `reagents`, `procedure`, `workup`, `characterization`, `notes`, `hazards` and `references`
- **AND** each `h2` is the only heading in its section's `div.widget__head`, and keeps the `id` it had before the change

#### Scenario: German sections carry the same roles
- **WHEN** a test scans `procedures/osdb-0002/index.html` of a build of the test collection in locale `de`
- **THEN** the section headed `Durchführung` carries `data-section="procedure"` and the one headed `Anmerkungen` `data-section="notes"`

#### Scenario: Every role list matches validation
- **WHEN** a test reads the role table the layouts use and `tools/validate.py`'s `SECTIONS_BY_LANGUAGE`
- **THEN** each language's section names map, in order, to the eight roles, and the table holds no other name

#### Scenario: Note links still resolve
- **WHEN** a test scans `procedures/osdb-0003/index.html` after a theme build in locale `en`
- **THEN** the elements `note-1` and `note-2` lie inside the section with `data-section="notes"`, the body's link to `#note-1` lies inside the section with `data-section="procedure"`, and its link to `#note-2` inside the one with `data-section="workup"`

#### Scenario: Scope widget
- **WHEN** a test scans the page of the test collection's general procedure after a theme build
- **THEN** its `section.scope` carries the class `widget`, holds its `h2` in a `div.widget__head` and its `table.scope-table` in a `div.widget__body`, and lies between the details wrapper and `div.procedure-content`
