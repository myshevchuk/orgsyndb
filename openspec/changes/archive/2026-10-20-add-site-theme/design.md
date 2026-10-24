## Context

This is change 3 of 3. Changes 1 and 2 are archived, and their specs in
`openspec/specs/` govern this change:

- `procedure-schema` and `procedure-validation` (change 1);
- `org-export`, `site-build`, `build-script` and `sample-procedures`
  (change 2).

The interface this change inherits is the site-build "Minimal layout
contract". It requires:

- exactly one `data-pagefind-body` element on each procedure page, and
  none on any other page;
- the title and ID shown on the procedure page;
- `lang`, `charset` and `<title>` on every page;
- root-relative assets;
- procedure content that needs no JS.

The site-build requirement "No fetches from other hosts" also stands.
Three inherited requirements are modified, each with a reason (D18).

State on `main` at the start:

- `tools/orgsyndb build` exports, validates (`validated 3 files`),
  runs `hugo --source site --minify`, then Pagefind 1.5.2.
- `pdf` renders every page in `public/procedures/` with WeasyPrint 70.0,
  allowing only `file:` URLs. A job fails only on an `ERROR:` line;
  warnings pass through to stderr.
- `site/layouts/` holds `baseof.html`, `single.html` and `list.html`, with
  no CSS.
- The two seeds are OSDB-0001 (Org, hydrolysis) and OSDB-0002 (Markdown,
  acylation, with `precursors = ["OSDB-0001"]`).

Machine facts:

