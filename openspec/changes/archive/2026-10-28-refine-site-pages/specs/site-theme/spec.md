## MODIFIED Requirements

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` holding, in this order:
  - `a.site-title`, linking `/` with the text `OrgSynDB`;
  - a `nav` element carrying `aria-label="Site"`, which links, in this order, to `/procedures/`, `/reaction_types/` and `/help/`, with the texts `Procedures`, `Reaction types` and `Help`. The header holds no other `nav`;
  - `form.site-search` with `role="search"` and `method="get"`, holding one `input` with `type="search"` and `name="q"`, and a `button` with `type="submit"` and the text `Search`. On the catalogue and term pages it is the catalogue's search form, with the `action`, attributes and texts that site-catalogue "Catalogue controls" gives. On every other page its `action` resolves to `/procedures/`, and its input carries `aria-label="Search procedures"` and the placeholder `Product, CAS, SMILES or keyword`;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures · built <time>`, where `<time>` is a `time` element whose `datetime` is the time the site was built, as an RFC 3339 date-time, and whose text is that time as `YYYY-MM-DD HH:MM`. Every page of one build shows the same time.

The navigation link whose URL is the page's own URL carries `aria-current="page"`. Otherwise the link of the section the page lies in carries `aria-current="true"`: every procedure page, `/tags/`, `/authors/` and their term pages lie in `/procedures/`; every reaction-type term page lies in `/reaction_types/`; every help page lies in `/help/`. No other navigation link carries `aria-current`. Every page has exactly one `input` with `name="q"`: the header's.

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
- **AND** on every page except `/procedures/` and the term pages the form's `action` resolves to `/procedures/` and its input has the stated `aria-label` and placeholder

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build in locale `en`
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

#### Scenario: Current section in the navigation
- **WHEN** a test scans the home page, `/procedures/`, a procedure page, the three taxonomy pages, a term page of each taxonomy, the help index and a help page after a theme build
- **THEN** the home page marks no navigation link; `/procedures/` marks its own link with `aria-current="page"`; the procedure page, `/tags/`, `/authors/`, the tag term page and the author term page mark `/procedures/` with `aria-current="true"`; `/reaction_types/` marks its own link with `page` and its term page with `true`; `/help/` marks its own link with `page`; and the help page `/help/schema/` marks `/help/` with `true`

#### Scenario: The header does not move between pages
- **WHEN** the orchestrator measures the header and the `h1` of the home page, `/procedures/`, a term page, a procedure page and the help index in a browser at 1280 and at 500 CSS pixels (manual verification, tasks.md section 3)
- **THEN** at each width the header has the same height, the site title, the navigation and the search form the same positions and sizes, and the `h1` the same font size on every page

### Requirement: Procedure page structure
Each procedure page's `main` element SHALL contain, in document order:
1. the sample banner, when the requirement "Sample banner" applies;
2. `header.procedure-header`, holding:
   - `p.procedure-id`, containing the ID in an element with `data-pagefind-meta="id"`, and the status badge `span.badge.badge--<status>` whose text is the status;
   - the `h1` with the title;
   - the print facts of the print-layout spec;
   - `p.actions`, holding `button.print-button` with `type="button"`, the attribute `data-print`, the text `Print / Save as PDF` and the attribute `hidden`;
3. `article.procedure`, the only element with `data-pagefind-body`, holding in order:
   - the metadata panel;
   - the structure figure;
   - the rendered body;
   - the index-terms element and then the SMILES index element of the site-search spec.

#### Scenario: Header and body in order
- **WHEN** a test scans `procedures/osdb-0002/index.html` and `procedures/osdb-0001/index.html` after a theme build
- **THEN** each has the elements in the stated order, the `h1` and the visible ID lie outside the `article`, and the `article` contains the `Summary` heading after the metadata panel

