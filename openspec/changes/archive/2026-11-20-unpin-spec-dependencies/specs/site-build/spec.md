## MODIFIED Requirements

### Requirement: Hugo configuration
The file `site/hugo.toml` SHALL configure Hugo as follows:
- `baseURL = "/"`, `locale = "de"` and `relativeURLs = true`. The locale is the site's language, as the localization spec defines.
- `buildFuture = true` and `buildExpired = true`, so that no date in front matter decides whether a validated procedure is published.
- `disableKinds` includes `rss` and `sitemap`.
- The taxonomies are exactly `author = "authors"`, `reaction_type = "reaction_types"` and `tag = "tags"`.
- `[permalinks.page]` maps `procedures` to `/procedures/:slug/` and `sequences` to `/sequences/:slug/`.
- `markup.goldmark.renderer.unsafe` is `true`.
- `markup.highlight.noClasses` is `false`, so that highlighted code carries CSS classes and no inline colours, and shows in the theme's colours.
- `minify.tdewolff.html.keepWhitespace` is `true`, so that minified HTML keeps a space between adjacent elements that Pagefind would otherwise index as one word.
- `params.siteurl` is `"http://127.0.0.1:8000"`, the default origin of `tools/orgsyndb serve`. The theme prints it as text before a page's path. The environment variable `HUGO_PARAMS_SITEURL` overrides it without editing the file.
- It sets neither `publishDir`, `resourceDir`, `module`, `languages` nor `defaultContentLanguage`.

The configuration names no host other than the loopback address in `params.siteurl`.

`pipeline.hugo_overlay(site, collection, language, lab=False)` SHALL return the text of the collection's overlay `build/hugo-config/_default/hugo.toml`, which the build passes to Hugo through `--configDir <collection>/build/hugo-config`, given the absolute paths of the application's `site/` and of the collection, the site's language, and whether the site links the lab application's views. It sets `defaultContentLanguage` to the language, `publishDir` to `<collection>/public`, `resourceDir` to `<collection>/build/hugo-resources`, and `module.mounts` to exactly these eight mounts, in this order, every path absolute:
1. `<site>/content` → `content`;
2. `<collection>/build/content/procedures` → `content/procedures` with `files = ["/OSDB-*.md"]`;
3. `<collection>/build/content/help` → `content/help`;
4. `<collection>/static` → `static`;
5. `<collection>/build/data/compounds` → `data/compounds`;
6. `<collection>/build/content/sequences` → `content/sequences` with `files = ["/SEQ-*.md"]`;
7. `<collection>/build/data` → `data/collection`;
8. `<collection>/build/substances` → `static/substances`.

Mount 2 holds the procedures the build staged, one per ID, as the localization spec defines. Mount 3 holds the help pages the build staged from the application's `docs/`, as the site-help spec defines. Mount 4 replaces Hugo's default `<site>/static` mount, so the application SHALL have no `site/static/`; its own static files go in `site/assets/`. Mount 5 makes each substance of the collection's registry the Hugo data entry `hugo.Data.compounds.<key>`: the build writes, for each substance, `build/data/compounds/<key>.json` holding its `name`, `name_de`, `formula`, `mw`, `smiles` and `cas`, the four registry fields under their keys (compound-fields "Registry fields"), `chemical_class` a list of keys, and `structure_image`, `substances/<key>/structure.svg`, when the build staged that image (compound-registry "Structure images"); a value the substance lacks is left out. Mount 6 holds the sequences the build staged, one per ID (synthesis-sequences "Sequence files"). Mount 7 makes the field data and the reaction-type data the build staged the Hugo data entries `hugo.Data.collection.fields` (compound-fields "Field data for the site") and `hugo.Data.collection.reaction_types` (reaction-types "Reaction-type data for the site"). Mounts 5 and 7 replace Hugo's default `<site>/data` mount, so the application SHALL have no `site/data/`: every data entry of the site comes from the collection. Mount 8 publishes the structure images the build staged at `substances/<key>/structure.svg` (compound-registry "Structure images").

With `lab` true the overlay also sets `params.lab = true`, which Hugo merges with the `params` of `site/hugo.toml`; the navigation then keeps its links under `/lab/` (site-theme "Navigation"). Without it the overlay sets no `params`.

