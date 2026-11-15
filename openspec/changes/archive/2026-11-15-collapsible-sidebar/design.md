## Context

The shell is a sidebar on wide windows and a stacked header below
55rem, the same markup on the site's pages and the application's. The
site loads `site.js` with `defer` at the end of `body`; the
application's pages load no script but the item list's `lab.js`. Both
live on one host, so they share the browser's local storage.

## Goals / Non-Goals

**Goals:** one toggle, at the same place on every page, whose state
holds across pages and applies before the first paint; nothing moves
without JavaScript or before the state applies.

**Non-Goals:** a spec for the collapse; a server-side state (the
static site could not read it); collapsing by default on phones.

## Decisions

**The state lives on the root element.** `site.js` sets
`data-sidebar` to `collapsed` or `expanded` from local storage before
the body is parsed, and the stylesheet keys every collapsed rule and
the toggle's visibility on it. A toggle marked `hidden` and revealed at
`DOMContentLoaded` would appear late and shift the title; keying on
the root shows it from the first paint, and without JavaScript the
attribute is missing, so the toggle stays hidden and the sidebar open.

**`site.js` loads in the head without `defer`.** The state must apply
before the first paint, and site-theme allows no inline script. The
rest of `site.js` runs at `DOMContentLoaded`. One script for both
sides, rather than a second file, keeps the compound pages and the
catalogue's script wiring as they are.

**The application collects `site/assets/js/` under `site/`.** It is
served as `/lab/static/site/site.js` beside the stylesheets; the
catalogue's scripts come along unused. The framed summary leaves the
script out, as it has no header.

**The toggle sits before the title, with the title in a wrapper.** It
then stays under the pointer when the sidebar collapses on a wide
window, where the rail keeps only it, and in the title's row on a
narrow one, where the search form and the menu hide. Its text, the
interface string `nav_toggle`, is kept for assistive technology and
the button shows a menu icon; `aria-expanded` gives the state.

## Risks / Trade-offs

- A blocking script in the head delays the first paint by one small,
  cached request → the script is minified and fingerprinted on the
  site, and served by WhiteNoise in the application.
- Local storage is per host: a site and an application on different
  hosts would keep separate states → both are served on one host in
  every deployment.
