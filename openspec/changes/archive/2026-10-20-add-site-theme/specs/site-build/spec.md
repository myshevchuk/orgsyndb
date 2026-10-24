## MODIFIED Requirements

<!-- Reasons. "Hugo configuration": Hugo's HTML minifier removes the
whitespace between adjacent block elements such as </dt><dd> and </th><th>.
Pagefind then indexes a label and its value as one word
(cas50782smilesccooc1ccccc1coo, verified with Hugo 0.162.1 and Pagefind
1.5.2), and searching a CAS number or a product name fails.
keepWhitespace keeps one space there; add-site-theme design.md D6. Brief
§6.3 requires the full URL on the first printed page, so params.siteurl
defaults to the loopback origin of serve, and the "names no host" rule
allows exactly that value (design.md D11). The requirement "No fetches
from other hosts" is not modified: the printed URL is text, which its
rules do not cover.
"Minimal layout contract": the guarantees are unchanged. The first
scenario named OSDB-0001 and OSDB-0002 as the only pages with an indexed
body; add-site-theme ships six more procedures, each with an indexed body,
so the scenario now covers every procedure page. -->

### Requirement: Hugo configuration
The file `site/hugo.toml` SHALL configure Hugo 0.162.1 as follows:
- `baseURL = "/"`, `locale = "en"`, `publishDir = "../public"` and `relativeURLs = true`.
- `buildFuture = true` and `buildExpired = true`, so that no date in front matter decides whether a validated procedure is published.
- `disableKinds` includes `rss` and `sitemap`.
- The taxonomies are exactly `author = "authors"`, `reaction_type = "reaction_types"` and `tag = "tags"`.
- `[permalinks.page]` maps `procedures` to `/procedures/:slug/`.
- `markup.goldmark.renderer.unsafe` is `true`.
- `minify.tdewolff.html.keepWhitespace` is `true`, so that minified HTML keeps a space between adjacent elements that Pagefind would otherwise index as one word.
- `params.siteurl` is `"http://127.0.0.1:8000"`, the default origin of `tools/orgsyndb serve`. The theme prints it as text before a page's path. The environment variable `HUGO_PARAMS_SITEURL` overrides it without editing the file.
- `module.mounts` is exactly these three mounts, in this order:
  1. `content` → `content`;
  2. `../build/export` → `content/procedures` with `files = ["/OSDB-*.md"]`;
  3. `../md/procedures` → `content/procedures` with `files = ["/OSDB-*.md"]`.

The configuration names no host other than the loopback address in `params.siteurl`.

#### Scenario: Configuration parses to the contract
- **WHEN** a test loads `site/hugo.toml` with `tomllib`
- **THEN** every value listed above is present as stated, `taxonomies` has exactly the three entries, and `module.mounts` equals the three listed mounts
- **AND** the only string value containing `://` or beginning with `//` is `params.siteurl`, equal to `http://127.0.0.1:8000`

### Requirement: Minimal layout contract
The layouts SHALL live in `site/layouts/`. Whichever layouts are in place, they meet all of the following:
- On every procedure page, the rendered body is inside exactly one element carrying `data-pagefind-body`.
- No other page carries `data-pagefind-body`.
- The procedure page shows the procedure's `title` and `id`.
- Every HTML page has `<html lang="en">`, `<meta charset="utf-8">` and a `<title>` element.
- Asset references in layouts are root-relative paths.
- A procedure page's content does not depend on JavaScript.

#### Scenario: One indexed body per procedure page
- **WHEN** an integration test builds the shipped procedures and parses every HTML file under `public/` with `html.parser`
- **THEN** each `procedures/<slug>/index.html` whose slug is that of a content file in `build/export/` or `md/procedures/` has exactly one element with `data-pagefind-body`, and that element contains the procedure's `Summary` heading
- **AND** no other HTML file has such an element

#### Scenario: Title and ID shown
- **WHEN** the same test reads `procedures/osdb-0002/index.html`
- **THEN** the text outside the indexed body contains the seed's title and `OSDB-0002`
