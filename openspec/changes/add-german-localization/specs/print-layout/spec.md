## MODIFIED Requirements

<!-- Reason: the footer is in the site's language. -->

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
