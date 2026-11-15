## MODIFIED Requirements

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` holding:
  - `a.site-title`, linking `/` with the text `OrgSynDB`;
  - `form.site-search` with `role="search"` and `method="get"`, holding one `input` with `type="search"` and `name="q"`, and a `button` with `type="submit"` and the text `Search`. On the catalogue, the term pages and `/general-procedures/` it is the catalogue's search form, with the `action`, attributes and texts that site-catalogue "Catalogue controls" gives, and on `/compounds/` and its tab pages it is the compound catalogue's, as site-catalogue "Compound catalogue" and "Compound tabs" give. On every other page its `action` resolves to `/procedures/`, and its input carries `aria-label="Search procedures"` and the placeholder `Product, CAS or SMILES`;
  - the navigation (Navigation), the header's only `nav`;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures · built <time>`, where `<time>` is a `time` element whose `datetime` is the time the site was built, as an RFC 3339 date-time, and whose text is that time as `YYYY-MM-DD HH:MM`. Every page of one build shows the same time.

Every page has exactly one `input` with `name="q"`: the header's.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, the interface string named by the page's `title_key` where it has one, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build in locale `en`
- **THEN** each has the skip link, the site header holding the site title, `form.site-search` and exactly one `nav`, one `main#main`, the footer text with its `time`, the same on every page, both `meta` elements, exactly one `h1`, no heading-level jump greater than one, and exactly one `input[name=q]`, the header's
- **AND** on every page except `/procedures/`, `/general-procedures/`, `/compounds/`, its tab pages and the term pages the form's `action` resolves to `/procedures/` and its input has the stated `aria-label` and placeholder

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build in locale `en`
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

## ADDED Requirements

### Requirement: Navigation
The site's pages and the lab application's pages SHALL show one navigation, defined once, in the menu `main` of `site/hugo.toml`, which alone decides its entries, their order, their grouping and the section each link stands for:
- An entry is a link, with a `url`, or a group, a label whose links name it as their `parent`. Its `identifier` is the key of its text among the interface strings (localization "Interface strings"). Entries are ordered by `weight`. A link may list in `params.paths` the paths of its section: every path that begins with one of them lies in that section.
- The navigation is a `nav` whose `aria-label` is the interface string `nav_site`, listing the entries in order: a link as a link with its text, a group as its label followed by a list of its links.
- Every page of a build shows the same navigation, the site's pages and the application's alike, except that a build without the lab application's views (site-build "Hugo configuration") leaves out every link whose `url` begins with `/lab/`, and every group left without links.
- The link whose `url` is the page's own path carries `aria-current="page"`. Otherwise the link whose section the page lies in carries `aria-current="true"`. No other link of the navigation carries `aria-current`.
- On screen, at a given window width, the site title, the search form and the navigation have the same position and size on every page, the site's and the application's alike, and the page's `main` begins at the same place. Every page's `h1` has the same font size.

#### Scenario: One navigation from the menu
- **WHEN** a test builds a copy of the test collection in locale `en` with the lab application's views, reads the menu `main` of `site/hugo.toml` and the interface strings, and scans every HTML page under `public/` except those under `public/pagefind/`
- **THEN** each page's header holds one `nav` labelled `Site` that lists the menu's entries in order of weight, each group as its label and a list of its links, each entry with its interface string as text, and each link with its `url`

#### Scenario: A build without the lab
- **WHEN** a test builds a copy of the test collection without the lab application's views and scans its pages
- **THEN** each page's `nav` lists the menu's entries less the links under `/lab/` and the groups left empty, and no `href` in any page's header resolves under `/lab/`

#### Scenario: Current link
- **WHEN** a test scans every page of a theme build
- **THEN** on each page the navigation's link to the page's own path, where there is one, carries `aria-current="page"`; otherwise the link whose section the page lies in, where there is one, carries `aria-current="true"`; and no other link carries `aria-current`

#### Scenario: The shell does not move
- **WHEN** the orchestrator measures the site title, the search form, the navigation, the start of `main` and the `h1` of the home page, `/procedures/`, a procedure page, `/compounds/`, `/lab/`, `/lab/registry/` and `/lab/tasks/`, signed in and not, in a browser at 1280 and at 500 CSS pixels (manual verification, tasks.md section 3)
- **THEN** at each width each of them has the same position and size on every page, and the `h1` the same font size
