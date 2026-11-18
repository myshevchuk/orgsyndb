## 1. Tests

- [x] 1.1 Scripts: on every page the menu links, a task's page and
  its edit form signed in, and the sign-in page signed out, every
  `script` has a `src` under `/lab/static/` and no text, no attribute
  name begins with `on`, `hx-on` or `data-hx-on`, and `htmx-config`
  sets `allowEval` false
- [x] 1.2 htmx and its licence found among the static files
- [x] 1.3 Page shell: htmx then `lab.js`, both deferred, on the item
  list, an item's page and `/lab/planning/`; the summary scenario
  without its script assertion
- [x] 1.4 Remove the tests of lifted rules: no script beyond the
  shell's, on the overview and elsewhere, `lab.js` on the item list
  alone, and the site's scan for content without JavaScript

## 2. Implementation

- [x] 2.1 Bundle htmx 2.0.11 and its licence under
  `webapp/orgsyndb_web/static/htmx/`, checked against the registry's
  integrity hash
- [x] 2.2 `base.html`: the `htmx-config` meta; htmx and `lab.js` in
  the script block with `defer`; the item list drops its own `lab.js`
- [x] 2.3 `lab.js`: its header comment for every page
- [x] 2.4 `README.md`: the statements on which pages load which
  scripts (none became false: the summary still loads none, and the
  item list's script still does what the README says)

## 3. Verification

- [x] 3.1 Both suites pass
- [ ] 3.2 On the test server, the item list, an item's page and a form
  load htmx and `lab.js` without errors in the browser's console

## 4. Review and archive

- [x] 4.1 Codex reviewer
- [x] 4.2 Archive and squash-merge into `develop`
