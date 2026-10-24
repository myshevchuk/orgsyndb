## Why

Changes 1 and 2 (`add-procedure-schema`, `add-build-pipeline`, both
archived) built the schema, the validator and a pipeline that exports,
validates, builds, indexes and prints. The pipeline's layouts are minimal
on purpose: they emit one bare HTML page per procedure and nothing a reader
can use. This change is the site itself. It covers brief §6 in full and
acceptance checks 2, 3, 4, 5 and 7:

- a custom theme;
- search with filters;
- precursor and used-in links;
- the sample banner;
- a print stylesheet for WeasyPrint and the browsers;
- the remaining sample procedures.

## What Changes

- Replace the minimal layouts with a custom theme written from scratch in
  `site/layouts/`, with no third-party theme, CSS or JS framework and no
  web fonts. The pages are:
  - home: intro, search form, recent procedures, and browsing by reaction
    type and tag;
  - procedure pages: ID, status badge, title, metadata panel, structure
    image or placeholder, body, and a Print / Save as PDF button;
  - two all-procedures lists, `/procedures/` (by ID) and
    `/procedures-by-date/` (newest first), which link to each other and
    need no JS;
  - taxonomy and term pages for reaction types (with vocabulary labels),
    tags and authors;
  - a search page.
- Add precursor links and computed "used in" reverse links. Add the sample
  banner "Sample data — quantities not experimentally verified." on every
  procedure tagged `sample-data`, on screen and in print.
- Add CSS under `site/assets/css/`, built with Hugo's standard-build
  pipes (`resources.Get`, `resources.Concat`, `minify`, `fingerprint`)
  into three stylesheets:
  - a base sheet for all media;
  - a screen sheet (`media="screen"`), which alone holds the
    `prefers-color-scheme: dark` tokens;
  - a print sheet (`media="print"`).

  Colour tokens are CSS custom properties whose contrast pairs are tested.
  System font stacks only. Body width is about 70ch. Every Markdown table
  is wrapped by a render hook in its own horizontal scroll container, and
  numeric Reagents columns are marked so that they never wrap.
- Add vanilla JS under `site/assets/js/` for the print button, the SMILES
  copy button, the full URL on browser printouts, and the search glue.
- Search uses Pagefind's default UI (`pagefind-ui.js`/`.css`) from the
  locally built bundle:
  - Filters are `reaction type` (vocabulary label), `tag`, `status` and
    `author`.
  - The metadata panel sits inside the indexed body, so product name,
    CAS number, tags and the other metadata are searchable. Header,
    banner, navigation and footer stay outside it.
  - SMILES substring search is a suffix index held in a Pagefind meta
    field, together with a query normalisation in the UI's `processTerm`.
    It was verified exact on 611 substring queries with the pinned
    binary.
  - `site/hugo.toml` gains
    `[minify.tdewolff.html] keepWhitespace = true`, because the minifier
    otherwise glues label and value into one search word
    (`cas50782smiles…`, verified).
- Add a print stylesheet that WeasyPrint 70.0 renders without a single
  warning:
  - A4 pages with margins;
  - a running header carrying the procedure's ID and title, from a
    per-page inline `@page` rule, and "Page N of M" footers;
  - black on white, with navigation and buttons hidden;
  - the full URL, ID, status and last-modified date on the first page;
  - no page break after a heading or inside a table row or numbered step;
  - wide tables wrap inside the page, and no print-applicable CSS can
    hide overflow.

  The printed URL is `params.siteurl` plus the page path. `site/hugo.toml`
  sets `siteurl` to `http://127.0.0.1:8000`, the `serve` origin, and the
  environment variable `HUGO_PARAMS_SITEURL` overrides it for an internal
  host. Browser printouts use `location.href`. The URL is plain text,
  never a fetched resource.
