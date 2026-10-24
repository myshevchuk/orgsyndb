## MODIFIED Requirements

### Requirement: Measure, responsiveness and tables
The screen layout SHALL prioritize desktop browsers with a shell up to 96rem wide, set in the system sans-serif stack; printed pages keep the text face of `tokens.css`. Running procedure paragraphs and lists SHALL keep a reading measure up to 78ch, while procedure tables SHALL use their available column width. Narrow windows SHALL retain a complete reading order, with wide tables scrolling within their own containers. Every Markdown table SHALL be rendered by `site/layouts/_markup/render-table.html` as follows:
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

#### Scenario: Desktop workspace
- **WHEN** a browser displays the home page at 1280 CSS pixels or wider
- **THEN** recent procedures and browse links occupy adjacent columns
- **AND** the all-procedures table uses the available shell width

#### Scenario: Procedure reference and text
- **WHEN** a browser displays a procedure at 1280 CSS pixels or wider
- **THEN** the body occupies a reading column on the left and the structure and metadata occupy a margin column on the right, without a panel border or background (the Marginalia design, `docs/designs/minimal/`, layout 7)
- **AND** prose has a bounded reading measure and wide tables scroll locally
- **AND** the details stay first in document order, so narrower windows, print and the search index show them before the body

#### Scenario: Print keeps document flow
- **WHEN** a procedure is printed or rendered to an A4 PDF
- **THEN** the details, structure and body retain their single-column order

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

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` with a `nav` element carrying `aria-label="Site"`. The nav links to `/procedures/`, `/reaction_types/`, `/tags/`, `/authors/` and `/search/`, with the texts `Procedures`, `Reaction types`, `Tags`, `Authors` and `Search`. The header holds no other `nav`. The link whose URL is the page's own URL carries `aria-current="page"`; otherwise the link of the section the page lies in carries `aria-current="true"`, where `/procedures-by-date/` and every procedure page lie in `/procedures/`, and every term page lies in its taxonomy's page. No other navigation link carries `aria-current`;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures`.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, the interface string named by the page's `title_key` where it has one, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build in locale `en`
- **THEN** each has the skip link, the site header with the five navigation links, one `main#main`, the footer text, both `meta` elements, exactly one `h1`, and no heading-level jump greater than one

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build in locale `en`
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

#### Scenario: Current section in the navigation
- **WHEN** a test scans the home page, both procedure lists, a procedure page, the tags page, a tag term page and the search page after a theme build
- **THEN** the home page marks no navigation link, `/procedures/` marks its own link with `aria-current="page"`, `/procedures-by-date/` and the procedure page mark `/procedures/` with `aria-current="true"`, the tags page marks `/tags/` with `page` and the term page with `true`, and the search page marks `/search/` with `page`

### Requirement: Procedure lists and their order
The site SHALL publish two lists of all procedures, each a table with the column headers `ID`, `Procedure`, `Reaction type`, `Status`, `Created` and `Modified`, and one row per procedure. The `ID` and `Procedure` cells link to the procedure page, and the `Reaction type` cell shows the vocabulary label.
- `/procedures/` lists the procedures by `id` ascending.
- `/procedures-by-date/` lists them by `date` descending, and procedures with equal `date` by `id` ascending.

Each list links to the other, and marks its own order's link with `aria-current="page"`. Neither needs JavaScript.

Above its table, each list SHALL have, in this order:
- the `h1`, followed by `p.list-count` with `role="status"`, `data-list-count`, the text `<n> entries` (`1 entry` for one) and a `data-filtered` attribute holding `{shown} of {total} entries`;
- a search form with `role="search"`, `method="get"` and an `action` resolving to `/search/`, holding an `input` with `name="q"` and an `aria-label`, and a visible submit button;
- `div.list-filters` with `data-list-filters` and `hidden`, holding a `select` with `data-filter="reaction-type"` whose options are `All` with an empty value followed by one option per reaction type in use, valued by its slug and labelled with its vocabulary label, and a `select` with `data-filter="status"` whose options are `All`, `draft`, `checked` and `retired`;
- the sort links.

Every row of a procedure table carries `data-reaction-types`, the procedure's reaction-type slugs joined by single spaces, and `data-status`, its status.

On screen, the lists follow the full-width table design (`docs/designs/minimal/`, layout 4): the tool row spans the shell with the search form on the left and the filters on the right, the sort links sit right-aligned above a table that uses the shell width, and the status column reads as plain text.

#### Scenario: Both orders
- **WHEN** a test scans `public/procedures/index.html` and `public/procedures-by-date/index.html` after a theme build, and computes both orders from the content files' front matter
- **THEN** the IDs in the rows of each table equal the computed order, and each page has a link to the other page's URL and an `aria-current="page"` link to its own

#### Scenario: List tools
- **WHEN** a test scans `public/procedures/index.html` and `public/procedures-by-date/index.html` after a theme build
- **THEN** each has the count, the search form, the hidden filters with the stated options and the sort links, every table row carries the two data attributes with the procedure's values, and the page loads `/js/list-filter.<hash>.js`

### Requirement: Content does not need JavaScript
Every procedure, list, taxonomy, term and home page SHALL show all of its content without running JavaScript. Scripts add only these:
- `site/assets/js/site.js` reveals and wires the print button (`window.print()`) and the SMILES copy button.
- `site.js` replaces the print-facts URL with `location.href` when the protocol is `http:` or `https:`.
- The copy button writes the SMILES string with the Clipboard API. When that fails or is unavailable, it selects the SMILES text instead.
- The search page's scripts run the search, as in the site-search spec.
- `site/assets/js/list-filter.js`, loaded by the two all-procedures lists only, reveals `div.list-filters`. When a select changes, it hides each table row whose `data-reaction-types` does not contain the selected reaction type or whose `data-status` differs from the selected status, an empty value matching every row, and sets the text of `p.list-count` from its `data-filtered` template, or back to the original text when neither filter is set. Its matching function is exposed as `globalThis.OrgSynListFilter.rowMatches(row, filters)`.

The JavaScript-enhancement buttons, the print button (`data-print`) and the SMILES copy button (`data-copy-smiles`), carry `hidden` in the published HTML, and only the script reveals them. No other button is hidden: the home page's search submit button in particular stays visible and works without JavaScript.

#### Scenario: Static HTML holds the content
- **WHEN** a test scans every procedure page after a theme build, without running scripts
- **THEN** the metadata values, the rendered body sections and the links are present in the HTML, every `button` with `data-print` or `data-copy-smiles` has the `hidden` attribute, and no other `button` on any page under `public/` has it

#### Scenario: Buttons work in a browser
- **WHEN** the orchestrator opens a procedure page in a browser with JavaScript (manual verification, tasks.md section 9)
- **THEN** the print button is visible and opens the print dialog, the Copy button copies or selects the SMILES string, and with JavaScript disabled neither button is shown and the page is otherwise unchanged
- **AND** with JavaScript disabled, the home page's Search button is visible and submitting the form loads `/search/?q=<term>`, which shows the `noscript` text

#### Scenario: List filter matching
- **WHEN** a Node test loads `site/assets/js/list-filter.js` and calls `rowMatches` with rows and filter values
- **THEN** a row matches when each set filter equals its status or is one of its reaction types, and an empty filter matches every row
