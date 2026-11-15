## MODIFIED Requirements

### Requirement: Page shell
Every page but the admin's and the summary's SHALL link, from `/lab/static/site/`, the site's own `tokens.css`, `base.css`, `screen.css` with `media="screen"` and `print.css` with `media="print"`, all collected from `site/assets/css/` of the same checkout, and then `/lab/static/lab.css`. Its `header.site-header` holds the site's shell, read from `site/hugo.toml` and `site/i18n/` of the same checkout: the site title linking to `/`; the site's search form as the site's pages other than the catalogues have it (site-theme "Page shell"); and the navigation, with every entry of the menu, those under `/lab/` included (site-theme "Navigation"). The header also shows the signed-in user's initials and a sign-out button, or a link `Anmelden` (`Sign in`). A message confirming a saved change shows above the content. The item list loads `/lab/static/lab.js` with `defer` (end-product-inventory "Item list"), and no other page does; the admin keeps Django's own pages and scripts. The summary, `/lab/summary/`, links the same five stylesheets and carries no `script` element, but no header, navigation or message; its `base` element sends its links to the top window, and it answers with `X-Frame-Options: SAMEORIGIN`, so that a page of the same host may frame it.

#### Scenario: Shell
- **WHEN** a test client requests `/lab/tasks/` signed in as `KL` and once not signed in
- **THEN** both pages link the five stylesheets in that order, hold the site title, the site's search form and the navigation as site-theme "Navigation" states them for a build with the lab application's views, the first shows `KL` and a sign-out form and the second a link to the sign-in page

#### Scenario: Current link on the application's pages
- **WHEN** a test client requests every page of the application that the menu links, and a page inside the section of each
- **THEN** each page's navigation marks its links as site-theme "Navigation" states

#### Scenario: A summary to frame
- **WHEN** a test client requests `/lab/summary/` and `/lab/tasks/`
- **THEN** the first links the five stylesheets, has a `base` with `target="_top"` and no `header` or `script` element, and answers with `X-Frame-Options: SAMEORIGIN`; the second answers with `X-Frame-Options: DENY`

#### Scenario: lab.js for the item list
- **WHEN** a test client requests the item list, an item's page and `/lab/planning/`
- **THEN** the item list has a `script` element with `src` `/lab/static/lab.js` and `defer`, and the other two load no `lab.js`
