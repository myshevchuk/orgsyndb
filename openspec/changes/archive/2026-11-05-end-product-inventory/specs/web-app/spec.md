## MODIFIED Requirements

### Requirement: Page shell
Every page but the admin's SHALL link, from `/lab/static/site/`, the site's own `tokens.css`, `base.css`, `screen.css` with `media="screen"` and `print.css` with `media="print"`, all collected from `site/assets/css/` of the same checkout, and then `/lab/static/lab.css`. Its `header.site-header` holds the site title linking to `/`, a `nav` labelled as the site's navigation with the site's sections `/procedures/`, `/compounds/`, `/sequences/` and `/help/` under the site's labels, followed by the application's views, each a link and the path its pages lie under: `Bestand` (`Inventory`), linking to `/lab/inventory/end-products/`, its pages under `/lab/inventory/`, and `Aufgaben` (`Tasks`), linking to `/lab/tasks/`, its pages under `/lab/tasks/`. A view's link carries `aria-current="page"` on the page it links to and `aria-current="true"` on every other page under its view's path. The header ends with the signed-in user's initials and a sign-out button, or a link `Anmelden` (`Sign in`). A message confirming a saved change shows above the content. These pages carry no `script` element; the admin keeps Django's own pages and scripts.

#### Scenario: Shell
- **WHEN** a test client requests `/lab/tasks/` signed in as `KL` and once not signed in
- **THEN** both pages link the five stylesheets in that order, the navigation lists the four site sections, `Bestand` without `aria-current` and `Aufgaben` with `aria-current="page"`, the first shows `KL` and a sign-out form and the second a link to the sign-in page, and neither has a `script` element

#### Scenario: Navigation in the inventory
- **WHEN** a test client requests the item list and an item's page
- **THEN** the navigation's `Bestand` link carries `aria-current="page"` on the list and `aria-current="true"` on the item's page, and `Aufgaben` carries neither
