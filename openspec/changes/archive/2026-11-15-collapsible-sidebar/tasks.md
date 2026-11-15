## 1. Tests

- [x] 1.1 Application: no `script` element beyond the shell's on the
  shell, overview and planning pages; `lab.js` on the item list only;
  the summary without a script
- [x] 1.2 Site: the toggle and `site.js` in the head on every page

## 2. Implementation

- [x] 2.1 `site.js`: the sidebar's state on the root element, the
  toggle, the rest at `DOMContentLoaded`; loaded in the head
- [x] 2.2 The toggle in the site's header partial and the
  application's `base.html`, its text `nav_toggle` in `site/i18n/`
- [x] 2.3 Collapsed and toggle styles in `screen.css`
- [x] 2.4 The application collects `site/assets/js/`; the summary
  leaves the script out; Dockerfile and its ignore file

## 3. Verification

- [x] 3.1 In a browser at 1280, 800, 375, 360 and 320 CSS pixels, signed in
  and not: the toggle collapses and expands on the site's and the
  application's pages, the state holds across pages, nothing moves
  on load, and without JavaScript the toggle is hidden
- [ ] 3.2 Run the stack on the test server

## 4. Review and archive

- [x] 4.1 Codex reviewer
- [x] 4.2 Archive and squash-merge into `develop`
