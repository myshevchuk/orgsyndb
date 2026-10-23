## RENAMED Requirements

- FROM: `### Requirement: Measure, responsiveness and tables`
- TO: `### Requirement: Measure and tables`

## MODIFIED Requirements

### Requirement: Measure and tables
The screen layout SHALL prioritize desktop browsers with a shell up to 96rem wide, set in the system sans-serif stack; printed pages keep the text face of `tokens.css`. Running procedure paragraphs and lists SHALL keep a reading measure up to 78ch, while procedure tables SHALL use their available column width. Narrower windows SHALL stack the columns in document order, and wide tables SHALL scroll within their own containers. Every Markdown table SHALL be rendered by `site/layouts/_markup/render-table.html` as follows:
- The `<table>` is the only child of a `div.table-scroll` with `tabindex="0"`, `role="region"` and a non-empty `aria-label`.
- Each header cell is a `th` with `scope="col"`.
- Every cell of a column whose header text is `CAS`, `MW (g/mol)`, `mmol` or `Equiv` carries `class="num"`.
- A newline separates adjacent cells in the output.

The screen stylesheet gives `.table-scroll` `overflow-x: auto`, so a wide table scrolls inside its own container. The base stylesheet gives `.num` cells `white-space: nowrap` and right alignment.

#### Scenario: Reagents tables are wrapped and marked
- **WHEN** a test scans every procedure page after a theme build
- **THEN** the table under the `Reagents` heading is the only child of a `div.table-scroll` with the three attributes, its header cells read `Reagent`, `CAS`, `MW (g/mol)`, `Amount`, `mmol` and `Equiv`, and exactly the cells of columns 2, 3, 5 and 6 carry `class="num"`

#### Scenario: Desktop workspace
- **WHEN** a browser displays the home page at 1280 CSS pixels or wider
- **THEN** recent procedures and browse links occupy adjacent columns
- **AND** the all-procedures table uses the available shell width

#### Scenario: Procedure reference and text
- **WHEN** a browser displays a procedure at 1280 CSS pixels or wider
- **THEN** the body occupies a reading column on the left and the structure and metadata occupy a margin column on the right, without a panel border or background
- **AND** prose has a bounded reading measure and wide tables scroll locally
- **AND** the details stay first in document order, so print and the search index show them before the body

#### Scenario: Print keeps document flow
- **WHEN** a procedure is printed or rendered to an A4 PDF
- **THEN** the details, structure and body retain their single-column order


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

On screen, each list is a full-width table: the tool row spans the shell with the search form on the left and the filters on the right, the sort links sit right-aligned above a table that uses the shell width, and the status column reads as plain text.

#### Scenario: Both orders
- **WHEN** a test scans `public/procedures/index.html` and `public/procedures-by-date/index.html` after a theme build, and computes both orders from the content files' front matter
- **THEN** the IDs in the rows of each table equal the computed order, and each page has a link to the other page's URL and an `aria-current="page"` link to its own

#### Scenario: List tools
- **WHEN** a test scans `public/procedures/index.html` and `public/procedures-by-date/index.html` after a theme build
- **THEN** each has the count, the search form, the hidden filters with the stated options and the sort links, every table row carries the two data attributes with the procedure's values, and the page loads `/js/list-filter.<hash>.js`

