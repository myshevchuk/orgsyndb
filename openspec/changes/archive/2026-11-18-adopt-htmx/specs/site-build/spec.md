## MODIFIED Requirements

### Requirement: Minimal layout contract
The layouts SHALL live in `site/layouts/`. Whichever layouts are in place, they meet all of the following:
- On every procedure page, the rendered body is inside exactly one element carrying `data-pagefind-body`.
- No other page carries `data-pagefind-body`.
- The procedure page shows the procedure's `title` and `id`.
- Every HTML page has `<html lang="<language>">` with the site's language, `<meta charset="utf-8">` and a `<title>` element.
- Asset references in layouts are root-relative paths.

#### Scenario: One indexed body per procedure page
- **WHEN** an integration test builds a copy of the test collection `tests/fixtures/collection/` and parses every HTML file under `public/` with `html.parser`
- **THEN** each procedure page of a published content file has exactly one element with `data-pagefind-body`, and that element contains the procedure's `Summary` or `Zusammenfassung` heading
- **AND** no other HTML file has such an element

#### Scenario: Title and ID shown
- **WHEN** the same test reads `procedures/osdb-0002/index.html`
- **THEN** the text outside the indexed body contains the title of the published variant and `OSDB-0002`

<!-- Reason: the index is in the site's language and counts IDs. -->
