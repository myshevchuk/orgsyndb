# print-layout Specification

## Purpose
Define the print stylesheet and batch PDFs: A4 pages with a running header and page footer, black on white, first-page URL facts, break rules, and the checks that nothing is clipped.

## Requirements

### Requirement: A4 page box
The print stylesheet SHALL set `@page` to `size: A4` with margins of at least 15 mm on every side. WeasyPrint's PDFs of procedure pages are then A4.

#### Scenario: A4 PDFs
- **WHEN** a test runs `pdfinfo` on every PDF after a PDF build
- **THEN** each reports `Page size:` of `595.276 x 841.89 pts (A4)` and at least one page

### Requirement: Running header and page numbers
Each procedure page SHALL give WeasyPrint a running header and footer:
- **Header.** Its `head` holds a `style` element with an `@page` rule. The rule sets the `@top-left` margin box's `content` to the procedure's `id` and the `@top-right` box's `content` to its `title`, both as CSS strings escaped by Hugo's HTML template engine.
- **Footer.** The same rule sets `@bottom-center` to `"Page " counter(page) " of " counter(pages)` on an English site and `"Seite " counter(page) " von " counter(pages)` on a German one. The print stylesheet sets the English footer for every other page.

#### Scenario: Header and footer on every page
- **WHEN** a test reads the page text of every page `i` of every PDF of `n` pages after a PDF build in locale `en`
- **THEN** each page text contains the procedure's `id`, its whitespace-normalised `title`, and the line text `Page <i> of <n>`

#### Scenario: Title with quotes and markup characters
- **WHEN** a PDF build includes `tests/fixtures/theme/OSDB-0906-quoted-title.md`, whose `title` is `Bob's "best" </style> ester \ x`
- **THEN** `pdf/OSDB-0906-quoted-title.pdf` exists, and the first line of its first page text ends with that exact title

### Requirement: Black on white
The print stylesheet SHALL print black text on a white page, whatever the screen colour scheme:
- Every `color` declaration in `site/assets/css/print.css` is `#000`.
- Every `background` or `background-color` declaration in it is `#fff`, `none` or `transparent`.
- It sets `color: #000` and `background: #fff` on `html`.

The dark tokens live only in the screen stylesheet, which the site-theme spec links with `media="screen"`.

#### Scenario: Print colours
- **WHEN** a test parses the declarations of `site/assets/css/print.css`
- **THEN** every `color` value is `#000`, every `background` or `background-color` value is `#fff`, `none` or `transparent`, and the `html` rule sets both

### Requirement: Navigation and controls are not printed
The print stylesheet SHALL hide the following:
- the site header and navigation;
- the footer;
- the skip link;
- `p.actions` and every `button`;
- any search form;
- the structure placeholder.

It keeps the sample banner, the procedure header, the print facts and the indexed body.

#### Scenario: No chrome in the PDFs
- **WHEN** a test reads all page texts of every PDF after a PDF build
- **THEN** none contains `Skip to content`, `Print / Save as PDF`, `No structure image` or `OrgSynDB · internal procedures`, and no line contains both `Reaction types` and `Authors`
- **AND** the first page of every sample's PDF contains `Sample data — quantities not experimentally verified.`

### Requirement: First-page facts
The procedure header SHALL contain a `p.print-facts`, shown only in print, whose text is the page's full URL, then ` · `, the `id`, ` · status `, the `status`, ` · last modified `, and the `lastmod` formatted `YYYY-MM-DD HH:MM`. The full URL is the whole text of a `span.page-url` inside it, built as follows:
- It is Hugo's `site.Params.siteurl` with any trailing `/` removed, followed by the page's path `/procedures/<slug>/`.
- `site/hugo.toml` sets `[params] siteurl = "http://127.0.0.1:8000"`, the default origin of `tools/orgsyndb serve`.
- The environment variable `HUGO_PARAMS_SITEURL` overrides it, for example with an internal host.
- In a browser, the site script replaces the span's text with `location.href` when the protocol is `http:` or `https:`.

The URL is plain text. The `siteurl` value appears in published HTML only as the text of `span.page-url`, never in an attribute. So `relativeURLs` does not rewrite it, and the site-build "No fetches from other hosts" rules, which concern fetching attributes, `url()` and `@import`, do not apply to it.

#### Scenario: Full URL on the first page by default
- **WHEN** a test reads the first page text of `pdf/OSDB-0002-aspirin.pdf` after a PDF build without `HUGO_PARAMS_SITEURL`
- **THEN** it contains `http://127.0.0.1:8000/procedures/osdb-0002/ · OSDB-0002 · status draft · last modified 2026-10-19 23:50`

#### Scenario: Site URL from the environment
- **WHEN** a PDF build runs with `HUGO_PARAMS_SITEURL=https://orgsyndb.example.invalid/` in the environment
- **THEN** the first page text of `pdf/OSDB-0002-aspirin.pdf` contains `https://orgsyndb.example.invalid/procedures/osdb-0002/`, and does not contain `127.0.0.1`

#### Scenario: The URL is text only
- **WHEN** a test scans every HTML file under `public/` after a theme build
- **THEN** every occurrence of `http://127.0.0.1:8000` is inside the text of a `span.page-url`, and each such span's text equals `http://127.0.0.1:8000` followed by its page's path
- **AND** no attribute value contains `127.0.0.1`