- Fedora 44: Hugo 0.162.1 (Fedora's extended build), WeasyPrint 70.0,
  pdfinfo/pdftotext 26.01.0 (poppler) and Firefox 158.0.
- Node 22.23.1 is present but must not become a dependency.
- Chromium is not installed.

## Goals / Non-Goals

**Goals:**

- The site of brief §6: pages, design, print and samples. Acceptance
  checks 2, 3, 4, 5 and 7 pass, automated wherever a stdlib scanner,
  `pdftotext` or the real Pagefind binary can decide them.
- Every behaviour that depends on a tool's quirks is pinned by a test
  that runs the pinned tool: Pagefind's tokeniser, Hugo's minifier and
  WeasyPrint's CSS support.
- No runtime or build dependency beyond change 2's.

**Non-Goals:**

- Web editing UI, SMILES rendering, substructure search, sign-off
  workflow, authentication, deployment. The one deployment hook is
  `HUGO_PARAMS_SITEURL` (D11).
- Changing `tools/`, the schema or the validator.
- Writing documents a person reads. The doc writer writes them from
  this change's facts (proposal Impact).

## Decisions

### D1. Page and partial structure

Hugo 0.162.1 picks templates by page kind (verified on a probe copy):

- `home.html`, `section.html`, `taxonomy.html` and `term.html`;
- `page.html` for regular pages;
- `procedures/page.html` for pages in the `procedures` section;
- `<layout>.html` for a page whose front matter sets `layout`.

`_partials/` and `_markup/` are the partial and render-hook directories.

| URL | Source | Template |
|---|---|---|
| `/` | `site/content/_index.md` (exists) | `home.html` |
| `/procedures/` | `site/content/procedures/_index.md`, title "All procedures" | `section.html` (by ID) |
| `/procedures-by-date/` | `site/content/procedures-by-date.md`, `layout = "procedures-by-date"` | `procedures-by-date.html` (newest first) |
| `/procedures/<slug>/` | the mounted content files | `procedures/page.html` |
| `/reaction_types/`, `/tags/`, `/authors/` | `site/content/reaction_types/_index.md`, title "Reaction types" (Hugo's default would be "Reaction_types"); tags and authors use Hugo's default titles "Tags" and "Authors" | `taxonomy.html` |
| `/<taxonomy>/<term>/` | generated | `term.html` |
| `/search/` | `site/content/search.md`, `layout = "search"` | `search.html` |
| fallback for any other regular page | — | `page.html` |

`list.html` and `single.html` are removed: every kind now has its own
template. `baseof.html` keeps a literal `<head>` line, because the
build-script scenario "Remote stylesheet fails the job" inserts a `<link>`
right after it.

Partials:

- `site-header.html`: the skip link and the site navigation.
- `site-footer.html`.
- `page-title.html`: the display title. For a reaction-type term it is the
  vocabulary label, for a tag the tag itself, otherwise `.Title`.
  Without it, Hugo title-cases term names, so `sample-data` becomes
  "Sample-Data" (verified).
- `reaction-type-label.html`: slug to label via `site.Data.reaction_types`,
  falling back to the slug.
- `procedure-table.html`: the list table for a page collection.
- `procedure-header.html`: banner, ID line, status badge, `h1`, print facts
  and actions.
- `procedure-meta.html`: the metadata panel (D6).
- `procedure-links.html`: precursor and used-in lists (D9).
- `structure.html`: the image or the placeholder slot (D14).
- `smiles-index.html`: the search-only SMILES suffix element (D7).
- `print-page-style.html`: the inline `@page` header rule (D11).

The procedure page, in document order:

1. the sample banner, when tagged `sample-data` (D10);
2. `header.procedure-header`: the ID (`data-pagefind-meta="id"`), the
   status badge (`data-pagefind-filter="status"`), the `h1` title,
   `p.print-facts` (print only), and the actions row holding the hidden
   print button;
3. `article.procedure[data-pagefind-body]`: the metadata panel, the
   structure figure, the rendered body, and the SMILES index element.

Site URLs in templates are root-relative literals such as `/procedures/`,
or `.RelPermalink`. `relativeURLs` rewrites them in attributes, which
`file:` rendering by WeasyPrint needs.

*Rejected alternatives:*

- *One `list.html` that branches on `.Kind`.* It works, but every page
  kind then shares one file of conditionals, and the per-kind lookup is
  what Hugo 0.162 is organised around.
- *Taxonomy titles hard-coded in templates.* An `_index.md` per taxonomy
  keeps the titles in content, and Hugo's own lookup uses them in
  `<title>`.

### D2. CSS organisation

Sources live in `site/assets/css/`:

| File | Media | Contents |
|---|---|---|
| `tokens.css` | all | the light colour tokens, font stacks, `--measure: 70ch`, spacing |
| `base.css` | all | typography, layout, components, tables, `.num` columns, `.print-only { display: none }`; no `overflow: hidden`/`clip` and no fixed `height`/`max-height` (D12), so no visually-hidden helper either |
| `screen.css` | screen | the dark tokens (D3), the Pagefind UI variables, `.table-scroll { overflow-x: auto }`, `:focus-visible`, hover states |
| `print.css` | print | `@page`, and the print rules (D11) without an `@media` wrapper |

`baseof.html` builds three stylesheets with Hugo Pipes features that the
standard (non-extended) build has, and links them:

```
{{ $base := slice (resources.Get "css/tokens.css") (resources.Get "css/base.css")
     | resources.Concat "css/base.css" | minify | fingerprint }}
<link rel="stylesheet" href="{{ $base.RelPermalink }}">
{{ $screen := resources.Get "css/screen.css" | minify | fingerprint }}
<link rel="stylesheet" href="{{ $screen.RelPermalink }}" media="screen">
{{ $print := resources.Get "css/print.css" | minify | fingerprint }}
<link rel="stylesheet" href="{{ $print.RelPermalink }}" media="print">
```

The search page adds `/pagefind/pagefind-ui.css`. JS is built the same
way:

- `js/site.js` → `/js/site.min.<hash>.js`;
- `js/search-terms.js` + `js/search.js`, concatenated → one search
  bundle.

The split by media is what makes WeasyPrint's output clean. With one
stylesheet holding `@media screen and (prefers-color-scheme: dark)`,
`overflow-x` and `clip-path`, WeasyPrint printed five `WARNING:` lines per
PDF:

- "Expected a media type", followed by "the whole @media rule was
  ignored";
- "Ignored `overflow-x:auto` …, unknown property";
- "Ignored `clip-path:inset(50%)` …".

With the split above, all five PDFs rendered with zero warnings
(verified). WeasyPrint does not load a `media="screen"` link. Browsers do
not apply it when printing, so the dark tokens can never reach paper.

*Rejected alternatives:*

- *Plain files in `site/static/css/`.* They need no pipes, but are not
  minified and carry no fingerprint, so browsers behind `http.server`
  can show a stale stylesheet after an update.
- *One stylesheet with `@media screen` and `@media print` blocks.* This
  gave WeasyPrint's warnings above, five per PDF, forty per `pdf` run.
- *Sass or PostCSS.* These need the extended build, Dart Sass or Node.
- *Inline CSS in every page.* It is repeated in every file, cannot be
  cached, and is harder to test as a unit.

### D3. Colour tokens and dark mode

Colours are CSS custom properties on `:root`, written as `#rrggbb`:

- **Light** (`tokens.css`, all media): `--bg #ffffff`, `--fg #1a1a1a`,
  `--muted #555555`, `--border #c8c8c8`, `--surface #f4f4f1`,
  `--link #0b4f8a`, `--focus #b35c00`, and the pairs `--banner-bg #fff4d6`
  / `--banner-fg #4a3300`, `--draft-bg #fde8c8` / `--draft-fg #5c3a00`,
  `--checked-bg #d6f0dc` / `--checked-fg #0f4a1f`, and
  `--retired-bg #e4e4e4` / `--retired-fg #3a3a3a`.
- **Dark** (`screen.css`, inside `@media (prefers-color-scheme: dark)`):
  `--bg #15171a`, `--fg #e6e6e3`, `--muted #a8a8a3`, `--border #3d4147`,
  `--surface #1f2226`, `--link #8cc4ff`, `--focus #ffb366`,
  `--banner-bg #3a2f12` / `--banner-fg #ffe7a8`, `--draft-bg #4a3410` /
  `--draft-fg #ffe0b0`, `--checked-bg #173d22` / `--checked-fg #c4f0cf`,
  and `--retired-bg #33363a` / `--retired-fg #dddddd`.

These are the values the prototype used. The implementer may change
them, provided the tested pairs keep their thresholds.

WCAG contrast of these values, computed:

| Pair | Light | Dark |
|---|---|---|
| fg/bg | 17.40 | 14.36 |
| muted/bg | 7.46 | 7.52 |
| link/bg | 8.40 | 9.80 |
| fg/surface | 15.79 | 12.77 |
| muted/surface | 6.77 | 6.69 |
| link/surface | 7.62 | 8.71 |
| banner | 10.86 | 10.81 |
| draft badge | 8.52 | 9.24 |
| checked badge | 8.59 | 9.68 |
| retired badge | 8.95 | 8.94 |
| focus/bg | 4.72 | 10.17 |

Rules:

- Text pairs must reach at least 4.5:1, and focus/bg at least 3:1 (WCAG
  non-text contrast). A test parses the two source files and checks
  every pair.
- `screen.css` maps Pagefind's UI variables (`--pagefind-ui-primary`,
  `-text`, `-background`, `-border`, `-tag`, `-font`) to these tokens.
- `<meta name="color-scheme" content="light dark">` lets form controls
  follow the scheme. The `color-scheme` property is deliberately absent
  from the CSS, because WeasyPrint does not know it.
- Structure images are black on their own white rectangle (D14). In dark
  mode they sit on a white panel, which is the chemistry convention and
  safe in print.

Verified: Firefox headless with `ui.systemUsesDarkTheme=1` rendered the
dark scheme. `layout.css.prefers-color-scheme.content-override=0` alone
did not.

*Rejected alternatives:*

- *A separate `<link media="(prefers-color-scheme: dark)">`.* A media
  query without a media type also matches print. A browser on a dark
  desktop would then print dark tokens, and WeasyPrint warns on such
  queries.
- *The `light-dark()` colour function.* It is newer than the targets
  need, depends on `color-scheme`, and would apply in print as well.
- *A JS theme toggle with `localStorage`.* The brief asks for
  `prefers-color-scheme`, and it adds a JS dependency to every page.

### D4. Sorting by ID or date without JS

There are two static pages, each with the same table (ID, Procedure,
Reaction type, Status, Created, Modified):

- `/procedures/` is sorted by ID ascending: `sort .Pages "Params.id"`.
- `/procedures-by-date/` is sorted by `date` descending, ties by ID
  ascending: `sort (sort $procedures "Params.id") "Date" "desc"`. Hugo's
  `sort` is stable. The seeds share one `date`, and the probe listed
  OSDB-0001 before OSDB-0002, where a title tie-break would have given
  the reverse (verified).

Each page links to the other above the table. The current order is marked
`aria-current="page"`. The home page's "Recent procedures" are the first
five of the date order.

"Date" means `date` (creation). Both dates are shown.

*Rejected alternatives:*

- *`/procedures/by-date/`.* The site-build scenario "Org-sourced and
  Markdown-sourced pages" requires the subdirectories of
  `public/procedures/` to be exactly the procedure slugs.
- *Sorting the table in JS.* The lists must work without JS.
- *Both orders on one page.* The table is duplicated, and so is every
  link on it.
- *A custom Hugo output format such as `procedures/by-date.html`.* It
  needs more configuration for a URL shape that differs from every
  other page.

### D5. Search UI and its no-JS fallback

The search page uses Pagefind's default UI, `pagefind-ui.js` and
`pagefind-ui.css` from the built bundle, configured like this:

```
new PagefindUI({ element: "[data-search]", showImages: false,
                 processTerm: OrgSynSearch.normaliseTerm,
                 processResult: OrgSynSearch.cleanResult })
```

Then, when `?q=` is present, `ui.triggerSearch(q)`. `resetStyles` stays at
its default; colours come from the Pagefind variables (D3).

The bundle ships three UIs. A grep of the shipped files decided the
choice:

- `pagefind-ui.js` has `processTerm`, `processResult`, `triggerSearch`
  and `triggerFilters`.
- `pagefind-component-ui.js` has no `processTerm`, which the SMILES
  design needs (D7).
- The modular UI needs more glue for the same result.

No-JS fallback:

- The home page's search form is an ordinary `GET` form to `/search/`
  with field `q`. With JS, the glue reads `q`.
- The search page carries `<noscript>` text linking to `/procedures/`,
  `/reaction_types/`, `/tags/` and `/authors/`. Those pages give
  JS-free faceted browsing.

How the default UI behaves (verified in headless Firefox driven over
WebDriver BiDi):

- Filters appear once a term is searched, and narrow it. With an empty
  term the UI shows no filter panel and runs no search.
- Two values ticked in one group must both match: Esterification plus
  Hydrolysis gave no results.
- Group names are the filter keys, capitalised: `reaction type` shows as
  "Reaction type".
- Result meta other than title, image and URL is shown under each result,
  so `id` appears as "Id: OSDB-0001".
- `triggerSearch` with `?q=c1ccccc1O` returned only salicylic acid.

*Rejected alternatives:*

- *The component UI.* It cannot normalise the query.
- *A hand-written UI over `pagefind.js`.* It means more JS to maintain
  for what the default UI already does accessibly: a native input,
  checkboxes and keyboard focus.

### D6. What is indexed: "only the article body" with searchable metadata

The indexed element is `article.procedure`. It holds:

- the metadata panel `dl.metadata`;
- the structure figure;
- the rendered Markdown;
- the SMILES index element (D7).

Outside it are the banner, the ID line and status badge, the `h1`, the
print facts, the actions, and the site header, navigation and footer.

This reads brief §3's "index only the article body" as "the procedure
record, not the page chrome". The panel is part of the record. Pagefind
takes the result title from the first `h1` on the page, wherever it is
(verified: `meta.title` was the title with the `h1` outside the body).

Panel labels and their order, each shown only when the field is set:

> ID, Product, Formula, MW, CAS, SMILES, Scale, Yield, Reaction type,
> Tags, Authors, Checked by, Created, Modified, Precursors, Used in.

**Word boundaries.** Pagefind joins the text of adjacent `<dt>`/`<dd>` and
`<th>` elements into one word when no whitespace separates them. Hugo's
minifier removes that whitespace. The probe index held
`cas50782smilesccooc1ccccc1coo` and `reagentcasmw`, and a search for
`50-78-2` returned four pages instead of one (verified). Two changes fix
it, and the probe needed both:

1. Templates put a newline between every `</dt>` and `<dd>`, and the
   table render hook one between cells.
2. `site/hugo.toml` gains:

   ```
   [minify.tdewolff.html]
   keepWhitespace = true
   ```

Without (2), header cells were glued again (`reagentcasmw`). With both,
the index held separate words `cas`, `50782` and `product`, and
`50-78-2` returned exactly OSDB-0002 (verified).

*Rejected alternatives:*

- *Hidden indexed text duplicating the metadata.* It duplicates visible
  content and doubles its weight in ranking.
- *Metadata only as `data-pagefind-meta` with the panel outside the
  body.* Meta values are searchable in 1.5.2 (verified). But the UI
  shows every meta key under every result, and excerpts would never show
  why a CAS search matched.
- *Turning the minifier off.* `--minify` is part of the build-script
  contract.

### D7. SMILES substring search

Pagefind matches words by prefix. It strips punctuation inside a word,
also indexes the parts between punctuation and digits, and stems English
words (verified by decoding a probe index). A plain SMILES is therefore
found only by its first characters. The default UI also splits a
punctuated query unpredictably: `OC(=O)N` returned three pages, of which
only one contained it (verified).

The design has two halves:

- **Index side.** Each procedure page carries, at the end of the body,
  `<span hidden data-smiles-index="…" data-pagefind-meta="smiles_index[data-smiles-index]"></span>`.
  Let `N(s)` be the SMILES lowercased with everything outside `[a-z0-9]`
  removed. The attribute holds every suffix of `N(s)`, longest first,
  separated by single spaces. Hugo computes it with `replaceRE`, `seq`
  and `substr`. Pagefind indexes meta values as words, prefix-searchable,
  and never puts them in excerpts (verified).
- **Query side.** `OrgSynSearch.normaliseTerm` removes every character
  that is not a Unicode letter or number from each whitespace-separated
  word. Pagefind lowercases. A SMILES substring `q` then becomes `N(q)`,
  which is a prefix of the suffix that starts where `q` starts.

`OrgSynSearch.cleanResult` deletes `smiles_index` from a result's meta,
so the UI does not list it.

Verification with the pinned binary covered six probe molecules (with
`/`, `[N+]`, `(=O)` and long carbon chains) and every substring whose
`N` has at least three characters:

| Variant | Queries | Misses | False positives |
|---|---|---|---|
| plain SMILES | 611 | 674 | 0 |
| suffixes as hidden body text | 611 | 0 | 0 |
| suffixes as a meta field | 611 | 0 | 0 |

The hidden-text variant was dropped because its suffixes appeared in
result excerpts ("ococ1ccccc1o coc1ccccc1o …", seen in the UI). The
same sweep took 2.1 s for 611 queries.

Stemming cannot cause a miss in this scheme. On the index side it removes
at most one final letter from a suffix word: the suffixes the stemmer
removes (`s`, `e`) are single letters, and no lowercased organic SMILES
spells a longer one. On the query side stemming only shortens the query,
which keeps it a prefix.

Normalisation also helps other queries:

- CAS: `50-78-2` → `50782`, matching Pagefind's own joined form.
- Tags: `sample-data` → `sampledata`.

The cost is that a hyphenated query never matches the same words written
apart. For example, `acetic-anhydride` does not find "acetic anhydride".

`N` also drops bond, branch, charge and stereo symbols, so the search is a
substring search over the atoms and ring digits, not over the full SMILES
grammar. Among the samples, the ketone OSDB-0004 (`CC(=O)c1ccc(cc1)-c1ccccc1`)
and the alcohol OSDB-0005 (`CC(O)c1ccc(cc1)-c1ccccc1`) normalise to the
same `ccoc1ccccc1c1ccccc1`. A search for either full SMILES returns both,
and nothing else. Likewise (E)-cinnamic acid OSDB-0008 normalises to
`ococcc1ccccc1`, a suffix of ethyl cinnamate OSDB-0007's
`ccococcc1ccccc1`, so every SMILES query that finds OSDB-0008 also finds
OSDB-0007. `CCOC(=O)/C=C` finds OSDB-0007 alone. The
site-search scenarios state exactly this, as a containment of `N` strings.
This is acceptable because structure search is out of scope, and the
search never misses.

*Rejected alternative:* encoding `=`, `#` and the parentheses as letters
that organic SMILES never use (for example `q`, `j`, `x`, `y`). Every
query, not only SMILES, would pass through the mapping. The letters would
collide with element symbols once inorganic content appears (`Xe`, `Y`).
And the result would still be a text search, not a structure match.

*Rejected alternatives:*

- *`--include-characters "()=#[]@+-/\"`.* Each SMILES becomes one word,
  so only prefixes match: `CC(=O)O` found aspirin, but `c1ccccc1` and
  `C(=O)O` found nothing (verified). It also changes tokenisation of
  every text on the site.
- *Character n-grams.* More words than suffixes, with no gain, since
  Pagefind already does prefix matching.
- *Searching SMILES in JS over a separately emitted JSON list.* It would
  be a second search engine beside Pagefind.

### D8. Filter attributes: labels, not slugs

| Filter key | Element | Value |
|---|---|---|
| `status` | the status badge in the header | the status word (`draft`, `checked`, `retired`) |
| `reaction type` | the reaction-type link in the panel | the vocabulary label, e.g. `Aldol condensation` |
| `tag` | each tag link in the panel | the tag, e.g. `sample-data` |
| `author` | each author link in the panel | the author's name as written |

Each attribute is the content form, `data-pagefind-filter="<key>"`, on a
visible element whose text is the value. Pagefind captures filters
anywhere on the page (verified with filters outside the body). Filter
values are not searchable words (verified), so the panel text carries the
search side.

Labels are used because the UI shows filter values verbatim. Tags have no
labels, so their slugs show.

Do not put the attribute on a `<ul>`: the list's text was captured as
`sample-data.`, with a trailing full stop (verified). One element per
value is required.

*Rejected alternatives:*

- *Reaction-type slugs as values.* The UI would show
  `aldol-condensation`.
- *The key `reaction_type`.* The UI would show "Reaction_type".
- *Hidden spans carrying the filters.* They duplicate the visible
  links.

### D9. Precursor and used-in links

- **Precursors.** For each ID in `precursors`, the template finds the page
  with `index (where site.RegularPages "Params.id" $id) 0`. It renders
  `<a class="precursor" href="{{ .RelPermalink }}">ID Title</a>`.
- **Used in.** `where (where site.RegularPages "Section" "procedures")
  "Params.precursors" "intersect" (slice .Params.id)`, sorted by ID. Each
  is `<a class="used-in">ID Title</a>`.

Verified on the probe: OSDB-0001 listed OSDB-0002 and two fixtures, and
pages without `precursors` (search, the date list) caused no error.

*Rejected alternatives:*

- *Making `precursors` a Hugo taxonomy.* The site-build spec fixes the
  taxonomies as exactly three, and term pages for IDs are meaningless.
- *A reverse index computed by `pipeline.py`.* That is a new build step
  and data file for something Hugo computes in one `where`.
- *JS.* Procedure content must not depend on it.

### D10. Banner trigger

The banner shows when `in .Params.tags "sample-data"`. It is
`<p class="sample-banner" role="note">Sample data — quantities not
experimentally verified.</p>`, placed before the procedure header and
outside the indexed body. Print keeps it, with a black border.

*Rejected alternatives:*

- *`status = "draft"`.* Real drafts are not sample data.
- *A new front-matter flag.* The schema is frozen, and the validator
  would warn `unknown field`.

### D11. Print stylesheet for WeasyPrint, with a browser fallback

`print.css` (`media="print"`) holds:

- `@page { size: A4; margin: 22mm 16mm 20mm 16mm; @bottom-center {
  content: "Page " counter(page) " of " counter(pages) } }`, in a small
  sans-serif face.
- Black on white: every `color` is `#000`, and every background is
  `#fff`, `none` or `transparent`. Badges get a 1px black border, the
  banner a 1.5pt one.
- Hidden: site header and navigation, footer, skip link, `.actions`, all
  buttons, the search form, and the structure placeholder.
- `.print-only { display: block }` reveals `p.print-facts`.
- `h1`–`h4 { break-after: avoid }`.
- `break-inside: avoid` on `tr`, `li`, metadata rows and `figure`.
- `thead { display: table-header-group }`.
- Tables: `width: 100%`, font about 8.5pt, `overflow-wrap: anywhere` in
  cells, and `white-space: nowrap` on `.num` cells.

**Running header.** `print-page-style.html` puts a per-page rule in the
procedure page's `<head>`:

```
<style>@page { @top-left { content: "{{ .Params.id }}" } @top-right { content: "{{ .Title }}" } }</style>
```

Go's `html/template` escapes values inside a CSS string. A title
`Bob's "best" </style> ester \ x` came out as
`"Bob\27s \22 best\22  \3c\2fstyle\3e  ester \\ x"`, and WeasyPrint's
header read back the exact title (verified).

**First-page facts.** Brief §6.3 requires the full URL on the first
printed page, and nothing waives it, so a full URL is the default.
`p.print-facts` holds `<span class="page-url">URL</span>`, then
`· <ID> · status <status> · last modified <YYYY-MM-DD HH:MM>` (from
`lastmod`). The URL is built as follows:

- `site/hugo.toml` sets `[params] siteurl = "http://127.0.0.1:8000"`, the
  origin `tools/orgsyndb serve` uses by default.
- The environment variable `HUGO_PARAMS_SITEURL` overrides it, for an
  internal host. Verified: with the configured default, the page carried
  `http://127.0.0.1:8000…`; with the variable set, it carried
  `https://orgsyndb.example.invalid…`.
- The URL is `siteurl` with any trailing `/` removed, followed by
  `.RelPermalink`, written whole as the text of `span.page-url`.
- In a browser, `site.js` replaces that span's text with `location.href`
  when the protocol is `http:` or `https:`. A browser printout therefore
  always shows the address actually used, including another `--port`.

The URL is plain text, never an attribute value, so:

- `relativeURLs` leaves it alone, since it rewrites attributes only;
- the site-build "No fetches from other hosts" rules, which cover
  fetching attributes, `url()` and `@import`, do not apply to it, and
  that requirement needs no change;
- a raw `grep` for `http://` in `public/` does find it, once per
  procedure page. The manual check (task 9.1) therefore removes exactly
  the matches of `^<siteurl>/procedures/osdb-[0-9]{4}/$` before review.
  An automated scenario (print-layout "First-page facts") requires that
  `siteurl` occur in published HTML only as the text of `span.page-url`.

`orgsyndb` already passes its environment to Hugo, so nothing in
`tools/` changes. `site/hugo.toml` gains one host, the loopback default,
so the site-build "Hugo configuration" requirement is restated to allow
exactly that value (D18).

**Wide tables.** The render hook marks the cells of the columns headed
`CAS`, `MW (g/mol)`, `mmol` and `Equiv` with `class="num"`. They stay on
one line and are right-aligned, and every other column wraps inside the
page.

Verified on a probe procedure with an eight-column table, long reagent
names, a 77-letter unbroken word and 40 steps:

- four A4 pages;
- every word inside the margins (45.4 to 549.9 pt on a 595.3 pt page);
- numbers intact;
- no step or row split across pages, and no page ending on a heading;
- zero warnings.

`overflow-wrap: anywhere` on every cell, including the numeric ones,
broke `15687-27-1` into `1568 / 7-27 / -1`.

**Browser fallback.** Browsers use the same stylesheet. Firefox 158,
printing through WebDriver BiDi `browsingContext.print`, gave A4, four pages, every word within the page,
no chrome, and the full `http://127.0.0.1:…` URL filled in by JS. It
ignored the `@page` margin boxes: no running header and no page numbers
from CSS. Firefox's own print-dialog headers and footers cover that.
Chromium is not installed, so its behaviour is unverified. Chromium
documents margin-box support from version 131, and this design uses no
`string-set`, which Chromium lacks.

*Rejected alternatives:*

- *`string-set` from the `h1`.* It works in WeasyPrint only. The literal
  per-page rule works wherever margin boxes do.
- *Headers written by JS.* WeasyPrint runs no JS.
- *A separate print output format per page.* Every template would exist
  twice.
- *Shrinking wide tables with `zoom` or `transform`.* Text becomes
  illegibly small, and WeasyPrint's support for both is partial.
- *The path alone unless `HUGO_PARAMS_SITEURL` is set.* This was this
  design's first version, and review rejected it: it does not meet brief
  §6.3's "full URL" on a fresh clone.
- *An internal host name in `hugo.toml`.* No such host exists yet, and
  committing a deployment's host name would put a site-specific
  identifier in a public repository. The loopback origin is generic.

### D12. How "no content clipped" is tested, and what that cannot show

The automated checks detect two failures: content pushed past the
margins, and a table row or numbered step split across pages. They do
not detect content hidden inside its own box. Acceptance evidence for
"nothing clipped" is therefore the orchestrator's raster review of page
images (task 9.5), supported by the checks below.

1. **Geometry.** `pdftotext -bbox` gives every word's box. Every `xMin`
   must be at least the left margin and every `xMax` at most the page
   width minus the right margin, with 1 pt tolerance, on every page.
   - Positive run: 45.4–549.9 pt.
   - Negative control: with `white-space: nowrap` on all cells, words
     reached 600.1 pt on a 595.3 pt page.

   Only the horizontal bounds are checked. Text in the page margins is
   legitimate (the margin-box header and footer). Paged flow moves
   overflowing content to the next page rather than below the bottom edge,
   so a vertical bound adds nothing.
2. **Content.** For each table cell and each Procedure `<li>` in the
   built HTML, its text, whitespace-stripped and NFKC-normalised, must
   occur in the whitespace-stripped `pdftotext -raw` text of a single
   page. This shows that the text was laid out on one page. It does not
   show that the text is visible.
3. **No clipping CSS.** The print-applicable stylesheets (`tokens.css`,
   `base.css`, `print.css`) declare:
   - no `overflow`, `overflow-x` or `overflow-y` of `hidden` or `clip`;
   - no `height` or `max-height` other than `auto` or `none`, except a
     `max-height` on a selector whose subject is `img`. A replaced image
     scales instead of being cut.

   That removes the only CSS route to hidden overflow. `screen.css` is
   exempt, because no printer loads it.

**What the checks miss (verified, by the reviewer and again here).** A
WeasyPrint 70.0 PDF of a page with
`<div style="height:1px; overflow:hidden">` around two paragraphs kept the
clipped words in `pdftotext -raw`. The word `HiddenClippedSentinel` had
the box 51.4–180.5 pt, inside the margins. Both checks 1 and 2 pass on
this clipped content. They also ignore non-text graphics: a cut-off SVG
or rule would pass. This negative control becomes a test,
`tests/fixtures/theme/clip-negative-control.html`. The test asserts that
checks 1 and 2 pass on it, recording the limit, and that check 3 would
reject its CSS.

*Rejected alternatives:*

- *Comparing against the source file.* Org and Markdown markup
  (`/italic/`, `H_{2}O`) would need re-implementing. The built HTML is
  what WeasyPrint saw.
- *Automated pixel comparison.* It would need a rendering of the
  "unclipped truth" to compare against, which does not exist
  independently of the renderer under test. The orchestrator's visual
  review of the page images covers what text extraction cannot.
- *Claiming that checks 1 and 2 prove "nothing clipped".* The negative
  control disproves it.

### D13. Samples

Six new samples, created with `tools/orgsyndb new` (Org by default,
`--md` for OSDB-0008), then filled. Timestamps are real Europe/Berlin
times of writing. `#+AI_MODEL` and `ai_model` name the writer's exact
model identifier. Authors are fictitious `X. Example` names. Every sample
has `status = "draft"`, the tag `sample-data`, at least one further tag
of its own, and a Summary sentence saying the quantities are not
experimentally verified.

| ID | Format | Product (formula, MW, CAS) | Reaction type | Precursors | Tags besides `sample-data` |
|---|---|---|---|---|---|
| OSDB-0003 | Org | isopentyl acetate (C7H14O2, 130.19, `123-92-2`), SMILES `CC(C)CCOC(C)=O`, `structure_image = "structures/osdb-0003.svg"` | esterification | — | `fischer-esterification`, `fragrance` |
| OSDB-0004 | Org, long | 4-acetylbiphenyl (C14H12O, 196.25, `92-91-1`), SMILES `CC(=O)c1ccc(cc1)-c1ccccc1` | cross-coupling | — | `suzuki-coupling`, `biphenyl` |
| OSDB-0005 | Org | 1-(biphenyl-4-yl)ethanol (C14H14O, 198.26, `3562-73-0`), SMILES `CC(O)c1ccc(cc1)-c1ccccc1` | reduction | `OSDB-0004` | `sodium-borohydride`, `biphenyl` |
| OSDB-0006 | Org | dibenzylideneacetone (C17H14O, 234.30, `538-58-9`), SMILES `O=C(/C=C/c1ccccc1)/C=C/c1ccccc1` | aldol-condensation | — | `claisen-schmidt` |
| OSDB-0007 | Org | ethyl (E)-cinnamate (C11H12O2, 176.21, `103-36-6`), SMILES `CCOC(=O)/C=C/c1ccccc1` | olefination | — | `wittig`, `cinnamate` |
| OSDB-0008 | Markdown, `md/procedures/OSDB-0008-cinnamic-acid.md` | (E)-cinnamic acid (C9H8O2, 148.16, `140-10-3`; not `621-82-9`, the unspecified-stereo entry), SMILES `OC(=O)/C=C/c1ccccc1`, by saponification of OSDB-0007's ester with aqueous NaOH in ethanol at reflux, then acidification with HCl, as in OSDB-0001 | hydrolysis | `OSDB-0007` | `saponification`, `cinnamate` |

Totals: 6 Org (OSDB-0001, 0003–0007) and 2 Markdown (OSDB-0002, 0008),
across seven reaction types (hydrolysis twice, acylation,
esterification, cross-coupling, reduction, aldol-condensation,
olefination). There are three two-step chains, which exercise precursor
and used-in links in both directions:

- OSDB-0001 → OSDB-0002 (exists, Org → Markdown);
- OSDB-0004 → OSDB-0005 (Org → Org);
- OSDB-0007 → OSDB-0008 (Org → Markdown).

No procedure is required to have both a precursor and a used-in link.
Brief §6.4 asks only for a chain of two or more steps, and acceptance
check 5 is about links resolving in both directions, which every chain
tests.

Reagents tables (`*` marks the limiting reagent; MW in g/mol; volumes from
standard densities). Solvents stay in the step text, as in the seeds:

| Sample | Reagent | CAS | MW | Amount | mmol | Equiv |
|---|---|---|---|---|---|---|
| 0003 | Isopentyl alcohol (3-methylbutan-1-ol)* | 123-51-3 | 88.15 | 4.41 g (5.44 mL) | 50.0 | 1.0 |
| 0003 | Acetic acid, glacial | 64-19-7 | 60.05 | 6.01 g (5.73 mL) | 100 | 2.0 |
| 0003 | Sulfuric acid, 96 % | 7664-93-9 | 98.08 | 0.5 mL | cat. | cat. |
| 0004 | 4′-Bromoacetophenone (1-(4-bromophenyl)ethan-1-one)* | 99-90-1 | 199.05 | 1.99 g | 10.0 | 1.0 |
| 0004 | Phenylboronic acid | 98-80-6 | 121.93 | 1.46 g | 12.0 | 1.2 |
| 0004 | Potassium carbonate, anhydrous | 584-08-7 | 138.21 | 2.76 g | 20.0 | 2.0 |
| 0004 | Tetra-n-butylammonium bromide | 1643-19-2 | 322.37 | 1.61 g | 5.00 | 0.5 |
| 0004 | Palladium(II) acetate | 3375-31-3 | 224.51 | 11.2 mg (0.5 mol %) | cat. | cat. |
| 0005 | 4-Acetylbiphenyl* | 92-91-1 | 196.25 | 0.981 g | 5.00 | 1.0 |
| 0005 | Sodium borohydride | 16940-66-2 | 37.83 | 0.114 g | 3.01 | 0.6 |
| 0006 | Benzaldehyde | 100-52-7 | 106.12 | 2.12 g (2.03 mL) | 20.0 | 2.0 |
| 0006 | Acetone* | 67-64-1 | 58.08 | 0.581 g (0.735 mL) | 10.0 | 1.0 |
| 0006 | Sodium hydroxide | 1310-73-2 | 40.00 | 2.00 g | 50.0 | 5.0 |
| 0007 | Benzaldehyde* | 100-52-7 | 106.12 | 0.531 g (0.509 mL) | 5.00 | 1.0 |
| 0007 | Ethyl (triphenylphosphoranylidene)acetate | 1099-45-2 | 348.38 | 2.09 g | 6.00 | 1.2 |
| 0008 | Ethyl (E)-cinnamate* | 103-36-6 | 176.21 | 0.529 g (0.504 mL) | 3.00 | 1.0 |
| 0008 | Sodium hydroxide | 1310-73-2 | 40.00 | 0.360 g | 9.00 | 3.0 |
| 0008 | Hydrochloric acid, 37 % (12.1 M) | 7647-01-0 | 36.46 | 1.00 mL | 12.1 | 4.0 |

Scales are the limiting reagent's mmol: `"50 mmol"`, `"10 mmol"`,
`"5 mmol"`, `"10 mmol"`, `"5 mmol"`, `"3 mmol"`. Suggested yields: 70, 85,
90, 85, 80 and 90 %.

The chain's masses are consistent:

- 0004 yields 1.67 g, more than the 0.981 g that 0005 uses.
- 0007 yields 0.705 g, more than the 0.529 g that 0008 uses.

How the numbers were checked:

- Every table above passes `tests/sample_support.quantity_violations`
  with the spec's atomic weights (run; no violation).
- Every CAS number passes the check digit, and resolves on PubChem to the
  intended compound when looked up as a name (PUG REST
  `compound/name/<CAS>/property/Title,MolecularFormula,MolecularWeight,IsomericSMILES`,
  queried 2026-10-20). PubChem's formulas and MWs agree with the table.
  A cross-reference listing (`xrefs/RN`) alone is not enough.
- My remembered `3562-73-1` for the alcohol failed the check digit.
  PubChem resolves `3562-73-0`.
- An earlier version of this design used 1-(biphenyl-4-yl)ethyl acetate
  as OSDB-0008, with `116651-08-2`. That number came only from a
  depositor cross-reference. It does not resolve on PubChem (HTTP 404),
  which knows the ester only as SCHEMBL10521081, without a registry
  number. Acceptance check 3 needs every sample findable by its CAS
  number, so the sample was replaced by (E)-cinnamic acid.

Chemistry choices:

- Benign textbook reactions, all from brief §6.4's list, plus a second
  saponification like the OSDB-0001 seed.
- Boc protection was dropped because di-tert-butyl dicarbonate is fatal
  if inhaled (H330).
- The Wittig is the solvent-free stabilised-ylide variant, with heptane
  (not hexane) for trituration.
- References cite *Vogel's Textbook of Practical Organic Chemistry*, 5th
  ed., as the seeds do. Two further sources may be added if the
  orchestrator confirms them in the "Review before archive" scenario;
  otherwise Vogel alone:
  - for OSDB-0004, Miyaura, N.; Suzuki, A. *Chem. Rev.* 1995, 95, 2457;
  - for OSDB-0006, Conard, C. R.; Dolliver, M. A. "Dibenzalacetone",
    *Org. Synth.* 1932, 12, 22.
- Literature melting or boiling points in Characterization must come from
  a source the orchestrator can check. Otherwise describe the
  measurement without a number.

**The long sample.** OSDB-0004 has:

- at least 15 numbered Procedure steps, each referring to a Note where
  useful, and at least 6 Notes;
- full Workup and Characterization (mp, ¹H NMR, ¹³C NMR, IR as text);
- reagent names and amounts long enough that the six-column table is
  wider than the A4 text block at its natural width. The names in the
  table above are written in full, and amounts may carry handling
  remarks such as "1.61 g (dried at 60 °C under vacuum)", starting with
  the mass.

Its PDF must run to at least three pages. The six columns are fixed by
the sample-procedures spec, so the width comes from cell content, not
extra columns.

*Rejected alternatives:*

- *The camphor sequence (isobornyl acetate → isoborneol → camphor →
  isoborneol).* It is textbook, but its oxidation step uses bleach in
  acetic acid, which liberates chlorine, and it repeats hydrolysis.
- *Ethyl cinnamate → cinnamic acid → methyl cinnamate.* A contrived round
  trip.
- *Extending the seed chain with a Fischer esterification to methyl
  salicylate.* This re-forms OSDB-0001's own starting material.

### D14. The SVG structure image

`site/static/structures/osdb-0003.svg` is hand-written (skeletal
isopentyl acetate):

- root `<svg xmlns="http://www.w3.org/2000/svg" viewBox="…" width height
  role="img" aria-labelledby="…">`;
- a `<title>` naming the compound and its SMILES;
- a full-size `<rect fill="#fff">`;
- a `<g stroke="#000" stroke-width="2" stroke-linecap="round"
  fill="none">` of `<line>` bonds, with a second offset line for C=O;
- `<text>` atom labels in `font-family="sans-serif"`, `fill="#000"`.

It contains no `<script>`, `<foreignObject>`, `<image>`, `<use>`, `href`
or `xlink:href`, no `style` with `url(`, and no attribute value starting
with `http:`, `https:` or `//` other than the `xmlns` namespace.

The page shows it as `<figure class="structure"><img src="/{{
.Params.structure_image }}" alt="Structure of <product name>"></figure>`
inside the body. Without `structure_image`, the page shows
`<figure class="structure structure--placeholder"><div
class="structure__slot">No structure image</div></figure>`, hidden in
print.

Verified: a probe drawn this way rendered cleanly in WeasyPrint (no
warning) and in Firefox.

*Rejected alternatives:*

- *An SVG with its own `prefers-color-scheme` style.* An image in a
  printout can still match `dark` in a browser and print white on white.
- *PNG.* It is not hand-writable, and blurs in print.

### D15. Running Pagefind searches in tests: optional Node

Tests run the real `public/pagefind/pagefind.js` under Node, as an
optional test-only tool:

- `tests/js/pagefind-query.mjs` (test code) imports a copy of
  `pagefind.js` renamed `.mjs` and calls `options({ basePath })`. It
  imports `site/assets/js/search-terms.js`, a classic script that sets
  `globalThis.OrgSynSearch`; Node loads it unchanged (verified).
- It reads a JSON list of requests (`term`, `filters`, `normalise`) on
  stdin, runs `search`, and writes the results to stdout as JSON: each
  result's `meta.id`, `meta.title` and `excerpt`, and `filters()`.
- The Python side serves the sandbox `public/` with a
  `ThreadingHTTPServer` on `127.0.0.1` in a thread. Pagefind fetches its
  index and WASM over HTTP; Node's `fetch` has no `file:`.
- Tests skip with the reason "node not found (optional; used only by the
  search tests)".
