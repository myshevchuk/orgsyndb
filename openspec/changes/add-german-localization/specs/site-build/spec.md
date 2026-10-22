## MODIFIED Requirements

<!-- Reason: the locale is German, and Hugo reads the staged variants
instead of the two source trees. -->

### Requirement: Hugo configuration
The file `site/hugo.toml` SHALL configure Hugo 0.162.1 as follows:
- `baseURL = "/"`, `locale = "de"` and `relativeURLs = true`. The locale is the site's language, as the localization spec defines.
- `buildFuture = true` and `buildExpired = true`, so that no date in front matter decides whether a validated procedure is published.
- `disableKinds` includes `rss` and `sitemap`.
- The taxonomies are exactly `author = "authors"`, `reaction_type = "reaction_types"` and `tag = "tags"`.
- `[permalinks.page]` maps `procedures` to `/procedures/:slug/`.
- `markup.goldmark.renderer.unsafe` is `true`.
- `minify.tdewolff.html.keepWhitespace` is `true`, so that minified HTML keeps a space between adjacent elements that Pagefind would otherwise index as one word.
- `params.siteurl` is `"http://127.0.0.1:8000"`, the default origin of `tools/orgsyndb serve`. The theme prints it as text before a page's path. The environment variable `HUGO_PARAMS_SITEURL` overrides it without editing the file.
- It sets neither `publishDir`, `resourceDir`, `module`, `languages` nor `defaultContentLanguage`.

The configuration names no host other than the loopback address in `params.siteurl`.

`pipeline.hugo_overlay(site, collection, language)` SHALL return the text of the collection's overlay `build/hugo-config/_default/hugo.toml`, which the build passes to Hugo through `--configDir <collection>/build/hugo-config`, given the absolute paths of the application's `site/` and of the collection, and the site's language. It sets `defaultContentLanguage` to the language, `publishDir` to `<collection>/public`, `resourceDir` to `<collection>/build/hugo-resources`, and `module.mounts` to exactly these three mounts, in this order, every path absolute:
1. `<site>/content` → `content`;
2. `<collection>/build/content/procedures` → `content/procedures` with `files = ["/OSDB-*.md"]`;
3. `<collection>/static` → `static`.

Mount 2 holds the procedures the build staged, one per ID, as the localization spec defines. Mount 3 replaces Hugo's default `<site>/static` mount, so the application SHALL have no `site/static/`; its own static files go in `site/assets/`.

#### Scenario: Configuration parses to the contract
- **WHEN** a test loads `site/hugo.toml` with `tomllib`
- **THEN** every value listed above is present as stated, `taxonomies` has exactly the three entries, and none of `publishDir`, `resourceDir`, `module`, `languages` and `defaultContentLanguage` is present
- **AND** the only string value containing `://` or beginning with `//` is `params.siteurl`, equal to `http://127.0.0.1:8000`
- **AND** `site/static/` does not exist

#### Scenario: Overlay parses to the contract
- **WHEN** a test calls `hugo_overlay` with a site path and a collection path that both contain a space and a double quote, and the language `de`, and loads the result with `tomllib`
- **THEN** it has exactly the keys `publishDir`, `resourceDir`, `defaultContentLanguage` and `module`, with the values and the three mounts listed above

<!-- Reason: one page per procedure ID, from the chosen variant. -->

### Requirement: Merged procedures section
A build SHALL publish each procedure ID of the content files of `build/export/` and `md/procedures/` as one page at `public/procedures/<slug>/index.html`, from the variant that the localization spec chooses, whatever its `date`, `publishDate` or `expiryDate`. No other file from those two directories is published.

#### Scenario: Org-sourced and Markdown-sourced pages
- **WHEN** an integration test runs `tools/orgsyndb -C <collection> build` on the seed procedures
- **THEN** `public/procedures/osdb-0001/index.html` (from Org) and `public/procedures/osdb-0002/index.html` (from Markdown) exist
- **AND** the subdirectories of `public/procedures/` are exactly the `slug` values of the published content files

#### Scenario: Future-dated procedure is published, indexed and printed
- **WHEN** an integration test adds to `md/procedures/` a copy of `tests/fixtures/baseline/OSDB-0100-baseline.md` whose `date` and `lastmod` are `2099-01-01T10:00:00+01:00`, and runs `tools/orgsyndb -C <collection> pdf`
- **THEN** it exits 0, `public/procedures/osdb-0100/index.html` exists, `languages.de.page_count` in `public/pagefind/pagefind-entry.json` counts it, and `pdf/OSDB-0100-baseline.pdf` exists

#### Scenario: Expired procedure is still published
- **WHEN** an integration test adds to `md/procedures/` a copy of the same baseline with the line `expiryDate = 2026-02-01T10:00:00+01:00` added to its front matter, and builds
- **THEN** the build exits 0, with the validator's `unknown field` warning for `expiryDate`, and `public/procedures/osdb-0100/index.html` exists

#### Scenario: Stray file and section index are not published
- **WHEN** an integration test adds `md/procedures/notes.txt` and an `md/procedures/_index.md` titled `Hijack`, then builds
- **THEN** the build exits 0, `public/procedures/notes.txt` does not exist, and `public/procedures/index.html` does not contain `Hijack`

<!-- Reason: pages declare the site's language. -->

### Requirement: Minimal layout contract
The layouts SHALL live in `site/layouts/`. Whichever layouts are in place, they meet all of the following:
- On every procedure page, the rendered body is inside exactly one element carrying `data-pagefind-body`.
- No other page carries `data-pagefind-body`.
- The procedure page shows the procedure's `title` and `id`.
- Every HTML page has `<html lang="<language>">` with the site's language, `<meta charset="utf-8">` and a `<title>` element.
- Asset references in layouts are root-relative paths.
- A procedure page's content does not depend on JavaScript.

#### Scenario: One indexed body per procedure page
- **WHEN** an integration test builds the shipped procedures and parses every HTML file under `public/` with `html.parser`
- **THEN** each procedure page of a published content file has exactly one element with `data-pagefind-body`, and that element contains the procedure's `Summary` or `Zusammenfassung` heading
- **AND** no other HTML file has such an element

#### Scenario: Title and ID shown
- **WHEN** the same test reads `procedures/osdb-0002/index.html`
- **THEN** the text outside the indexed body contains the title of the published variant and `OSDB-0002`

<!-- Reason: the index is in the site's language and counts IDs. -->

### Requirement: Search index
`build` SHALL run Pagefind over `public/` after Hugo, writing the bundle to `public/pagefind/`. Only procedure pages are indexed, under the site's language.

#### Scenario: Bundle location and page count
- **WHEN** an integration test builds the seeds
- **THEN** `public/pagefind/pagefind.js`, `public/pagefind/pagefind-ui.js` and `public/pagefind/pagefind-ui.css` exist
- **AND** `public/pagefind/pagefind-entry.json` parses as JSON with `version` equal to `1.5.2`, `languages` holding only the site's language, and its `page_count` equal to the number of published procedures
