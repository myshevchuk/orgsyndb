## ADDED Requirements

### Requirement: Scripts
Every page of the application but the admin's SHALL take its scripts from the application's own static files, served under `/lab/static/`. A library is kept in the repository at a fixed version, beside its licence; the application includes htmx so. No `script` element holds code, and no element carries an attribute that holds code: no attribute name begins with `on`, `hx-on` or `data-hx-on`, and a page that loads htmx configures it, through the `meta` element `htmx-config`, with `allowEval` false, so that it evaluates no code it finds in the page. A page may load parts of other pages into itself; whatever it loads, the server also shows in a complete page at a URL of its own, so that a link or a reload shows it.

#### Scenario: Scripts from the application's files
- **WHEN** a test client requests every page of the application that the menu links, a task's page and its edit form, signed in as `KL`, and the sign-in page, not signed in
- **THEN** every `script` element of each page has a `src` beginning with `/lab/static/` and no text, no element carries an attribute whose name begins with `on`, `hx-on` or `data-hx-on`, and the page's `meta` `htmx-config` holds JSON with `allowEval` false

#### Scenario: htmx kept with its licence
- **WHEN** a test looks up htmx among the application's static files
- **THEN** it finds `htmx/htmx.min.js` and the licence beside it

## MODIFIED Requirements

### Requirement: Page shell
Every page but the admin's, the authorization endpoint's error page and the summary's SHALL link, from `/lab/static/site/`, the site's own `tokens.css`, `base.css`, `screen.css` with `media="screen"` and `print.css` with `media="print"`, all collected from `site/assets/css/` of the same checkout, and then `/lab/static/lab.css`, and load htmx and then `/lab/static/lab.js`, both with `defer` (Scripts). Its `header.site-header` holds the site's shell, read from `site/hugo.toml` and `site/i18n/` of the same checkout: the site title linking to `/`; the site's search form as the site's pages other than the catalogues have it (site-theme "Page shell"); and the navigation, with every entry of the menu, those under `/lab/` included (site-theme "Navigation"). The header also shows the signed-in user's initials and a sign-out button, or a link `Anmelden` (`Sign in`). A message confirming a saved change shows above the content. The admin keeps Django's own pages and scripts, and the authorization endpoint (OpenID provider) answers a request it refuses with the OAuth toolkit's own error page. The summary, `/lab/summary/`, links the same five stylesheets, but no header, navigation or message; its `base` element sends its links to the top window, and it answers with `X-Frame-Options: SAMEORIGIN`, so that a page of the same host may frame it.

#### Scenario: Shell
- **WHEN** a test client requests `/lab/tasks/` signed in as `KL` and once not signed in
- **THEN** both pages link the five stylesheets in that order, hold the site title, the site's search form and the navigation as site-theme "Navigation" states them for a build with the lab application's views, the first shows `KL` and a sign-out form and the second a link to the sign-in page

#### Scenario: Current link on the application's pages
- **WHEN** a test client requests every page of the application that the menu links, and a page inside the section of each
- **THEN** each page's navigation marks its links as site-theme "Navigation" states

#### Scenario: A summary to frame
- **WHEN** a test client requests `/lab/summary/` and `/lab/tasks/`
- **THEN** the first links the five stylesheets, has a `base` with `target="_top"` and no `header` element, and answers with `X-Frame-Options: SAMEORIGIN`; the second answers with `X-Frame-Options: DENY`

#### Scenario: Scripts on every page
- **WHEN** a test client requests the item list, an item's page and `/lab/planning/`
- **THEN** each loads `/lab/static/htmx/htmx.min.js` and then `/lab/static/lab.js`, both with `defer`