#### Scenario: Configuration parses to the contract
- **WHEN** a test loads `site/hugo.toml` with `tomllib`
- **THEN** every value listed above is present as stated, `taxonomies` has exactly the three entries, and none of `publishDir`, `resourceDir`, `module`, `languages` and `defaultContentLanguage` is present
- **AND** the only string value containing `://` or beginning with `//` is `params.siteurl`, equal to `http://127.0.0.1:8000`
- **AND** neither `site/static/` nor `site/data/` exists

#### Scenario: Overlay parses to the contract
- **WHEN** a test calls `hugo_overlay` with a site path and a collection path that both contain a space and a double quote, and the language `de`, and loads the result with `tomllib`
- **THEN** it has exactly the keys `publishDir`, `resourceDir`, `defaultContentLanguage` and `module`, with the values and the eight mounts listed above
- **AND** called with `lab=True` it has besides them exactly the key `params`, holding only `lab = true`

#### Scenario: Staged substance data
- **WHEN** a test builds a copy of the test collection and reads `build/data/compounds/`
- **THEN** it holds one `<key>.json` per substance of the registry and no other file; the file of `acetylsalicylic-acid` holds `article_number` `CH-0010` and `short_name` `ASA`, the file of a substance without a short name has no `short_name`, and the file of `isopentyl-acetate` holds `structure_image` `substances/isopentyl-acetate/structure.svg`, the collection's registry file having `substances/isopentyl-acetate/structure.svg` beside it

### Requirement: Pagefind binary acquisition
`build` SHALL index with the pinned version of the Pagefind standalone binary at `<app>/.tools/pagefind-<version>/pagefind`, obtained through `pipeline.ensure_pagefind(<app>/.tools)`, which returns the binary's path and works as follows:
- It accepts a cached binary only when its SHA-256 is the binary hash `tools/pipeline.py` pins.
- Otherwise it downloads the pinned release's `x86_64-unknown-linux-musl` tarball from Pagefind's GitHub releases into an empty download directory and requires the tarball's SHA-256 to be the tarball hash `tools/pipeline.py` pins.
- From the tarball it extracts only the regular-file member `pagefind`. It requires that file's SHA-256 to be the binary hash above, makes it executable, and moves it into place.
- Any mismatch or download error removes everything that run wrote and raises `PagefindError`, so that `build` exits 1, with a message giving the URL or the expected and actual hashes.

No Node, npm or pip is used.

`pipeline.install_pagefind(tarball, tar_sha256, bin_sha256, dest)` performs the verification and extraction, and raises `PagefindError` on a mismatch.

#### Scenario: Valid tarball installs the binary
- **WHEN** a test builds a local tarball whose only member is a regular file `pagefind`, and calls `install_pagefind` with that tarball's hash and that member's hash
- **THEN** `dest` holds an executable `pagefind` whose bytes equal the member's

#### Scenario: Wrong tarball hash
- **WHEN** a test calls `install_pagefind` on the same tarball with a different `tar_sha256`
- **THEN** it raises `PagefindError`, whose message contains both the expected and the actual hash, and `dest` holds no `pagefind`

#### Scenario: Wrong binary hash
- **WHEN** a test calls `install_pagefind` with the correct `tar_sha256` and a different `bin_sha256`
- **THEN** it raises `PagefindError`, and `dest` holds no `pagefind`

#### Scenario: Unsafe member is refused
- **WHEN** a test calls `install_pagefind` on a tarball whose `pagefind` member is a symbolic link, giving the tarball's correct hash
- **THEN** it raises `PagefindError`, and nothing is written outside `dest`

### Requirement: Search index
`build` SHALL run Pagefind over `public/` after Hugo, writing the bundle to `public/pagefind/`. Only procedure pages are indexed, under the site's language.

#### Scenario: Bundle location and page count
- **WHEN** an integration test builds a copy of the test collection `tests/fixtures/collection/`
- **THEN** `public/pagefind/pagefind.js`, `public/pagefind/pagefind-ui.js` and `public/pagefind/pagefind-ui.css` exist
- **AND** `public/pagefind/pagefind-entry.json` parses as JSON with `version` equal to the pinned Pagefind version, `languages` holding only the site's language, and its `page_count` equal to the number of published procedures
