## Context

The static site is built by `tools/orgsyndb build`, alone for the demo
on GitHub Pages and through `orgsyndb-deploy` in the container
deployment, where Caddy forwards `/lab/` to the Django application. The
site cannot tell at build time whether an application will answer under
`/lab/`; only the deployment knows.

## Decisions

### A build switch, set by the deployment

`ORGSYNDB_LAB` decides whether the header links the lab's views. The
Compose file sets it for the builder, next to the `app` service it
refers to; the demo build leaves it unset and keeps a header without
dead links. The build passes it to Hugo as `params.lab` through the
overlay it already writes, so `site/hugo.toml` stays the same for every
deployment.

Rejected:
- Always linking the lab: the demo site and a local preview would link
  pages that do not exist.
- Hugo's own `HUGO_PARAMS_LAB`: its values are strings, so `false`
  would count as set, and the deployment would name a Hugo setting
  rather than the application's.
- Finding the application from the browser: the header would change
  after the page loads, and the site's pages must work without scripts.

### One order in both headers

The views come first because they are where daily work happens; the
site's sections follow in the owner's order. The application's header
keeps its labels from its own translations and the site's sections from
the site's strings, as before.

## Risks / Trade-offs

- Seven links make the header wider. The gaps between the links and
  before the search form shrink to `--space-3` and `--space-4`, so that
  at 1280 CSS pixels the row still holds the search field with its whole
  German placeholder; at 1024 the search form wraps to a second row,
  the same on every page.
