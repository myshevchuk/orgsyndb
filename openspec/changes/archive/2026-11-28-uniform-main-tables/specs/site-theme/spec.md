## MODIFIED Requirements

### Requirement: Measure and tables
The screen layout SHALL prioritize desktop browsers, set in the system sans-serif stack; printed pages keep the text face of `tokens.css`. Running procedure paragraphs and lists SHALL keep a reading measure up to 78ch, while procedure tables SHALL use their available column width. Narrower windows SHALL stack the columns in document order, and wide tables SHALL scroll within their own containers. Every Markdown table SHALL be rendered by `site/layouts/_markup/render-table.html` as follows:
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