- Add six samples, reaching 6 Org and 2 Markdown procedures across seven
  reaction types:
  - OSDB-0003, isopentyl acetate by Fischer esterification (Org), with
    the hand-written SVG `site/static/structures/osdb-0003.svg`;
  - OSDB-0004, 4-acetylbiphenyl by Suzuki coupling (Org), the long sample;
  - OSDB-0005, NaBH₄ reduction of OSDB-0004's product (Org);
  - OSDB-0006, dibenzylideneacetone by Claisen–Schmidt condensation (Org);
  - OSDB-0007, ethyl cinnamate by Wittig olefination (Org);
  - OSDB-0008, (E)-cinnamic acid by saponification of OSDB-0007's ester
    (Markdown).

  With the seeds' OSDB-0001 → OSDB-0002, the precursor chains are
  OSDB-0004 → OSDB-0005 and OSDB-0007 → OSDB-0008. Every CAS number
  passes the check-digit rule and resolves to its compound on PubChem.
- Add tests:
  - stdlib HTML scanning of a sandbox build, covering pages, links in both
    directions, taxonomy listings, filter and meta attributes, the
    banner, no remote fetches, no web fonts and no JS dependence;
  - an Org/Markdown twin fixture pair that must render identically apart
    from its ID;
  - token contrast;
  - the SVG;
  - PDF checks with `pdfinfo`/`pdftotext`: A4, header and footer on
    every page, first-page facts, no chrome, no page ending on a heading,
    no split step or row, every word inside the margins, every table cell
    present, and warning-free rendering;
  - real Pagefind searches, through an optional, test-only Node helper
    that skips when `node` is absent. Node never becomes a build
    dependency.

## Capabilities

### New Capabilities

- `site-theme`: the custom theme. Covers its files and constraints, the
  page shell, stylesheets and colour tokens, tables and responsiveness,
  the procedure page and its metadata panel, precursor and used-in links,
  the sample banner, structure images, the lists and their sorting, the
  home page, taxonomy pages, content without JS, and Org/Markdown parity.
- `site-search`: the search page and what Pagefind indexes. Covers the
  default UI and its no-JS fallback, the indexed content, filters, result
  metadata, the SMILES substring index and query normalisation, verified
  search behaviour, and keeping Node optional.
- `print-layout`: printing and the PDFs. Covers the A4 page box, running
  header and footer, black on white, hidden chrome, first-page facts and
  the site-URL hook, break control, no clipping, warning-free WeasyPrint
  rendering, and the browser-print fallback.

### Modified Capabilities

- `site-build`:
  - "Hugo configuration" gains the minifier's `keepWhitespace`. Without
    it, Pagefind indexes `<dt>CAS</dt><dd>50-78-2</dd>` as one word, and
    CAS and product-name search fails (verified). It also gains
    `[params] siteurl = "http://127.0.0.1:8000"`, and its "names no host"
    rule now allows exactly that loopback value, so that PDFs carry the
    full URL brief §6.3 requires.
  - "No fetches from other hosts" is unchanged: the printed URL is text
    in a `span`, which its attribute, `url()` and `@import` rules do not
    cover.
  - "Minimal layout contract" keeps every guarantee. Its scenario named
    the two seed pages as the only pages with an indexed body, which the
    new samples break; it now covers every procedure page.
- `build-script`: "pdf subcommand" keeps its behaviour. Its scenario
  expected exactly the two seed PDFs, which the new samples break; it now
  expects one PDF per procedure content file.
- `sample-procedures`: adds the requirement "Theme sample set" (the six
  new samples, their chains, the structure image and the long sample). The
  existing requirements already apply to every procedure tagged
  `sample-data` and are unchanged.

`procedure-schema`, `procedure-validation` and `org-export` are unchanged.
No new front-matter field is introduced.

## Impact

- New files:
  - `site/layouts/home.html`, `section.html`, `taxonomy.html`,
    `term.html`, `page.html`, `search.html`, `procedures-by-date.html`,
    `procedures/page.html`, `_partials/*.html` and
    `_markup/render-table.html`;
  - `site/assets/css/{tokens,base,screen,print}.css` and
    `site/assets/js/{site,search-terms,search}.js`;
  - `site/content/search.md`, `procedures-by-date.md`,
    `procedures/_index.md` and `reaction_types/_index.md`;
  - `site/static/structures/osdb-0003.svg`;
  - five Org samples in `org/procedures/` and one Markdown sample in
    `md/procedures/`;
  - fixtures under `tests/fixtures/theme/` (Org/Markdown twins, a quoted
    title, and the clipping negative control), the test-only
    `tests/js/pagefind-query.mjs`, and `tests/test_theme_*.py`,
    `tests/test_search_*.py` and `tests/test_print_*.py`.