- Nothing in `tools/` or `check-deps` mentions Node.

Verified: Node 22.23.1 ran searches against a probe bundle through
`http.server`, including filter-only searches with a `null` term.

*Rejected alternatives:*

- *Decoding the index in Python.* It is feasible: the `.pf_index` files
  are gzip with a `pagefind_dcd` header around CBOR, and a 40-line probe
  decoder listed the words. But it would re-implement Pagefind's
  stemming, prefix and ranking rules, and so test the decoder rather
  than the search the site ships. The format is also undocumented.
- *A headless browser in the suite.* Firefox would become a test
  dependency, and BiDi scripting is far more code. It stays a manual
  review tool (task 9).

### D16. Org and Markdown output are indistinguishable

The proof is a twin fixture pair, `tests/fixtures/theme/OSDB-0904-twin.org`
and `OSDB-0905-twin.md`. They hold identical content in the two formats:

- every metadata field the panel shows, including `checked_by`,
  `precursors = ["OSDB-0001"]`, tags `sample-data` and `twin-check`;
- the same `date` and `lastmod`;
- all eight sections, with a table, ordered lists, italic, bold and
  `H_{2}O` / `H<sub>2</sub>O`.

Both are built in the sandbox. After every `OSDB-0904`/`osdb-0904` and
`OSDB-0905`/`osdb-0905` is replaced by a placeholder, the two pages must
be byte-identical. This held with the prototype theme (verified).

