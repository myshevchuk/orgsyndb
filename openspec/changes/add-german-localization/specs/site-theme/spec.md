## MODIFIED Requirements

<!-- Reason: the shell is in the page's language and may carry a language
switch. -->

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` with a `nav` element carrying `aria-label="Site"`. The nav links to `/procedures/`, `/reaction_types/`, `/tags/`, `/authors/` and `/search/`, with the texts `Procedures`, `Reaction types`, `Tags`, `Authors` and `Search`. When the page has a translation, the header also holds the language switch of the localization spec after this nav;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures`.

These texts and paths are those of English pages; a German page has the German texts and the `/de/` paths that the localization spec gives.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every English HTML file under `public/` except files under `public/pagefind/`, after a theme build
- **THEN** each has the skip link, the site header with the five navigation links, one `main#main`, the footer text, both `meta` elements, exactly one `h1`, and no heading-level jump greater than one

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`