### Requirement: Metadata panel
The metadata panel SHALL be a `dl.metadata`, the first element of the details wrapper at the start of `article.procedure`. It holds one `dt`/`dd` pair per field, with these labels in this order, each pair present only when the field is set. The panel repeats nothing the procedure header shows: the ID is in the header's ID line, and the product name, when it equals the title, is the `h1`.
- `Product` (the `product.name`), only when it differs from the title;
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
- **THEN** the `dt` texts are, in order, `Product`, `Formula`, `MW`, `CAS`, `SMILES`, `Scale`, `Yield`, `Reaction type`, `Tags`, `Authors`, `Created`, `Modified` and `Precursors`
- **AND** the values include `Acetylsalicylic acid`, `C9H8O4` with three `<sub>` elements, `180.16 g/mol`, `50-78-2`, `CC(=O)Oc1ccccc1C(=O)O` in `code[data-smiles]`, `20 mmol`, `75 %`, a link with text `Acylation`, links `sample-data` and `acetylation`, links `A. Example` and `C. Example`, and `<time datetime="2026-10-19T23:46:11+02:00">`

#### Scenario: Panel labels follow the canonical order on every page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** each page's `dt` texts are a subsequence of the canonical label list in its order, they include every label whose field the content file sets except `Product` where `product.name` equals the title, no page has an `ID` label, and whitespace follows every `</dt>`

#### Scenario: A product named like its procedure
- **WHEN** a test scans `procedures/osdb-0001/index.html`, whose title and `product.name` are both `Salicylic acid`, after a theme build
- **THEN** its panel has no `Product` pair, and its index-terms element reads `OSDB-0001 Salicylic acid`

### Requirement: Home page
The home page's `main` SHALL contain, in this order:
- `div.home-intro`, holding the `h1` `Synthetic procedures` and a `p.lede` with the text `The group's procedures, written in Org or Markdown to one schema.`;
- `div.home-layout`, holding, in this order:
  - `section.home-recent`, with the `h2` `Recently updated`, then an `ol.recent-list` with one `li` per procedure for the first five published procedures, or all when there are fewer, ordered by `lastmod` as an instant, newest first, and by `id` ascending for equal instants. Each `li` holds an `a` linking the procedure page whose text is `<id> <title>`, then `<time datetime="<RFC 3339 lastmod>">YYYY-MM-DD</time>`. After the list, a `p` links `/procedures/?sort=modified` with the text `All procedures, recently updated first`;
  - `section.home-unchecked`, only when some published procedure has the status `draft`, with the `h2` `Not yet checked`, then an `ol.unchecked-list` with one `li` per draft for the first five drafts by `id` ascending, or all when there are fewer: the drafts the catalogue lists first under `/procedures/?status=draft`. Each `li` holds an `a` linking the procedure page whose text is `<id> <title>`, then `<time datetime="<RFC 3339 date>">YYYY-MM-DD</time>` of its creation. After the list, a `p` holds a link to `/procedures/?status=draft` with the text `All draft procedures`, then ` ` and a `span.count` reading `(<n>)`, `n` the number of drafts;
  - `section.home-browse`, with the `h2` `Browse`, then a `ul.browse-list` whose `li` entries hold, in this order, a link and then ` ` and a `span.count` reading `(<n>)`: `All procedures` to `/procedures/`, `n` the number of published procedures; `Reaction types` to `/reaction_types/`, `Tags` to `/tags/` and `Authors` to `/authors/`, each `n` the number of terms of that taxonomy in use.

The counts are computed from the published procedures and written with the site language's digit grouping. The home page's `main` holds no form, no `input` and no procedure table. On screen, from 70rem up, the recent and unchecked lists form the first column and the browse list the second.

#### Scenario: Home page content
- **WHEN** a test scans `public/index.html` of a theme build that adds the catalogue fixtures to the test collection, in locale `en`
- **THEN** the `h1` is `Synthetic procedures`, and the recent list holds the first five procedures in the computed order, each ID once, with the stated link texts and dates, and two fixtures whose `lastmod` is the same instant are ordered by ID
- **AND** the unchecked list holds the first five drafts by ID with their creation dates, and its link reads the number of drafts computed from the published content files
- **AND** the browse list has the four entries in order, with the stated targets, and counts equal to those computed from the published content files
- **AND** `main` has the links to `/procedures/?sort=modified` and `/procedures/?status=draft`, and no `form`, `input` or `table`

#### Scenario: Nothing waits for a check
- **WHEN** a test scans `public/index.html` of a theme build of a collection whose procedures are all `checked`
- **THEN** it has no `section.home-unchecked` and no link to `/procedures/?status=draft`

## ADDED Requirements

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