*Rejected alternatives:*

- *Comparing the two seeds' element skeletons.* Their content differs,
  so equality has to be weakened until it proves little.

### D17. Tests: layers and skips

| Layer | Needs | Skips when |
|---|---|---|
| Static source tests: contrast, CSS media split and print colours, SVG rules, sample set, render-hook and template text | Python | never |
| JS unit tests of `search-terms.js` | Node | `node` missing |
| Theme integration (HTML scans of a sandbox build) | change 2's builder (Emacs, bootstrapped `.emacs-batch/`, Hugo, cached Pagefind) | as change 2, by name |
| Search integration | builder plus Node | either missing |
| Print integration | builder plus WeasyPrint, `pdfinfo` and `pdftotext` | any missing ("pdftotext not found (poppler-utils)") |

Integration tests build once per test class (`setUpClass`), copying the
twin and quoted-title fixtures into the sandbox where a scenario needs
them. That keeps runtime near a dozen builds.

*Rejected alternatives:*

- *A fresh sandbox per test.* Each build is about 3 s plus export;
  dozens of scenarios would make the suite slow for no isolation gain,
  since scans are read-only.

### D18. Changes to inherited requirements

| Spec | Requirement | Change | Reason |
|---|---|---|---|
| site-build | Hugo configuration | adds `[minify.tdewolff.html] keepWhitespace = true` | D6: without it, metadata words are glued and CAS search fails (verified) |
| site-build | Hugo configuration | adds `[params] siteurl = "http://127.0.0.1:8000"`, and narrows "names no host" to allow exactly that value | D11: brief §6.3's full URL on the first printed page, by default |
| site-build | Minimal layout contract | same guarantees; the scenario now checks every procedure page | the old scenario named only OSDB-0001/0002 as pages with a body, and the new samples carry one too |
| build-script | pdf subcommand | same behaviour; the scenario expects one PDF per content file | it expected exactly the two seed PDFs |
| site-build | No fetches from other hosts | unchanged | the printed URL is text, which the rules do not cover (D11) |

