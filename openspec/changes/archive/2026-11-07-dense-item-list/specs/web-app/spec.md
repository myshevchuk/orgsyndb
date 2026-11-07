## MODIFIED Requirements

### Requirement: Page shell
Every page but the admin's and the summary's SHALL link, from `/lab/static/site/`, the site's own `tokens.css`, `base.css`, `screen.css` with `media="screen"` and `print.css` with `media="print"`, all collected from `site/assets/css/` of the same checkout, and then `/lab/static/lab.css`. Its `header.site-header` holds the site title linking to `/`, a `nav` labelled as the site's navigation with the application's views, each a link and the path its pages lie under, followed by the site's sections `/compounds/`, `/sequences/`, `/procedures/` and `/help/` under the site's labels. The views are `Bestand` (`Inventory`), linking to `/lab/inventory/end-products/`, its pages under `/lab/inventory/`; `Planung` (`Planning`), linking to `/lab/planning/`, its pages under `/lab/planning/`; and `Aufgaben` (`Tasks`), linking to `/lab/tasks/`, its pages under `/lab/tasks/`. A view's link carries `aria-current="page"` on the page it links to and `aria-current="true"` on every other page under its view's path. The header ends with the signed-in user's initials and a sign-out button, or a link `Anmelden` (`Sign in`). A message confirming a saved change shows above the content. These pages carry no `script` element but the item list, whose one `script` element loads `/lab/static/lab.js` with `defer` (end-product-inventory "Item list"); the admin keeps Django's own pages and scripts. The summary, `/lab/summary/`, links the same five stylesheets and carries no `script` element, but no header, navigation or message; its `base` element sends its links to the top window, and it answers with `X-Frame-Options: SAMEORIGIN`, so that a page of the same host may frame it.

#### Scenario: Shell
- **WHEN** a test client requests `/lab/tasks/` signed in as `KL` and once not signed in
- **THEN** both pages link the five stylesheets in that order, the navigation lists `Bestand` and `Planung` without `aria-current`, `Aufgaben` with `aria-current="page"`, and then the four site sections in that order, the first shows `KL` and a sign-out form and the second a link to the sign-in page, and neither has a `script` element

#### Scenario: Navigation in the inventory
- **WHEN** a test client requests the item list and an item's page
- **THEN** the navigation's `Bestand` link carries `aria-current="page"` on the list and `aria-current="true"` on the item's page, and `Planung` and `Aufgaben` carry neither

#### Scenario: Navigation in the planning list
- **WHEN** a test client requests `/lab/planning/` and `/lab/planning/?all=1`
- **THEN** the navigation's `Planung` link carries `aria-current="page"` on both, and `Bestand` and `Aufgaben` carry neither

#### Scenario: A summary to frame
- **WHEN** a test client requests `/lab/summary/` and `/lab/tasks/`
- **THEN** the first links the five stylesheets, has a `base` with `target="_top"` and no `header` or `script` element, and answers with `X-Frame-Options: SAMEORIGIN`; the second answers with `X-Frame-Options: DENY`

#### Scenario: One script for the item list
- **WHEN** a test client requests the item list, an item's page and `/lab/planning/`
- **THEN** the item list has one `script` element, with `src` `/lab/static/lab.js` and `defer`, and the other two have none
