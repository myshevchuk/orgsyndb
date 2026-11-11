## MODIFIED Requirements

### Requirement: Hugo configuration
The file `site/hugo.toml` SHALL configure Hugo 0.162.1 as follows:
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

`pipeline.hugo_overlay(site, collection, language, lab=False)` SHALL return the text of the collection's overlay `build/hugo-config/_default/hugo.toml`, which the build passes to Hugo through `--configDir <collection>/build/hugo-config`, given the absolute paths of the application's `site/` and of the collection, the site's language, and whether the site links the lab application's views. It sets `defaultContentLanguage` to the language, `publishDir` to `<collection>/public`, `resourceDir` to `<collection>/build/hugo-resources`, and `module.mounts` to exactly these seven mounts, in this order, every path absolute:
1. `<site>/content` → `content`;
2. `<collection>/build/content/procedures` → `content/procedures` with `files = ["/OSDB-*.md"]`;
3. `<collection>/build/content/help` → `content/help`;
4. `<collection>/static` → `static`;
5. `<collection>/build/data/compounds` → `data/compounds`;
6. `<collection>/build/content/sequences` → `content/sequences` with `files = ["/SEQ-*.md"]`;
7. `<collection>/build/data` → `data/collection`.

Mount 2 holds the procedures the build staged, one per ID, as the localization spec defines. Mount 3 holds the help pages the build staged from the application's `docs/`, as the site-help spec defines. Mount 4 replaces Hugo's default `<site>/static` mount, so the application SHALL have no `site/static/`; its own static files go in `site/assets/`. Mount 5 makes each substance of the collection's registry the Hugo data entry `site.Data.compounds.<key>`: the build writes, for each substance, `build/data/compounds/<key>.json` holding its `name`, `name_de`, `formula`, `mw`, `smiles` and `cas`, the four registry fields under their keys (compound-fields "Registry fields"), `chemical_class` a list of keys, and `structure_image`, `structures/<key>.svg`, or `structures/<key>.png` when there is no SVG, when that file exists under the collection's `static/` (compound-registry "Structure images by key"); a value the substance lacks is left out. Mount 6 holds the sequences the build staged, one per ID (synthesis-sequences "Sequence files"). Mount 7 makes the field data, the reaction-type data and the route data the build staged the Hugo data entries `site.Data.collection.fields` (compound-fields "Field data for the site"), `site.Data.collection.reaction_types` (reaction-types "Reaction-type data for the site") and `site.Data.collection.routes` (synthesis-routes "Derived routes"). Mounts 5 and 7 replace Hugo's default `<site>/data` mount, so the application SHALL have no `site/data/`: every data entry of the site comes from the collection.

With `lab` true the overlay also sets `params.lab = true`, which Hugo merges with the `params` of `site/hugo.toml`; the header then links the lab application's views (site-theme "Page shell"). Without it the overlay sets no `params`.

#### Scenario: Configuration parses to the contract
- **WHEN** a test loads `site/hugo.toml` with `tomllib`
- **THEN** every value listed above is present as stated, `taxonomies` has exactly the three entries, and none of `publishDir`, `resourceDir`, `module`, `languages` and `defaultContentLanguage` is present
- **AND** the only string value containing `://` or beginning with `//` is `params.siteurl`, equal to `http://127.0.0.1:8000`
- **AND** neither `site/static/` nor `site/data/` exists

#### Scenario: Overlay parses to the contract
- **WHEN** a test calls `hugo_overlay` with a site path and a collection path that both contain a space and a double quote, and the language `de`, and loads the result with `tomllib`
- **THEN** it has exactly the keys `publishDir`, `resourceDir`, `defaultContentLanguage` and `module`, with the values and the seven mounts listed above
- **AND** called with `lab=True` it has besides them exactly the key `params`, holding only `lab = true`

#### Scenario: Staged substance data
- **WHEN** a test builds a copy of the test collection and reads `build/data/compounds/`
- **THEN** it holds one `<key>.json` per substance of the registry and no other file; the file of `acetylsalicylic-acid` holds `article_number` `CH-0010` and `short_name` `ASA`, the file of a substance without a short name has no `short_name`, and the file of `isopentyl-acetate` holds `structure_image` `structures/isopentyl-acetate.svg`, the collection having `static/structures/isopentyl-acetate.svg`
