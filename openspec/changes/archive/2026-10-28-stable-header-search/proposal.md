## Why

The header search form is present on every page except `/procedures/` and
the term pages, where the catalogue's own field takes its place further
down. Switching between those pages and any other moves the header: the
navigation jumps from the middle of the row to its right end (about 575
CSS pixels at 1280), the row loses 9 pixels of height, and the catalogue's
`h1` is set smaller than every other page's. The search box itself
disappears from the place a reader has learnt to find it.

## What Changes

- Every page's header holds the same search form in the same place. On
  `/procedures/` and the term pages that form is the catalogue's search:
  its field is the catalogue's one search field, which the catalogue
  script drives as before (live results, address, history). The
  catalogue's own `form.catalogue-search` is removed, so each page still
  has exactly one search field.
- On a term page the header field searches within the page's scope, and
  its accessible name and placeholder say so (`Search procedures with
  the tag cinnamate`). The form's action is the page's own URL, so it
  never leaves the scope.
- Everywhere else the field keeps its target, `/procedures/`; its
  placeholder becomes `Product, CAS, SMILES or keyword`, the text that
  says what search matches.
- On screen, the site title and the navigation sit at the start of the
  header row and the search form at its end, and the catalogue's `h1`
  takes the size of every other `h1`, so the header and the heading keep
  their geometry from page to page.

## Capabilities

### Modified Capabilities

- `site-theme`: the page shell's header search on every page and its
  stable layout.
- `site-catalogue`: the catalogue's search form is the header's; the
  page's parts and the controls requirement follow.
- `localization`: the German header and term-page search texts.

## Impact

- `site/layouts/_partials/site-header.html`, `catalogue.html`;
  `site/assets/js/catalogue.js`; `site/assets/css/base.css`,
  `screen.css`, `print.css`; both i18n files.
- Tests: the page shell, catalogue part order and controls checks, the
  German shell and catalogue checks.
- Docs: `README.md` ("Use the site": the header search on every page).