- Changed files:
  - `site/hugo.toml` (two tables: `[minify.tdewolff.html]` and `[params]`);
  - `site/layouts/baseof.html`, rewritten but still containing a literal
    `<head>`, which the "Remote stylesheet fails the job" test edits;
  - `site/layouts/list.html` and `single.html`, removed in favour of the
    kind-specific templates;
  - `tests/pipeline_support.py`, `tests/test_build_integration.py` and
    `tests/test_samples.py`.
- Unchanged: `tools/` (`build.fish`, `pipeline.py`, `export.el`,
  `validate.py`), `templates/`, `.gitignore`. The `pdf` subcommand
  already renders whatever `public/` holds.
- Dependencies:
  - No new runtime dependency.
  - Test-only and optional, each skipping by name when absent: `node`
    (search tests; verified with Node 22.23.1) and `pdfinfo`/`pdftotext`
    (poppler-utils; PDF tests).
  - Firefox (headless) serves only the orchestrator's visual review.
- Facts the doc writer needs. The final orchestrator task hands these
  over; no relay stage writes these documents.
  - `README.md`:
    - The site's pages and URLs: `/`, `/procedures/` (by ID),
      `/procedures-by-date/` (newest first), `/reaction_types/`,
      `/tags/`, `/authors/` and their term pages, `/search/`.
    - Search works only through a web server (`tools/build.fish serve`,
      or Caddy), never from `file:` URLs. Without JS, the search page
      points to the browse pages.
    - What search finds:
      - product name, CAS number typed with its hyphens, any part of the
        SMILES string (case-insensitive, at least three characters
        recommended), a tag, the ID, and words of the text;
      - the filters reaction type, tag, status and author narrow a typed
        search;
      - two values ticked in one filter group must both match, so two
        reaction types give no result;
      - punctuation inside a search word is ignored, so `50-78-2` and
        `CC(=O)O` work as typed.
    - Printing from the browser uses the same print stylesheet. Firefox
      prints no running header or page numbers from the stylesheet;
      enable them in Firefox's print dialog. WeasyPrint PDFs from
      `tools/build.fish pdf` carry the ID and title on every page and
      "Page N of M".
    - PDFs from `tools/build.fish pdf` print the full URL
      `http://127.0.0.1:8000/procedures/<slug>/` on the first page by
      default, the `serve` address. Setting
      `HUGO_PARAMS_SITEURL=https://<internal host>` when running `pdf` or
      `build` prints that host instead; set it too when serving on another
      `--port`. Browser printouts always show the address bar's URL.
    - A text search of `public/` for `http://` finds that URL once per
      procedure page. It is plain text, not a fetched resource.
    - The SMILES copy button needs `https:` or `127.0.0.1`. On plain
      `http:` hosts it selects the SMILES text for Ctrl-C instead.
    - The build log line now reads `validated 14 files: 0 errors,
      0 warnings` (6 Org sources, their 6 exports, 2 Markdown files).
    - Optional test tools: `node` for the search tests and `pdfinfo` and
      `pdftotext` (`sudo dnf install poppler-utils`) for the PDF tests.
      Both skip when absent, and neither is needed to build.
  - `docs/AUTHORING.md` (co-worker):
    - how each front-matter field appears in the page's details panel;
    - `precursors` creates a link to the precursor and a "Used in" link
      back on its page;
    - the tag `sample-data` puts the sample banner on screen and on
      paper, so never use it on a real procedure;
    - a structure picture is an SVG or PNG placed in
      `site/static/structures/` and named in `structure_image`, for
      example `structures/osdb-0012.svg`; without one the page shows an
      empty slot, which is not printed;
    - keep the six Reagents columns; long tables scroll sideways on
      screen and wrap on paper;
    - the Print / Save as PDF button.
  - `docs/AUTHORING-ORG.org` (owner):
    - the same facts in Org terms:
      `#+HUGO_CUSTOM_FRONT_MATTER: :structure_image "structures/osdb-NNNN.svg"`,
      tags on `#+HUGO_TAGS`, and the `sample-data` banner rule;
    - the SVG convention: black strokes on a white background rectangle,
      a `<title>`, and no external references.
