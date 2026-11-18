## Context

The application's pages share one template, `base.html`, which loads
the site's `site.js` in the head without `defer`; the item list adds
`lab.js` with `defer` through its own `head` block, and the framed
summary empties the script block. `lab.js` wires the item list's
popups, its submitting choices and its remembered view controls, each
with a query that finds nothing on other pages. Static files are
served by WhiteNoise from `webapp/orgsyndb_web/static/` and the
site's collected assets. No page loads anything from another host,
and the deployment runs on an internal network.

## Goals / Non-Goals

**Goals:** one copy of htmx that every page of the shell loads, and
`lab.js` beside it, so that the next changes can load parts of pages
and submit forms in dialogs; specs that permit this and keep only the
rules that guard security and operation.

**Non-Goals:** any use of htmx in this change; the CSRF header that
htmx's posts will need, which comes with the first form in a dialog;
a `Content-Security-Policy` header; changes to the site's code.

## Decisions

**htmx 2.0.11, bundled.** The npm registry's `latest` is 2.0.11;
4.0 is published under `next` and is not taken. The minified file
and its licence (0BSD) are placed in
`webapp/orgsyndb_web/static/htmx/`, taken from the registry's tarball
after checking the tarball against the registry's `integrity` hash.
The file's own `version` field records the version; an update
replaces both files. No `django-htmx`: telling an htmx request apart
is one header check, and Django 6.0's template partials render the
parts a request asks for.

**Configured by a `meta` element, not a script.** `base.html` carries
`<meta name="htmx-config">` with `allowEval` false, so that htmx runs
no code from `hx-on`, `js:` values or event filters in `hx-trigger`,
and `includeIndicatorStyles` false, so that it injects no `style`
element; indicators, once used, are styled in `lab.css`. Behaviour
that would sit in such attributes goes into `lab.js` as listeners.
Together with local files and no inline code, this leaves a later
`script-src 'self'` policy possible.

**Loaded in the shell, deferred, htmx first.** The block that holds
`site.js` in `base.html` also loads htmx and then `lab.js`, both with
`defer`, so `lab.js` runs after htmx and can use its API. The item
list drops its own `lab.js`. The summary keeps emptying the block: it
is framed and has nothing to enhance.

**`lab.js` on every page.** Its listeners find nothing to wire on
pages without popups, `data-submit` or `data-remember`. Wiring
content that htmx swaps in later is left to the change that first
swaps content.

**The site keeps its fallbacks.** Lifting "Content does not need
JavaScript" drops a requirement, not code: the hidden print and copy
buttons, the catalogue's `noscript` note and its hidden controls stay
as site-catalogue and site-theme "Procedure page structure" describe
them. The tests that scanned for the lifted rule as such go.

## Risks / Trade-offs

- htmx adds about 50 kB, 16 kB compressed, to the first page a
  browser loads → WhiteNoise serves it compressed, and the browser
  caches it across pages.
- `allowEval` false removes htmx's event filters and `hx-on` → the few
  listeners that need them live in `lab.js`, which keeps the behaviour
  in one place.
- A bundled library ages unnoticed → its version sits in the file and
  in this design; updating is replacing two files.
