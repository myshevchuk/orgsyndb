## Why

The site's navigation ends in a Search link, but the search page is not
a separate feature: the search forms of the home page and of the two
procedure lists submit to `/search/?q=…`, and that page runs the one
Pagefind search for all three. A reader who types into any of the three
boxes gets the same results page with the same filters, so the
navigation link adds nothing the forms do not already give.

The application's guides, schema reference, German style guide and
German glossary live in `docs/` and reach only readers of the
repository. People who use the site, many of whom also write
procedures, have no way to read them there.

## What Changes

- The navigation's last link becomes **Help** (`/help/`) in place of
  **Search** (`/search/`). `/search/` stays as the results page of the
  home-page and procedure-list search forms, unchanged; no link in the
  navigation leads to it any more.
- New section `/help/`: `build` stages every `.md` and `.org` document
  directly in the application's `docs/` into
  `build/content/help/`, and Hugo publishes each as a page under
  `/help/<slug>/`. Both languages are published whatever the site's
  language, because the documents link to each other across languages
  and the German style guide and glossary have no English versions.
- Staging takes each document's title from its first line (`# Title`
  or `#+TITLE:`), records its group (glossaries for names starting with
  `GLOSSARY`, guides otherwise), base name and language in front
  matter, and rewrites its links: a link to another document in `docs/`
  becomes a link to that help page, keeping any fragment; a link to any
  other relative path (a template, a demo procedure) becomes its link
  text, since those files are not published.
- `/help/` lists the guides and the glossaries, one entry per document
  with its title in the site's language where a version exists, and
  links to its versions in other languages.
- Code blocks are highlighted with CSS classes instead of inline
  colours (`markup.highlight.noClasses = false`), and the base
  stylesheet styles `pre`, so that the guides' examples follow the
  theme in light and dark mode.

## Capabilities

### New Capabilities

- `site-help`: staging of `docs/` into help pages, link rewriting, the
  help index and the help page layout.

### Modified Capabilities

- `site-theme`: the navigation links `/help/` instead of `/search/`.
- `site-build`: the overlay's fourth mount for the staged help pages,
  and the highlight setting.
- `localization`: the navigation string `Hilfe` replaces `Suche`, and
  `Hilfe` joins the page titles.
- `print-layout`: a help page's article may name the `serve` address,
  which the guides give in their text.
- `build-script`: the pipeline module exposes the help functions and
  reads the Org documents of `docs/`.

## Impact

- `tools/pipeline.py` (`help_page`, `stage_help`, `hugo_overlay`),
  `tools/orgsyndb` (`run_build`).
- `site/hugo.toml`, `site/content/help/_index.md`,
  `site/layouts/help/`, `site/layouts/_partials/site-header.html`,
  `site/i18n/*.toml`, `site/assets/css/base.css`, `screen.css`.
- Tests: new unit tests for staging and link rewriting, integration
  tests for the help section; the navigation, overlay and German title
  tests change; the test sandbox copies `docs/`.
- Docs: `README.md` ("Use the site" lists `/help/`, and describes
  `/search/` as the results page of the search forms).
