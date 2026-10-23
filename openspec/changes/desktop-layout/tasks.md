## Implementation

- [x] Widen the screen shell and improve desktop navigation spacing.
- [x] Arrange the home list and browse tools in columns.
- [x] Arrange procedure details and body in columns with readable prose.
- [x] Keep tables scrollable within their available column.
- [x] Preserve source order, localization and print flow.
- [x] Update the existing HTML order assertion and README.
- [x] Prepare three visual design concepts with real demo content.

## Chosen layouts

- [x] Lists: implement layout 4 (count, search, filters, sort bar, table).
- [x] Add list-filter.js with a Node-tested matching function.
- [x] Procedures: implement layout 7 Marginalia (body left, margin right).
- [x] Use sans-serif on screen; keep print unchanged.
- [x] Mark the current page and section in the navigation.
- [x] Add the list-tools, navigation and filter tests; update the spec.

## Validation

- [x] Build the German demo: 28 files, no errors or warnings.
- [x] Run all tests: 330 passed, 1 optional Caddy skip; 3,971 subtests passed.
- [x] Check whitespace and inspect static desktop renders.
- [x] Verify live browser layouts at 1280, 1440 and 1920 CSS pixels in
  both color schemes: Chromium (Playwright) screenshots of the German demo
  list and procedure pages, no horizontal overflow, no script errors, and
  the filters tested by selecting values.