## Conformance to inherited specs

- **site-build "Merged procedures section".** No subdirectory is added
  under `/procedures/` (D4). `site/content/procedures/_index.md` comes
  from the `content` mount, and `md/procedures/_index.md` is still
  filtered out.
- **site-build "No fetches from other hosts".**
  - Every stylesheet, script and image is local. Root-relative URLs are
    rewritten to relative ones.
  - No `@font-face` is used and no font file is published.
  - The inline `@page` rule has no `url()`.
  - The printed URL (`params.siteurl` or `HUGO_PARAMS_SITEURL`) appears
    only as the text of `span.page-url`, never in an attribute (D11).
- **site-build "Search index".** Only procedure pages carry
  `data-pagefind-body`. The search page and the lists do not.
- **sample-procedures.** The six samples satisfy "Sample marking",
  "Benign textbook chemistry", "Quantities agree" and "Samples validate
  and export cleanly" as written.
- **procedure-schema.** `structure_image = "structures/osdb-0003.svg"`
  matches "Structure image path". No new field is used.
- **org-export.** The Org samples set `:structure_image` on a
  custom-front-matter line before `:product`.

## Verification

Every run below was made on this machine on 2026-10-20, in throwaway
copies under the session scratchpad (`theme probe/`, a path with a
space), never in the repository. The prototype theme lived only there.

