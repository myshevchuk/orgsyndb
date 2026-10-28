## MODIFIED Requirements

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
   - `dl.key-facts`, when the procedure sets `scale` or `yield_percent`, holding a `dt`/`dd` pair `Scale` and a pair `Yield`, as `<n> %`, each only when its field is set, with whitespace after each `</dt>`;
   - the print facts of the print-layout spec;
   - `p.actions`, holding `button.print-button` with `type="button"`, the attribute `data-print`, the text `Print / Save as PDF` and the attribute `hidden`;
   - the structure figure of the requirement "Structure image slot";
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

### Requirement: Metadata panel
The metadata panel SHALL be a `dl.metadata`, the first element of the details wrapper at the start of `article.procedure`. It holds one `dt`/`dd` pair per field, with these labels in this order, each pair present only when the field is set. The panel repeats nothing the procedure header shows: the ID is in the header's ID line, the product name, when it equals the title, is the `h1`, the scale and yield are its key facts, and the checkers of a checked procedure are its sign-off.
- `Product` (the `product.name`), only when it differs from the title;
- `Formula`, where each digit run is wrapped in `<sub>`;
- `MW`, as `<mw> g/mol`;
- `CAS`;
- `SMILES`, as a `<code data-smiles>` with the string, followed by `button.copy-button` with `type="button"`, `data-copy-smiles`, the text `Copy` and `hidden`;
- `Reaction type`, as a link to the term page whose text is the vocabulary label;
- `Tags`, as one link per tag to its term page, with the tag as text;
- `Authors`, as one link per author to the author's term page, with the name as text;
- `Checked by`, as the names joined by `, `, not linked, only when the status is not `checked`;
- `Created`, as `<time datetime="<RFC 3339 date>">YYYY-MM-DD HH:MM</time>`;
- `Modified`, the same for `lastmod`;
- `Precursors`, as in the requirement "Precursor and used-in links";
- `Used in`, as in the same requirement.

Whitespace separates every `</dt>` from the following `<dd>` in the published HTML.

#### Scenario: Panel of the Markdown seed
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build
- **THEN** the `dt` texts are, in order, `Product`, `Formula`, `MW`, `CAS`, `SMILES`, `Reaction type`, `Tags`, `Authors`, `Created`, `Modified` and `Precursors`
- **AND** the values include `Acetylsalicylic acid`, `C9H8O4` with three `<sub>` elements, `180.16 g/mol`, `50-78-2`, `CC(=O)Oc1ccccc1C(=O)O` in `code[data-smiles]`, a link with text `Acylation`, links `sample-data` and `acetylation`, links `A. Example` and `C. Example`, and `<time datetime="2026-10-19T23:46:11+02:00">`

#### Scenario: Panel labels follow the canonical order on every page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** each page's `dt` texts are a subsequence of the canonical label list in its order, they include every label whose field the content file sets except `Product` where `product.name` equals the title and `Checked by` where the status is `checked`, no page has an `ID`, `Scale` or `Yield` label, and whitespace follows every `</dt>`

#### Scenario: A product named like its procedure
- **WHEN** a test scans `procedures/osdb-0001/index.html`, whose title and `product.name` are both `Salicylic acid`, after a theme build
- **THEN** its panel has no `Product` pair, and its index-terms element reads `OSDB-0001 Salicylic acid`

### Requirement: Structure image slot
When a procedure sets `structure_image`, its procedure header SHALL end with a `figure.structure` holding an `img` whose `src` resolves to the published copy of the collection's `static/<structure_image>`, and whose `alt` is `Structure of <product name>`. Otherwise the header ends with a `figure.structure.structure--placeholder` holding `div.structure__slot` with the text `No structure image`. The print stylesheet hides the placeholder.

#### Scenario: Image and placeholder
- **WHEN** a test scans `procedures/osdb-0003/index.html` and `procedures/osdb-0002/index.html` after a theme build
- **THEN** the first has an `img` whose resolved `src` is `public/structures/osdb-0003.svg`, which exists, with `alt` `Structure of Isopentyl acetate`
- **AND** the second has the placeholder figure and no `img`
