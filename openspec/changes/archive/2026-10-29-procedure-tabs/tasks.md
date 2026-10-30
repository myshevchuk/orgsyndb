## 1. Tests, red first

- [x] 1.1 Page shell: two navigation links; the current section of the
  taxonomy and term pages is `/procedures/`
- [x] 1.2 Section tabs on the catalogue, taxonomy and term pages, their
  current tab, and no tabs elsewhere
- [x] 1.3 Scope line without the directory link, in both languages
- [x] 1.4 German navigation and tabs; PDF chrome check with the new
  navigation texts

## 2. Implementation

- [x] 2.1 `site-header.html`: two links and the new section rule
- [x] 2.2 `section-tabs.html`, called from `section.html`, `term.html`
  and `taxonomy.html`; the tab strings in both i18n files
- [x] 2.3 `catalogue.html`: the scope line without the directory link
- [x] 2.4 `screen.css`: the tab row and its current tab

## 3. Verification

- [x] 3.1 Full suite: 401 passed and 1 skipped (`caddy`)
- [x] 3.2 Browser: the tabs and the header at 1280 and 500 CSS pixels,
  light and dark. Checked in headless Firefox on the German demo build:
  the tabs sit in one row under the header at 1280 and wrap to two at
  500 with their baselines aligned, the current tab is underlined, the
  header keeps its height, and the dark scheme keeps them legible

## 4. Docs and review

- [x] 4.1 Doc writer: `README.md` and the help pages where they
  describe the navigation
- [x] 4.2 Codex reviewer: no findings; all 17 scenarios implemented
- [x] 4.3 Archive
