## Why

The lab application's views, `Bestand`, `Planung` and `Aufgaben`, show
in the navigation only on pages under `/lab/`: the static site's header
links its four sections and nothing else, so from the site's own pages
the lab can be reached only by typing its address. The owner also
wants one order in both headers: `Bestand`, `Planung`, `Aufgaben`,
`Verbindungen`, `Synthesewege`, `Vorschriften`, `Hilfe`.

## What Changes

- The static site's header links the lab application's views first,
  on a site built for a deployment that runs the application.
- `tools/orgsyndb build` reads `ORGSYNDB_LAB`: `true` builds the site
  with those links; unset or `false` without them, as for the demo site
  on GitHub Pages, which has no application behind it. Any other value
  stops the build.
- `deploy/compose.yaml` sets `ORGSYNDB_LAB=true` for the builder, since
  every container deployment runs the application.
- Both headers list the site's sections as `Verbindungen`,
  `Synthesewege`, `Vorschriften`, `Hilfe` (`Compounds`, `Sequences`,
  `Procedures`, `Help`), after the lab's views where they show.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-theme`: the header's navigation order and the lab's views.
- `localization`: the German navigation in its new order.
- `site-build`: the overlay's `params.lab`.
- `build-script`: `build` reads `ORGSYNDB_LAB`.
- `container-deployment`: the builder sets `ORGSYNDB_LAB=true`.
- `web-app`: the page shell lists the views before the site's sections.

## Impact

- `site/layouts/_partials/site-header.html`, `site/i18n/de.toml` and
  `en.toml`, `tools/pipeline.py` (`hugo_overlay`), `tools/orgsyndb`,
  `deploy/compose.yaml`, `webapp/orgsyndb_web/context_processors.py`.
- Tests: the theme, localization, overlay, build and Compose tests at
  the root, and the shell tests of the application.
- Docs: `README.md` where it names the navigation or the build's
  environment.
- Existing deployments rebuild the site on their next cycle once the
  application is updated; nothing else changes for them.