**Hugo 0.162.1:**

- Template lookup by kind, including `procedures/page.html`, and
  `layout = "x"` → `layouts/x.html`.
- `_partials/` and `_markup/render-table.html` with `.THead`/`.TBody`
  cells.
- Taxonomy titles from `_index.md`; term titles title-cased without a
  partial ("Sample-Data").
- Reverse links with `where … "intersect"`.
- `index site.Data.reaction_types .Name "label"`.
- Stable `sort`.
- `HUGO_PARAMS_SITEURL` overriding a configured `[params] siteurl`.
- CSS-string escaping in an inline `<style>`.
- `minify.tdewolff.html.keepWhitespace` shown by `hugo config`.
- An Org/Markdown twin pair byte-identical apart from the ID.

**Pagefind 1.5.2:**

- Filters captured outside the body.
- `hidden` and `display:none` text inside the body indexed.
- `data-pagefind-ignore` excluded.
- Meta values searchable and absent from excerpts.
- Filter values not searchable.
- `<ul>`-level filter text gets a trailing full stop.
- Words glued across minified `dt`/`dd`/`th`.
- Stemming (`hydrolysi`, `sampl`).
- The SMILES sweep (D7).
- `--include-characters` results (D7).
- Default UI options, found by grep.
- The UI driven in headless Firefox over WebDriver BiDi: filter labels
  and counts, AND within a group, `processTerm` and `processResult`.

