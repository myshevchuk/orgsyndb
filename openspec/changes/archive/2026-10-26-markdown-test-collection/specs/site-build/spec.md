## MODIFIED Requirements

### Requirement: Merged procedures section
A build SHALL publish each procedure ID of the content files of `build/export/` and `md/procedures/` as one page at `public/procedures/<slug>/index.html`, from the variant that the localization spec chooses, whatever its `date`, `publishDate` or `expiryDate`. No other file from those two directories is published.

#### Scenario: Org-sourced and Markdown-sourced pages
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on a copy of the demo collection
- **THEN** `public/procedures/osdb-0001/index.html` (from Org) and `public/procedures/osdb-0002/index.html` (from Markdown) exist
- **AND** the subdirectories of `public/procedures/` are exactly the `slug` values of the published content files

#### Scenario: Future-dated procedure is published, indexed and printed
- **WHEN** an integration test adds to `md/procedures/` a copy of `tests/fixtures/baseline/OSDB-0100-baseline.md` whose `date` and `lastmod` are `2099-01-01T10:00:00+01:00`, and runs `tools/orgsyndb -C <collection> pdf`
- **THEN** it exits 0, `public/procedures/osdb-0100/index.html` exists, `languages.de.page_count` in `public/pagefind/pagefind-entry.json` counts it, and `pdf/OSDB-0100-baseline.pdf` exists

#### Scenario: Expired procedure is still published
- **WHEN** an integration test adds to `md/procedures/` a copy of the same baseline with the line `expiryDate = 2026-02-01T10:00:00+01:00` added to its front matter, and builds
- **THEN** the build exits 0, with the validator's `unknown field` warning for `expiryDate`, and `public/procedures/osdb-0100/index.html` exists

#### Scenario: Stray file and section index are not published
- **WHEN** an integration test adds `md/procedures/notes.txt` and an `md/procedures/_index.md` titled `Hijack`, then builds
- **THEN** the build exits 0, `public/procedures/notes.txt` does not exist, and `public/procedures/index.html` does not contain `Hijack`

<!-- Reason: pages declare the site's language. -->

### Requirement: Minimal layout contract
The layouts SHALL live in `site/layouts/`. Whichever layouts are in place, they meet all of the following:
- On every procedure page, the rendered body is inside exactly one element carrying `data-pagefind-body`.
- No other page carries `data-pagefind-body`.
- The procedure page shows the procedure's `title` and `id`.
- Every HTML page has `<html lang="<language>">` with the site's language, `<meta charset="utf-8">` and a `<title>` element.
- Asset references in layouts are root-relative paths.
- A procedure page's content does not depend on JavaScript.

#### Scenario: One indexed body per procedure page
- **WHEN** an integration test builds a copy of the test collection `tests/fixtures/collection/` and parses every HTML file under `public/` with `html.parser`
- **THEN** each procedure page of a published content file has exactly one element with `data-pagefind-body`, and that element contains the procedure's `Summary` or `Zusammenfassung` heading
- **AND** no other HTML file has such an element

#### Scenario: Title and ID shown
- **WHEN** the same test reads `procedures/osdb-0002/index.html`
- **THEN** the text outside the indexed body contains the title of the published variant and `OSDB-0002`

<!-- Reason: the index is in the site's language and counts IDs. -->

### Requirement: No fetches from other hosts
A built site SHALL contain no reference that makes a browser or WeasyPrint fetch from a host other than the serving one. The rules are:
- In HTML, no `src`, `srcset`, `poster` or `data` attribute, and no `href` on a `<link>` element, has a value beginning with `http:`, `https:` or `//`.
- In HTML `style` attributes, `<style>` elements and CSS files under `public/` (including `public/pagefind/`), no `url(...)` or `@import` target begins with one of those prefixes.
- Links in `<a href>` are not fetches and are allowed, for example literature citations.

#### Scenario: Seed build fetches nothing remote
- **WHEN** an integration test builds a copy of the test collection `tests/fixtures/collection/` and scans `public/` with the rules above
- **THEN** no violation is found

### Requirement: Search index
`build` SHALL run Pagefind over `public/` after Hugo, writing the bundle to `public/pagefind/`. Only procedure pages are indexed, under the site's language.

#### Scenario: Bundle location and page count
- **WHEN** an integration test builds a copy of the test collection `tests/fixtures/collection/`
- **THEN** `public/pagefind/pagefind.js`, `public/pagefind/pagefind-ui.js` and `public/pagefind/pagefind-ui.css` exist
- **AND** `public/pagefind/pagefind-entry.json` parses as JSON with `version` equal to `1.5.2`, `languages` holding only the site's language, and its `page_count` equal to the number of published procedures
