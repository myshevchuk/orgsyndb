## MODIFIED Requirements

<!-- Reason: German pages are published under /de/. -->

### Requirement: Merged procedures section
A build SHALL publish each procedure content file of `build/export/` and `md/procedures/` as one page, whatever its `date`, `publishDate` or `expiryDate`: an English file at `public/procedures/<slug>/index.html`, a German file (named `*.de.md`) at `public/de/procedures/<slug>/index.html`. No other file from those two directories is published.

#### Scenario: Org-sourced and Markdown-sourced pages
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on the seed procedures
- **THEN** `public/procedures/osdb-0001/index.html` (from Org) and `public/procedures/osdb-0002/index.html` (from Markdown) exist
- **AND** the subdirectories of `public/procedures/` are exactly the `slug` values of the English content files in `build/export/` and `md/procedures/`, and those of `public/de/procedures/` exactly the `slug` values of the German ones

#### Scenario: Future-dated procedure is published, indexed and printed
- **WHEN** an integration test adds to `md/procedures/` a copy of `tests/fixtures/baseline/OSDB-0100-baseline.md` whose `date` and `lastmod` are `2099-01-01T10:00:00+01:00`, and runs `tools/orgsyndb -C <collection> pdf`
- **THEN** it exits 0, `public/procedures/osdb-0100/index.html` exists, `languages.en.page_count` in `public/pagefind/pagefind-entry.json` counts it, and `pdf/OSDB-0100-baseline.pdf` exists

#### Scenario: Expired procedure is still published
- **WHEN** an integration test adds to `md/procedures/` a copy of the same baseline with the line `expiryDate = 2026-02-01T10:00:00+01:00` added to its front matter, and builds
- **THEN** the build exits 0, with the validator's `unknown field` warning for `expiryDate`, and `public/procedures/osdb-0100/index.html` exists

#### Scenario: Stray file and section index are not published
- **WHEN** an integration test adds `md/procedures/notes.txt` and an `md/procedures/_index.md` titled `Hijack`, then builds
- **THEN** the build exits 0, `public/procedures/notes.txt` does not exist, and `public/procedures/index.html` does not contain `Hijack`

<!-- Reason: each page declares its own language. -->

### Requirement: Minimal layout contract
The layouts SHALL live in `site/layouts/`. Whichever layouts are in place, they meet all of the following:
- On every procedure page, the rendered body is inside exactly one element carrying `data-pagefind-body`.
- No other page carries `data-pagefind-body`.
- The procedure page shows the procedure's `title` and `id`.
- Every HTML page has `<html lang="<language>">`, `en` for English pages and `de` for German ones, `<meta charset="utf-8">` and a `<title>` element.
- Asset references in layouts are root-relative paths.
- A procedure page's content does not depend on JavaScript.

#### Scenario: One indexed body per procedure page
- **WHEN** an integration test builds the shipped procedures and parses every HTML file under `public/` with `html.parser`
- **THEN** each procedure page of a content file in `build/export/` or `md/procedures/` has exactly one element with `data-pagefind-body`, and that element contains the procedure's `Summary` heading, or `Zusammenfassung` on a German page
- **AND** no other HTML file has such an element

#### Scenario: Title and ID shown
- **WHEN** the same test reads `procedures/osdb-0002/index.html`
- **THEN** the text outside the indexed body contains the seed's title and `OSDB-0002`

<!-- Reason: one index per language. -->

### Requirement: Search index
`build` SHALL run Pagefind over `public/` after Hugo, writing the bundle to `public/pagefind/`. Only procedure pages are indexed, each under the language of its page.

#### Scenario: Bundle location and page count
- **WHEN** an integration test builds the seeds
- **THEN** `public/pagefind/pagefind.js`, `public/pagefind/pagefind-ui.js` and `public/pagefind/pagefind-ui.css` exist
- **AND** `public/pagefind/pagefind-entry.json` parses as JSON with `version` equal to `1.5.2`, `languages.en.page_count` equal to the number of English procedure content files in `build/export/` and `md/procedures/`, and `languages.de.page_count` equal to the number of German ones
