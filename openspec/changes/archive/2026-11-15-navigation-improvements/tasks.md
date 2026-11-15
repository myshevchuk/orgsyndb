## 1. Tests

- [x] 1.1 Site: shell on every page, one navigation from the menu, a
  build without the lab, the current link on every page; drop the
  tests of the old item lists and section table
- [x] 1.2 Localization: menu strings in both languages, the German
  shell; build-script and prefix scenarios without lab paths
- [x] 1.3 Application: shell from the menu with the site's search, the
  current link on every linked page and inside each section, English
  texts from the site's strings; the registry page without the
  notebook and import links
- [x] 1.4 Image: the Dockerfile copies the menu and the strings

## 2. Implementation

- [x] 2.1 Menu `main` in `site/hugo.toml`, its strings in `site/i18n/`
- [x] 2.2 Site header partial rendering the menu
- [x] 2.3 Application: navigation and search from the site's files,
  `base.html`, registry, journal and imports templates, translations
- [x] 2.4 Sidebar layout in `base.css` and `screen.css`, `lab.css`
- [x] 2.5 Dockerfile and its ignore file

## 3. Verification

- [x] 3.1 Measure the shell on site and lab pages at 1280 and 500 CSS
  pixels, signed in and not, light and dark (site-theme "The shell
  does not move")
- [x] 3.2 Run the stack on the test server

## 4. Docs and archive

- [x] 4.1 README and the four authoring guides (`docs/AUTHORING*`)
  through the doc writer
- [x] 4.2 Review, then archive
