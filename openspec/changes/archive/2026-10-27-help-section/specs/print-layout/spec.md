## MODIFIED Requirements

### Requirement: First-page facts
The procedure header SHALL contain a `p.print-facts`, shown only in print, whose text is the page's full URL, then ` · `, the `id`, ` · status `, the `status`, ` · last modified `, and the `lastmod` formatted `YYYY-MM-DD HH:MM`. The full URL is the whole text of a `span.page-url` inside it, built as follows:
- It is Hugo's `site.Params.siteurl` with any trailing `/` removed, followed by the page's path `/procedures/<slug>/`.
- `site/hugo.toml` sets `[params] siteurl = "http://127.0.0.1:8000"`, the default origin of `tools/orgsyndb serve`.
- The environment variable `HUGO_PARAMS_SITEURL` overrides it, for example with an internal host.
- In a browser, the site script replaces the span's text with `location.href` when the protocol is `http:` or `https:`.

The URL is plain text. The `siteurl` value appears in published HTML only as the text of `span.page-url`, never in an attribute. The article of a help page is exempt: its text is a document of `docs/` (site-help spec), which may name the address of `tools/orgsyndb serve` in its text and its links. So `relativeURLs` does not rewrite it, and the site-build "No fetches from other hosts" rules, which concern fetching attributes, `url()` and `@import`, do not apply to it.

#### Scenario: Full URL on the first page by default
- **WHEN** a test reads the first page text of `pdf/OSDB-0002-aspirin.pdf` after a PDF build without `HUGO_PARAMS_SITEURL`
- **THEN** it contains `http://127.0.0.1:8000/procedures/osdb-0002/ · OSDB-0002 · status draft · last modified 2026-10-19 23:50`

#### Scenario: Site URL from the environment
- **WHEN** a PDF build runs with `HUGO_PARAMS_SITEURL=https://orgsyndb.example.invalid/` in the environment
- **THEN** the first page text of `pdf/OSDB-0002-aspirin.pdf` contains `https://orgsyndb.example.invalid/procedures/osdb-0002/`, and does not contain `127.0.0.1`

#### Scenario: The URL is text only
- **WHEN** a test scans every HTML file under `public/` after a theme build, leaving out the `article.help-page` of each help page
- **THEN** every occurrence of `http://127.0.0.1:8000` is inside the text of a `span.page-url`, and each such span's text equals `http://127.0.0.1:8000` followed by its page's path
- **AND** no attribute value contains `127.0.0.1`