**WeasyPrint 70.0:**

- `@page` size and margins, `@top-left`/`@top-right` literals, and
  `counter(page)`/`counter(pages)`.
- `media="screen"` links skipped.
- Warnings listed in D2, and none after the split.
- Table wrapping, with `.num` intact.
- The bbox and raw-text checks, including the negative control.
- No page ending on a heading, and no split step or row.
- An SVG image.
- The hidden-overflow negative control (D12): clipped words stay in the
  text layer with in-margin boxes.
- `pdfinfo` reports `595.276 x 841.89 pts (A4)`.

**Firefox 158 (headless):**

- Screenshots at 1100 px and 390 px, light and dark.
- Print through BiDi `browsingContext.print`: A4, URL from JS, no
  margin-box header or footer.
- `firefox --screenshot` alone captures the search page before results
  render, so result screenshots need the BiDi route or a real browser.

**PubChem PUG REST:** formulas, MWs and registry numbers for every sample
compound and reagent (D13).

**Unverified:**

- Chromium print: not installed. Margin boxes are expected from
  Chromium 131, per its release notes.
- Layout on a real phone: only Firefox at 390 px was checked.
- The clipboard fallback on a plain-`http:` internal host.
- Screen-reader behaviour of the Pagefind UI.
- The final colours, if the implementer changes the D3 values. The
  contrast test decides.
