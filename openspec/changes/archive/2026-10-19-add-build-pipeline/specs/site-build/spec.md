## ADDED Requirements

<!-- "Integration test" is defined in the org-export spec. A site-build
integration test additionally skips when hugo, or the cached Pagefind
binary, is absent, and names which one. -->

### Requirement: Hugo configuration
The file `site/hugo.toml` SHALL configure Hugo 0.162.1 as follows:
- `baseURL = "/"`, `locale = "en"`, `publishDir = "../public"` and `relativeURLs = true`.
- `buildFuture = true` and `buildExpired = true`, so that no date in front matter decides whether a validated procedure is published.
- `disableKinds` includes `rss` and `sitemap`.
- The taxonomies are exactly `author = "authors"`, `reaction_type = "reaction_types"` and `tag = "tags"`.
- `[permalinks.page]` maps `procedures` to `/procedures/:slug/`.
- `markup.goldmark.renderer.unsafe` is `true`.
- `module.mounts` is exactly these three mounts, in this order:
  1. `content` → `content`;
  2. `../build/export` → `content/procedures` with `files = ["/OSDB-*.md"]`;
  3. `../md/procedures` → `content/procedures` with `files = ["/OSDB-*.md"]`.

The configuration names no host.

#### Scenario: Configuration parses to the contract
- **WHEN** a test loads `site/hugo.toml` with `tomllib`
- **THEN** every value listed above is present as stated, `taxonomies` has exactly the three entries, and `module.mounts` equals the three listed mounts

### Requirement: Merged procedures section
A build SHALL publish each procedure content file of `build/export/` and `md/procedures/` as one page at `public/procedures/<slug>/index.html`, whatever its `date`, `publishDate` or `expiryDate`. No other file from those two directories is published.

#### Scenario: Org-sourced and Markdown-sourced pages
- **WHEN** an integration test runs `tools/orgsyndb build` on the seed procedures
- **THEN** `public/procedures/osdb-0001/index.html` (from Org) and `public/procedures/osdb-0002/index.html` (from Markdown) exist
- **AND** the subdirectories of `public/procedures/` are exactly the `slug` values of the content files in `build/export/` and `md/procedures/`

#### Scenario: Future-dated procedure is published, indexed and printed
- **WHEN** an integration test adds to `md/procedures/` a copy of `tests/fixtures/baseline/OSDB-0100-baseline.md` whose `date` and `lastmod` are `2099-01-01T10:00:00+01:00`, and runs `tools/orgsyndb pdf`
- **THEN** it exits 0, `public/procedures/osdb-0100/index.html` exists, `languages.en.page_count` in `public/pagefind/pagefind-entry.json` counts it, and `pdf/OSDB-0100-baseline.pdf` exists

#### Scenario: Expired procedure is still published
- **WHEN** an integration test adds to `md/procedures/` a copy of the same baseline with the line `expiryDate = 2026-02-01T10:00:00+01:00` added to its front matter, and builds
- **THEN** the build exits 0, with the validator's `unknown field` warning for `expiryDate`, and `public/procedures/osdb-0100/index.html` exists

#### Scenario: Stray file and section index are not published
- **WHEN** an integration test adds `md/procedures/notes.txt` and an `md/procedures/_index.md` titled `Hijack`, then builds
- **THEN** the build exits 0, `public/procedures/notes.txt` does not exist, and `public/procedures/index.html` does not contain `Hijack`

### Requirement: Minimal layout contract
The layouts SHALL live in `site/layouts/`. Whichever layouts are in place, now or after change 3 replaces them, they meet all of the following:
- On every procedure page, the rendered body is inside exactly one element carrying `data-pagefind-body`.
- No other page carries `data-pagefind-body`.
- The procedure page shows the procedure's `title` and `id`.
- Every HTML page has `<html lang="en">`, `<meta charset="utf-8">` and a `<title>` element.
- Asset references in layouts are root-relative paths.
- A procedure page's content does not depend on JavaScript.

#### Scenario: One indexed body per procedure page
- **WHEN** an integration test builds the seeds and parses every HTML file under `public/` with `html.parser`
- **THEN** each of `procedures/osdb-0001/index.html` and `procedures/osdb-0002/index.html` has exactly one element with `data-pagefind-body`, and that element contains the procedure's `Summary` heading
- **AND** no other HTML file has such an element

#### Scenario: Title and ID shown
- **WHEN** the same test reads `procedures/osdb-0002/index.html`
- **THEN** the text outside the indexed body contains the seed's title and `OSDB-0002`

### Requirement: No fetches from other hosts
A built site SHALL contain no reference that makes a browser or WeasyPrint fetch from a host other than the serving one. The rules are:
- In HTML, no `src`, `srcset`, `poster` or `data` attribute, and no `href` on a `<link>` element, has a value beginning with `http:`, `https:` or `//`.
- In HTML `style` attributes, `<style>` elements and CSS files under `public/` (including `public/pagefind/`), no `url(...)` or `@import` target begins with one of those prefixes.
- Links in `<a href>` are not fetches and are allowed, for example literature citations.

#### Scenario: Seed build fetches nothing remote
- **WHEN** an integration test builds the seeds and scans `public/` with the rules above
- **THEN** no violation is found

### Requirement: Pagefind binary acquisition
`build` SHALL index with the Pagefind 1.5.2 standalone binary at `<repo>/.tools/pagefind-1.5.2/pagefind`, obtained through `tools/pipeline.py ensure-pagefind --tools-dir <repo>/.tools`. That command prints the binary's path and works as follows:
- It accepts a cached binary only when its SHA-256 is `c4b86009ce5420dc2a1748ab2705bef6ba730ed883f684fd52ef6008bd600532`.
- Otherwise it downloads `https://github.com/Pagefind/pagefind/releases/download/v1.5.2/pagefind-v1.5.2-x86_64-unknown-linux-musl.tar.gz` into an empty download directory and requires the tarball's SHA-256 to be `afb824a9e7f64905a934900481cea5be679c03975e527329e0e5e6cc70f5feda`.
- From the tarball it extracts only the regular-file member `pagefind`. It requires that file's SHA-256 to be the binary hash above, makes it executable, and moves it into place.
- Any mismatch or download error removes everything that run wrote and exits 1, with a message giving the URL or the expected and actual hashes.

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
`build` SHALL run Pagefind over `public/` after Hugo, writing the bundle to `public/pagefind/`. Only procedure pages are indexed.

#### Scenario: Bundle location and page count
- **WHEN** an integration test builds the seeds
- **THEN** `public/pagefind/pagefind.js`, `public/pagefind/pagefind-ui.js` and `public/pagefind/pagefind-ui.css` exist
- **AND** `public/pagefind/pagefind-entry.json` parses as JSON with `version` equal to `1.5.2`, and `languages.en.page_count` equal to the number of procedure content files in `build/export/` and `md/procedures/`
