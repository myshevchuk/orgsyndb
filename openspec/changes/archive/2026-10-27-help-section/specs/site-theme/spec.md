## MODIFIED Requirements

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` with a `nav` element carrying `aria-label="Site"`. The nav links to `/procedures/`, `/reaction_types/`, `/tags/`, `/authors/` and `/help/`, with the texts `Procedures`, `Reaction types`, `Tags`, `Authors` and `Help`. No navigation link leads to `/search/`, the results page of the search forms (site-search spec). The header holds no other `nav`. The link whose URL is the page's own URL carries `aria-current="page"`; otherwise the link of the section the page lies in carries `aria-current="true"`, where `/procedures-by-date/` and every procedure page lie in `/procedures/`, and every term page lies in its taxonomy's page, and every help page lies in `/help/`. No other navigation link carries `aria-current`;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures`.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, the interface string named by the page's `title_key` where it has one, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build in locale `en`
- **THEN** each has the skip link, the site header with the five navigation links, one `main#main`, the footer text, both `meta` elements, exactly one `h1`, and no heading-level jump greater than one

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build in locale `en`
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

#### Scenario: Current section in the navigation
- **WHEN** a test scans the home page, both procedure lists, a procedure page, the tags page, a tag term page, the search page, the help index and a help page after a theme build
- **THEN** the home page marks no navigation link, `/procedures/` marks its own link with `aria-current="page"`, `/procedures-by-date/` and the procedure page mark `/procedures/` with `aria-current="true"`, the tags page marks `/tags/` with `page` and the term page with `true`, the search page marks no navigation link, `/help/` marks its own link with `page`, and the help page `/help/schema/` marks `/help/` with `true`