- The two non-Vogel citations, left to the orchestrator's review.

## Risks / Trade-offs

- [Searchable meta and the tokeniser are observed behaviour of
  Pagefind 1.5.2, not documented guarantees.] → The binary is pinned by
  hash, and the Node search tests fail if a pin bump changes either.
- [`keepWhitespace` makes HTML slightly larger.] → A few hundred bytes
  per page. Correct search words matter more.
- [Two values in one Pagefind filter group are ANDed.] → Single-valued
  groups (reaction type, status) then give no results. Documented; the
  taxonomy pages give single-term browsing without the UI.
- [Firefox printouts lack running headers.] → The brief accepts browser
  print as "acceptable". The batch PDFs are the reference output.
- [Search tests skip without Node, and PDF tests without poppler.] → The
  static scans still check that the searchable content and filter
  attributes are present. Both tools are on the owner's machine.
- [Batch PDFs print `http://127.0.0.1:8000/…` unless
  `HUGO_PARAMS_SITEURL` is set, which is wrong for a deployment or for
  another `serve --port`.] → Documented. Browser printouts always show
  the address bar's URL.
- [Hidden overflow is not caught by any automated check (D12).] → The
  static CSS rule removes the means, and the raster review is the
  acceptance evidence.

## Open Questions

- Should term pages link to the search page with their filter preset,
  using `triggerFilters`? Left out: the default UI applies filters only
  to a typed term (D5).
- Should OR semantics within a filter group be offered by a custom UI
  later? Left for a future change.
