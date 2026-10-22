## MODIFIED Requirements

### Requirement: Measure, responsiveness and tables
The screen layout SHALL prioritize desktop browsers with a shell up to 96rem wide. Running procedure paragraphs and lists SHALL keep a reading measure up to 78ch, while procedure tables SHALL use their available column width. Narrow windows SHALL retain a complete reading order, with wide tables scrolling within their own containers. Every Markdown table SHALL be rendered by `site/layouts/_markup/render-table.html` as follows:
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
- **THEN** metadata and structure occupy a details column beside the body
- **AND** prose has a bounded reading measure and wide tables scroll locally

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
