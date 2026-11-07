## MODIFIED Requirements

### Requirement: Home page
The home page's `main` SHALL contain, in this order:
- `div.home-intro`, holding the `h1` `Synthetic procedures` and a `p.lede` with the text `The group's procedures, written in Org or Markdown to one schema.`;
- in a build with `params.lab` (site-build "Hugo configuration"), `section.home-lab`, holding the `h2` `Lab at a glance`, an `iframe.home-lab-frame` whose `src` is `/lab/summary/` and whose `title` is `Lab at a glance`, and a `p` with a link to `/lab/` whose text is `Open the lab overview`; without `params.lab` the page has no `section.home-lab`;
- `div.home-layout`, holding, in this order:
  - `section.home-recent`, with the `h2` `Recently updated`, then an `ol.recent-list` with one `li` per procedure for the first five published procedures, or all when there are fewer, ordered by `lastmod` as an instant, newest first, and by `id` ascending for equal instants. Each `li` holds an `a` linking the procedure page whose text is `<id> <title>`, then `<time datetime="<RFC 3339 lastmod>">YYYY-MM-DD</time>`. After the list, a `p` links `/procedures/?sort=modified` with the text `All procedures, recently updated first`;
  - `section.home-unchecked`, only when some published procedure has the status `draft`, with the `h2` `Not yet checked`, then an `ol.unchecked-list` with one `li` per draft for the first five drafts by `id` ascending, or all when there are fewer: the drafts the catalogue lists first under `/procedures/?status=draft`. Each `li` holds an `a` linking the procedure page whose text is `<id> <title>`, then `<time datetime="<RFC 3339 date>">YYYY-MM-DD</time>` of its creation. After the list, a `p` holds a link to `/procedures/?status=draft` with the text `All draft procedures`, then ` ` and a `span.count` reading `(<n>)`, `n` the number of drafts;
  - `section.home-browse`, with the `h2` `Browse`, then a `ul.browse-list` whose `li` entries hold, in this order, a link and then ` ` and a `span.count` reading `(<n>)`: `All procedures` to `/procedures/`, `n` the number of published procedures; `Reaction types` to `/reaction_types/`, `Tags` to `/tags/` and `Authors` to `/authors/`, each `n` the number of terms of that taxonomy in use; `Compounds` to `/compounds/`, `n` the number of compounds in the registry; `Sequences` to `/sequences/`, `n` the number of published sequences.

The counts are computed from the published procedures and the registry, and written with the site language's digit grouping. The home page's `main` holds no form, no `input` and no procedure table. On screen, from 70rem up, the recent and unchecked lists form the first column and the browse list the second. The frame takes the content's width and a fixed height that shows the summary whole, taller on narrow screens.

#### Scenario: Home page content
- **WHEN** a test scans `public/index.html` of a theme build that adds the catalogue fixtures to the test collection, in locale `en`
- **THEN** the `h1` is `Synthetic procedures`, and the recent list holds the first five procedures in the computed order, each ID once, with the stated link texts and dates, and two fixtures whose `lastmod` is the same instant are ordered by ID
- **AND** the unchecked list holds the first five drafts by ID with their creation dates, and its link reads the number of drafts computed from the published content files
- **AND** the browse list has the six entries in order, with the stated targets, and counts equal to those computed from the published content files and the registry
- **AND** `main` has the links to `/procedures/?sort=modified` and `/procedures/?status=draft`, and no `form`, `input` or `table`

#### Scenario: Nothing waits for a check
- **WHEN** a test scans `public/index.html` of a theme build of a collection whose procedures are all `checked`
- **THEN** it has no `section.home-unchecked` and no link to `/procedures/?status=draft`

#### Scenario: The lab's summary on the home page
- **WHEN** a test scans `public/index.html` of a theme build of the test collection with `ORGSYNDB_LAB=true`, and of one without
- **THEN** the first has, between `div.home-intro` and `div.home-layout`, a `section.home-lab` with its `h2`, its `iframe` and its link to `/lab/`, and no `script` element beyond those of other home pages; the second has no `section.home-lab` and no `iframe`
