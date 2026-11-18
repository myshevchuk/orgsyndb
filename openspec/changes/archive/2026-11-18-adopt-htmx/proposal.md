## Why

The lab's edit and submit forms are to move into native dialogs that
htmx loads and submits, and the item list is to show an item's
details beside the table, loaded in place. The specs still limit
scripts as they did when the site was meant to be a static publication
that works anywhere: web-app lets only the item list load `lab.js`,
site-theme admits no library apart from Pagefind and requires every
site page to show its content without JavaScript, site-build requires
the same of procedure pages, and the framed summary may carry no
script. The owner decided on 2026-11-18 that these limits go. What
stays is what guards security and operation: scripts are the
project's own files, never fetched from another host; the HTML holds
no code; and every view keeps a URL of its own that renders a whole
page.

## What Changes

- web-app gains a requirement "Scripts" for the application's pages:
  scripts come from the application's own static files; a library is
  kept in the repository at a fixed version beside its licence, and the
  application includes htmx so; no `script` element and no attribute
  holds code, `on…` and `hx-on…` attributes included, and htmx is set
  to evaluate none; whatever a page loads into itself, the server also
  shows in a complete page at a URL of its own.
- web-app "Page shell": every page of the shell loads htmx and then
  `lab.js`, both deferred, instead of the item list alone; the
  summary's ban on `script` elements goes. The OpenID authorization
  endpoint's error page, the OAuth toolkit's own, is named beside
  the admin's as a page outside the shell, which it always was.
- lab-overview "Overview page": the ban on scripts beyond the
  shell's goes.
- site-theme "Theme sources and constraints": the ban on libraries
  goes; a script library is kept like the application's. Scripts stay
  local files, and no attribute name begins with `on`.
- site-theme "Content does not need JavaScript" becomes "Site scripts":
  it keeps what `site.js` and the catalogue script do, and drops the
  rule that every page shows its content without them, with the
  scenario that scans pages for it.
- site-theme "Home page": its scenario no longer bars the lab's
  section from adding a script.
- site-build "Minimal layout contract": the point that a procedure
  page's content does not depend on JavaScript goes.
- Code: htmx 2 is bundled under the application's static files with
  its licence, configured to evaluate no code and to inject no styles,
  and loaded with `lab.js` on every page of the shell. The site's code
  is unchanged; its existing fallbacks for a browser without
  JavaScript stay, no longer required.

The item list's own statements about `lab.js` and about working
without it stay until the change that adds the detail pane rewrites
that requirement.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-app`: new requirement "Scripts"; "Page shell" loads htmx and
  `lab.js` on every page, drops the summary's ban on scripts, and
  names the authorization endpoint's error page outside the shell.
- `site-theme`: "Theme sources and constraints" allows script
  libraries; "Content does not need JavaScript" is renamed "Site
  scripts" and keeps only what the scripts do; "Home page" drops its
  ban on a script for the lab's section.
- `site-build`: "Minimal layout contract" drops its point on
  JavaScript.
- `lab-overview`: "Overview page" drops its ban on scripts beyond the
  shell's.
- `lab-registry`: "Registry pages" names the renamed site-theme
  requirement for the copy button.

## Impact

- `webapp/orgsyndb_web/static/htmx/` (new: `htmx.min.js` and its
  licence), `webapp/orgsyndb_web/templates/orgsyndb_web/base.html`,
  `webapp/inventory/templates/inventory/item_list.html`,
  `webapp/orgsyndb_web/static/lab.js` (its header comment).
- Tests: `webapp/tests/test_shell.py` and the helpers in
  `webapp/tests/__init__.py`, which assert no script beyond the
  shell's and `lab.js` on the item list alone; the site's theme tests
  that scan for content without JavaScript.
- `README.md`, where it states which pages load which scripts.
- No new Python dependency; the deployment collects the new static
  files as it does `lab.js`.
