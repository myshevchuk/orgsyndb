## Why

The menu is written twice: the site's header partial lists three lab
views and the application's context processor four, and the specs
list each copy. The two have drifted, so `Substanzen` shows on lab
pages and vanishes on the site's. The lab overview, the lab notebooks
and the collection imports have no menu entry at all; the notebooks
and imports are reached only through a line of links on the registry
page. The site's header ends in a search form and the application's in
the account, so the header changes height and everything below it
shifts when moving between the two.

The owner wants the menu at the left of the page, and wants specs that
state general design rules rather than layout or individual menu
items, which they add and remove at will.

## What Changes

- One menu, `main` in `site/hugo.toml`, with its texts in
  `site/i18n/`. The site renders it with Hugo; the application reads
  the same two files and renders the same markup. Its entries are
  grouped: the lab (overview, inventory, planning, tasks, substances,
  lab notebooks, imports), the collection (compounds, sequences,
  procedures), and help.
- On screen the shell becomes a sidebar: the site title, the search
  form, the menu and, on the application's pages, the account. Narrow
  windows stack it above the content. The application's pages gain
  the site's procedure search, so both shells are the same. The search
  hints shorten to fit the sidebar: `Product, CAS or SMILES`,
  `Name, formula, CAS, SMILES`, and in German also
  `In diesen Vorschriften` for a scoped catalogue.
- The registry page drops its links to the lab notebooks and imports,
  and those two pages drop their link back to the substances.
- Specs: the lists of menu items, the header-row layout and the table
  of sections leave site-theme, web-app, localization, site-build,
  build-script, site-catalogue and general-procedures. A new
  site-theme requirement "Navigation" states the rules that remain:
  one menu defined once, the same on every page, the current link
  marked, nothing under `/lab/` without the lab, and a shell that does
  not move between pages.
- The application's image copies `site/hugo.toml` and `site/i18n/`
  besides the stylesheets.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-theme`: "Page shell" loses the menu items, the section table
  and the header layout; new "Navigation".
- `web-app`: "Page shell" takes the site's shell, search included,
  from the menu; "Interface language" takes the navigation's texts
  from the site's strings.
- `localization`: "Interface strings" names no menu items; the
  shorter German hints.
- `site-build`: "Hugo configuration" and "Deployment under a path
  prefix" name no lab paths.
- `build-script`: the lab-views scenario names no menu item.
- `site-catalogue`: no section membership for the navigation; the
  shorter hints in "Catalogue controls", "Compound catalogue" and
  "Compound tabs".
- `general-procedures`: no section membership for the navigation.
- `lab-registry`: "Registry pages" drops the links to the notebooks
  and imports.
- `container-deployment`: "Application image" copies the menu and the
  strings.

## Impact

- Site: `site/hugo.toml` (menu), `site/i18n/de.toml` and `en.toml`
  (new menu strings), `site/layouts/_partials/site-header.html`,
  `site/assets/css/base.css` and `screen.css`.
- Application: `webapp/orgsyndb_web/` (navigation from the menu,
  `base.html`, `lab.css`), the registry, journal and imports
  templates, translations.
- Deployment: `deploy/webapp/Dockerfile` and its ignore file.
- Tests: the site's shell, localization, build and prefix tests; the
  application's shell and registry tests.
- Docs: README, `docs/AUTHORING.md` and `docs/AUTHORING-ORG.de.org`
  where they describe the navigation and the header.