### Requirement: Page-break control
The print stylesheet SHALL declare these rules:
- `break-after: avoid` on `h1`, `h2`, `h3` and `h4`;
- `break-inside: avoid` on `tr`, `li`, `figure` and the metadata panel's rows;
- `display: table-header-group` on `thead`.

In WeasyPrint's PDFs, no page but the last ends with a section heading, and no numbered Procedure step or table row is split across pages.

#### Scenario: Declarations present
- **WHEN** a test parses `site/assets/css/print.css`
- **THEN** each listed selector receives the listed declaration

#### Scenario: No page ends on a heading
- **WHEN** a test reads every page but the last of every PDF after a PDF build, drops blank lines and the `Page <i> of <n>` line, and takes the last line
- **THEN** that line is not equal to the text of any `h2` of the procedure's page

#### Scenario: Steps and rows stay on one page
- **WHEN** a test takes the text of every `li` of the `ol` under the `Procedure` heading, and of every `tr` of the Reagents table, from each procedure page, with whitespace removed
- **THEN** each occurs within the whitespace-free raw page text of a single page of that procedure's PDF

### Requirement: Nothing is clipped
Printed procedures SHALL lose no content. The print stylesheets prevent clipping by construction:
- **Clipping CSS.** No stylesheet a procedure page loads in print media (`tokens.css`, `base.css`, `print.css`) declares `overflow`, `overflow-x` or `overflow-y` as `hidden` or `clip`. None declares a `height` or `max-height` other than `auto` or `none`, except `max-height` on a selector whose subject is `img`.
- **Wide tables.** Tables are `width: 100%`. Cells of `.num` columns do not wrap, and all other cells may break anywhere (`overflow-wrap: anywhere`), so a table wider than the page wraps instead of overflowing.
- **Long sample.** The longest sample, OSDB-0004, prints on at least three pages.
- **Page counts.** Every PDF has between one and ten pages.

The automated PDF checks below detect content pushed past the left or right margin, and text missing from a page's text layer. They cannot detect content hidden inside its own box, or clipped graphics: clipped text stays in the text layer with in-margin boxes. The acceptance evidence that nothing is clipped is the orchestrator's review of the rendered page images.

#### Scenario: No clipping CSS in print
- **WHEN** a test parses the declarations of `site/assets/css/tokens.css`, `base.css` and `print.css`, including those inside `@media` and `@page` blocks
- **THEN** no `overflow`, `overflow-x` or `overflow-y` value is `hidden` or `clip`, and every `height` or `max-height` value is `auto` or `none`, apart from `max-height` on selectors whose last compound selector is `img`

#### Scenario: Every word within the margins
- **WHEN** a test reads `pdftotext -bbox` of every PDF after a PDF build
- **THEN** on every page every word has `xMin` of at least 15 mm minus 1 pt and `xMax` of at most the page width minus 15 mm plus 1 pt, measured in points

#### Scenario: Every table cell is printed
- **WHEN** a test takes the text of every `td` and `th` of every table on each procedure page, with whitespace removed
- **THEN** each occurs within the whitespace-free raw page text of some page of that procedure's PDF

#### Scenario: The checks do not see hidden overflow
- **WHEN** a test renders `tests/fixtures/theme/clip-negative-control.html` with `weasyprint --allowed-protocols file`, a page whose `div style="height:1px; overflow:hidden"` holds the word `HiddenClippedSentinel`, and applies the margin check and the text check to it
- **THEN** both checks pass although the word is clipped, its raw page text contains `HiddenClippedSentinel`, and the clipping-CSS check rejects the fixture's inline style
- **AND** the test's docstring states that this records the checks' limit

#### Scenario: The long sample spans pages
- **WHEN** a test runs `pdfinfo` on `pdf/OSDB-0004-4-acetylbiphenyl.pdf` and on every other PDF after a PDF build
- **THEN** the first has at least three pages, and every PDF has between one and ten

#### Scenario: Page images show nothing clipped
- **WHEN** the orchestrator renders every page of at least three PDFs, OSDB-0003, OSDB-0004 and OSDB-0008, to images with `pdftoppm` and inspects them (manual verification, tasks.md section 9)
- **THEN** no text, table, figure or rule is cut off at a box edge or the page edge, and the structure drawing on OSDB-0003 is complete

### Requirement: Warning-free rendering
WeasyPrint 70.0 SHALL render every procedure page without a warning. No stylesheet a procedure page loads in print media uses a property, value or media query that WeasyPrint does not support.

#### Scenario: Clean pdf run
- **WHEN** a PDF build completes
- **THEN** it exits 0, and no line of its stdout or stderr begins with `WARNING:`

### Requirement: Browser print fallback
Printing a procedure page from Firefox or Chromium SHALL use the same print stylesheet. The page prints on A4 in black on white, without navigation, buttons or a dark scheme, with the full page URL in the print facts, and with no content lost. Running headers and page numbers from `@page` margin boxes are required only of WeasyPrint. A browser that ignores margin boxes, as Firefox 158 does, still meets this requirement.

#### Scenario: Firefox print
- **WHEN** the orchestrator prints `procedures/osdb-0004/` to PDF from Firefox on A4 (manual verification, tasks.md section 9) and renders its pages as images
- **THEN** the pages are black on white, show the banner, the full `http://127.0.0.1:…` URL, the ID, status and modified date on the first page, show no navigation or buttons, and every word lies within the page
