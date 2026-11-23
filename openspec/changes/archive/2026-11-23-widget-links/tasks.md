## 1. Tests

- [x] 1.1 Back links on the seven record pages, in German and English:
  one `p.lab-back` after the demo note and before the `h1`, target,
  text equal to the list's `h1`, arrow hidden, and exactly one link to
  the list outside the navigation and section tabs.
- [x] 1.2 Overview: `#<id>` for a note without a number, `Alle →` link.
- [x] 1.3 Summary: no link to `/lab/` itself; existing summary tests
  updated.
- [x] 1.4 Site: the notebook value links `/lab/journal/<code>/`; the
  prefix and root link tests accept notebook pages of the registry.

## 2. Implementation

- [x] 2.1 Back-link partial and the seven pages; the notebook page's
  plain link replaced; `.lab-back` style.
- [x] 2.2 Overview and summary templates.
- [x] 2.3 `procedure-meta.html` notebook link.

## 3. Verification

- [x] 3.1 Browser: back links on each page, light and dark; the home
  page's lab box at 1440 and 390 px.
- [x] 3.2 Owner checks the links on the test server.
