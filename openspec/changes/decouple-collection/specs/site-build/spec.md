## MODIFIED Requirements

<!-- Reason: the procedures and the build output now belong to a
collection outside the application (design.md D3, D4). The mounts and the
publish directory therefore move out of site/hugo.toml into an overlay
that the build generates per collection. -->

### Requirement: Hugo configuration
The file `site/hugo.toml` SHALL configure Hugo 0.162.1 as follows:
- `baseURL = "/"`, `locale = "en"` and `relativeURLs = true`.
- `buildFuture = true` and `buildExpired = true`, so that no date in front matter decides whether a validated procedure is published.
- `disableKinds` includes `rss` and `sitemap`.
- The taxonomies are exactly `author = "authors"`, `reaction_type = "reaction_types"` and `tag = "tags"`.
- `[permalinks.page]` maps `procedures` to `/procedures/:slug/`.
- `markup.goldmark.renderer.unsafe` is `true`.
- `minify.tdewolff.html.keepWhitespace` is `true`, so that minified HTML keeps a space between adjacent elements that Pagefind would otherwise index as one word.
- `params.siteurl` is `"http://127.0.0.1:8000"`, the default origin of `tools/orgsyndb serve`. The theme prints it as text before a page's path. The environment variable `HUGO_PARAMS_SITEURL` overrides it without editing the file.
- It sets neither `publishDir`, `resourceDir` nor `module`.

The configuration names no host other than the loopback address in `params.siteurl`.

`pipeline.hugo_overlay(site, collection)` SHALL return the text of the collection's overlay `build/hugo-config/_default/hugo.toml`, which the build passes to Hugo through `--configDir <collection>/build/hugo-config`, given the absolute paths of the application's `site/` and of the collection. It sets `publishDir` to `<collection>/public`, `resourceDir` to `<collection>/build/hugo-resources`, and `module.mounts` to exactly these four mounts, in this order, every path absolute:
1. `<site>/content` → `content`;
2. `<collection>/build/export` → `content/procedures` with `files = ["/OSDB-*.md"]`;
3. `<collection>/md/procedures` → `content/procedures` with `files = ["/OSDB-*.md"]`;
4. `<collection>/static` → `static`.

Mount 4 replaces Hugo's default `<site>/static` mount, so the application SHALL have no `site/static/`; its own static files go in `site/assets/`.

#### Scenario: Configuration parses to the contract
- **WHEN** a test loads `site/hugo.toml` with `tomllib`
- **THEN** every value listed above is present as stated, `taxonomies` has exactly the three entries, and none of `publishDir`, `resourceDir` and `module` is present
- **AND** the only string value containing `://` or beginning with `//` is `params.siteurl`, equal to `http://127.0.0.1:8000`
- **AND** `site/static/` does not exist

#### Scenario: Overlay parses to the contract
- **WHEN** a test calls `hugo_overlay` with a site path and a collection path that both contain a space and a double quote, and loads the result with `tomllib`
- **THEN** it has exactly the keys `publishDir`, `resourceDir` and `module`, with the values and the four mounts listed above
