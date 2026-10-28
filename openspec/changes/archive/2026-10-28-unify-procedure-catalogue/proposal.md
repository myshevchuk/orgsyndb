## Why

The site has three overlapping ways to look for a procedure. `/procedures/`
and `/procedures-by-date/` list every procedure, each with its own order,
a reaction-type and a status select that hide table rows in place, and a
search field that leaves the list for `/search/`. `/search/` runs
Pagefind's own interface, which lists nothing until a term is typed, shows
five results at a time and combines filter values in one group with AND,
so two reaction types give no results. Term pages show a bare table, and
the home page repeats a procedure table and the full reaction-type and
tag lists. A reader who wants "draft procedures about cinnamates, newest
first" has no single place to ask for it, and the search box behaves
differently depending on which page it sits on.

## What Changes

- **One catalogue.** `/procedures/` becomes the collection browser: with no
  query or filters it lists every published procedure, and a query
  searches metadata and body text through the existing Pagefind index.
  Query, facets and sort apply to one result set. **BREAKING** `/search/`
  and `/procedures-by-date/` are removed, with their content files,
  layouts, scripts and links; no redirects.
- **Facets.** Multi-select reaction type, status, tag and author facets:
  OR within a facet, AND across facets, per-value counts that leave out
  the facet's own selections, removable selections, Clear all, and a
  match count announced to assistive technology.
- **State in the address.** `q`, repeated `type`, `status`, `tag` and
  `author`, `sort` and `view`, with machine values (reaction-type slugs,
  status literals, term keys). Reload, sharing and Back/Forward restore
  controls, results, counts and order; typing is coalesced into one
  history entry; parameters that cannot be applied are reported and
  dropped from the address.
- **Term pages share the catalogue.** Reaction-type, tag and author term
  pages stay static lists of exactly their procedures and gain the same
  controls, with the term as a fixed, labelled scope and a Browse all
  procedures link that carries the remaining state. Taxonomy pages stay
  compact directories.
- **Search integration.** The catalogue uses Pagefind's JavaScript API.
  Each procedure page gives Pagefind an `id` filter and an `id` sort key,
  from which the catalogue maps result pages to procedure IDs without
  loading result fragments. **BREAKING** The status, reaction-type, tag
  and author Pagefind filters, the Pagefind UI and `cleanResult` are
  removed; the ID, product, CAS, tag, body-word and SMILES matching
  contracts are unchanged.
- **Header search and navigation.** Every page outside the catalogue has
  one compact search form in the header, submitting `q` to
  `/procedures/`. The navigation is Procedures, Reaction types and Help;
  the tag and author directories stay, reached from the catalogue, the
  home page and metadata links.
- **Home page.** A short introduction, one Recently updated list (last
  modified first, ID breaking ties), and a browse list with collection
  totals and shortcuts, including Draft procedures. The large search form,
  the procedure table and the full term lists go.
- **Table and Details view.** Columns ID, Procedure, Reaction type,
  Status and Modified; sorts by ID, title, created, modified and, during
  a query, relevance. An optional Details view adds product name,
  formula, molecular weight, CAS, yield, created date and an existing
  structure image to the same rows.

## Capabilities

### New Capabilities

- `site-catalogue`: the catalogue page and its term-page form, row
  records, controls, address state, facet matching and counts, sort
  orders, the Details view, the fixed scope, the browser behaviour and
  the core script's functions.

### Modified Capabilities

- `site-theme`: the page shell (navigation, header search), stylesheets,
  colour tokens (no Pagefind UI variables), layout scenarios, the home
  page, taxonomy and term pages, the JavaScript rule; the two procedure
  lists are removed.
- `site-search`: the search page is removed; the Pagefind `id` filter and
  sort key replace the four label filters; result metadata and query
  normalisation lose `cleanResult`; the catalogue's text search is
  defined; findability is checked through it.
- `localization`: German interface strings for the catalogue, home page
  and navigation; the German search-index scenario; the reaction-type
  lists that follow the German labels; the home-page count of the
  partial-translation scenario.
- `site-build`: a built site works under a path prefix such as
  `/orgsyndb/`.
- `demo-site`: the published-demo check searches in the catalogue.
- `print-layout`: the PDF check for printed navigation follows the new
  navigation texts.

## Impact

- Layouts: `site/layouts/{home,section,term,taxonomy,baseof}.html`;
  partials `site-header`, `procedure-table`, `procedure-header`,
  `procedure-meta`; new catalogue partials; removed `search.html`,
  `procedures-by-date.html`, `list-tools`, `list-filter-script` and
  `sort-links`.
- Content: removed `site/content/search.md` and
  `site/content/procedures-by-date.md`.
- Scripts: new `catalogue-core.js` and `catalogue.js`; `search-terms.js`
  keeps `normaliseTerm` only; removed `search.js` and `list-filter.js`.
- Styles: `base.css`, `screen.css`, `print.css`; both i18n files.
- Tests: the theme, search, localization, JavaScript and static tests
  that assert the removed pages and filters are replaced; new Node tests
  of the core functions, real-index tests of the catalogue search, HTML
  scans of the catalogue, term and home pages, a path-prefix scan, and
  catalogue fixtures with mixed statuses, several authors and tags,
  missing optional fields, date ties and a query with no result.
- Docs: `README.md` ("Use the site", the introduction and search
  description).
