## Why

The sidebar takes 17rem of every page, and on narrow windows the
stacked header pushes the content down by the whole menu. The owner
wants it collapsible. A collapse that persists across pages, and
holds before the first paint so that nothing jumps, needs a script
in the page shell of both the site and the lab application, and
three specs forbid exactly that: site-theme lists the only things
scripts may add, web-app allows no `script` element on the
application's pages but the item list's, and lab-overview none on the
overview. The owner decided that the collapse itself needs no spec,
and that spec points standing in its way are dropped rather than
reworded to describe it.

## What Changes

- A toggle before the site title collapses the sidebar to a rail
  holding only the toggle, and on narrow windows hides the search
  form and the menu, leaving the title's row. The state is kept in the
  browser's local storage, so it holds on every page of the host, the
  site's and the application's alike; without JavaScript the toggle is
  not shown and the sidebar stays open.
- `site.js` moves into the head without `defer`, marks the root
  element with the stored state before the first paint, and wires the
  toggle once the page is parsed. The application's pages load the
  same `site.js`, collected from `site/assets/js/`, except the framed
  summary, which keeps no script.
- Specs drop the points that forbid this: site-theme's closed list of
  what scripts add, web-app's ban on `script` elements beyond the item
  list's, and lab-overview's on the overview page. Nothing is added
  about the collapse.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-theme`: "Content does not need JavaScript" no longer closes
  the list of what scripts add.
- `web-app`: "Page shell" no longer forbids `script` elements; the
  item list still loads `lab.js`, and no other page does.
- `lab-overview`: "Overview page" allows the page shell's script.

## Impact

- `site/layouts/baseof.html`, `site/layouts/_partials/site-header.html`,
  `site/assets/js/site.js`, `site/assets/css/screen.css`,
  `site/i18n/` (the toggle's text).
- `webapp/orgsyndb_web/templates/orgsyndb_web/base.html`, the summary
  template, `context_processors.py`, `settings.py`
  (`STATICFILES_DIRS`).
- `deploy/webapp/Dockerfile` and its ignore file copy
  `site/assets/js/`.
- Tests that assert no `script` element on the application's pages.
