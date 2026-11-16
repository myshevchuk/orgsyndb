## MODIFIED Requirements

### Requirement: Page shell
Every HTML page the theme renders SHALL contain, in this order:
- a skip link `a.skip-link` with `href="#main"`;
- a `header.site-header` holding:
  - `a.site-title`, linking `/` with the text `OrgSynDB`;
  - `form.site-search` with `role="search"` and `method="get"`, holding one `input` with `type="search"` and `name="q"`, and a `button` with `type="submit"` and the text `Search`. On the catalogue, the term pages and `/general-procedures/` it is the catalogue's search form, with the `action`, attributes and texts that site-catalogue "Catalogue controls" gives. On every other page its `action` resolves to `/procedures/`, and its input carries `aria-label="Search procedures"` and the placeholder `Product, CAS or SMILES`;
  - the navigation (Navigation), the header's only `nav`;
- exactly one `main` element with `id="main"`;
- a `footer.site-footer` whose text is `OrgSynDB · internal procedures · built <time>`, where `<time>` is a `time` element whose `datetime` is the time the site was built, as an RFC 3339 date-time, and whose text is that time as `YYYY-MM-DD HH:MM`. Every page of one build shows the same time.

Every page has exactly one `input` with `name="q"`: the header's.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

Each page's head has a `<meta name="viewport" content="width=device-width, initial-scale=1">` and a `<meta name="color-scheme" content="light dark">`. The site-build "Minimal layout contract" elements also stay: `lang`, `charset` and `<title>`.

Headings follow these rules:
- Each page has exactly one `h1`.
- No heading is more than one level deeper than the heading before it.
- The `<title>` is the page's display title followed by ` | OrgSynDB`, except on the home page, whose title is `OrgSynDB`. The display title is the vocabulary label on a reaction-type term page, the tag itself on a tag term page, the interface string named by the page's `title_key` where it has one, and the page title otherwise.

#### Scenario: Shell on every page
- **WHEN** a test scans every HTML file under `public/` except files under `public/pagefind/`, after a theme build in locale `en`
- **THEN** each has the skip link, the site header holding the site title, `form.site-search` and exactly one `nav`, one `main#main`, the footer text with its `time`, the same on every page, both `meta` elements, exactly one `h1`, no heading-level jump greater than one, and exactly one `input[name=q]`, the header's
- **AND** on every page except `/procedures/`, `/general-procedures/` and the term pages the form's `action` resolves to `/procedures/` and its input has the stated `aria-label` and placeholder

#### Scenario: Term titles use labels and tags
- **WHEN** a test reads `public/reaction_types/aldol-condensation/index.html` and `public/tags/sample-data/index.html` after a theme build in locale `en`
- **THEN** their `h1` texts are `Aldol condensation` and `sample-data`, and their `<title>` texts are `Aldol condensation | OrgSynDB` and `sample-data | OrgSynDB`

### Requirement: Metadata panel
The metadata panel SHALL be a `dl.metadata`, the first element of the details wrapper at the start of `article.procedure`. It holds one `dt`/`dd` pair per field, with these labels in this order, each pair present only when the field is set. The panel repeats nothing the procedure header shows: the ID is in the header's ID line, the scale and yields are its key facts, and the checkers of a checked procedure are its sign-off. A compound's name is its shown name (localization "German compound names").
- `Product`, or `Products` when the procedure has several: one `a.compound` per product, in `products` order, linking the substance's lab page `/lab/registry/substances/<key>/` (lab-registry "Registry pages") with the compound's name as text, each followed by its note of compound-fields "Values beside compound links" when it has one, joined by `, `;
- `Formula`, only when the procedure has one product: the compound's formula, where each digit run is wrapped in `<sub>`;
- `MW`, likewise, as `<mw> g/mol`;
- `CAS`, likewise, when the compound sets it;
- `SMILES`, likewise, as a `<code data-smiles>` with the string, followed by `button.copy-button` with `type="button"`, `data-copy-smiles`, the text `Copy` and `hidden`;
- `Starting materials`: one `a.compound` per entry of `substrates`, in its order, linking the compound's page with its name as text, each followed by its note as for `Product`, joined by `, `;
- `Reaction type`, as a link to the term page whose text is the vocabulary label;
- `Tags`, as one link per tag to its term page, with the tag as text;
- `Authors`, as one link per author to the author's term page, with the account's name as text (procedure-authors "Author data for the site");
- `Checked by`, as the names joined by `, `, not linked, only when the status is not `checked`;
- each procedure field the collection declares (procedure-fields "Procedure field declarations") that the procedure sets, in declared order, labelled with the field's shown label (procedure-fields "Procedure field data"), its value written as compound-fields "Field display" writes a value;
- `Created`, as `<time datetime="<RFC 3339 date>">YYYY-MM-DD HH:MM</time>`;
- `Modified`, the same for `lastmod`;
- `Precursors`, as in the requirement "Precursor and used-in links";
- `Used in`, as in the same requirement;
- `Sequences`, as synthesis-sequences "Sequences beside procedures and compounds" states.

Whitespace separates every `</dt>` from the following `<dd>` in the published HTML.

#### Scenario: Panel of the Markdown seed
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build
- **THEN** the `dt` texts are, in order, `Product`, `Formula`, `MW`, `CAS`, `SMILES`, `Starting materials`, `Reaction type`, `Tags`, `Authors`, `Lab notebook`, `Project`, `Working time`, `Inert atmosphere`, `Created`, `Modified`, `Precursors` and `Sequences`
- **AND** the values include an `a.compound` to `/lab/registry/substances/acetylsalicylic-acid/` with the text `Acetylsalicylic acid`, `C9H8O4` with three `<sub>` elements, `180.16 g/mol`, `50-78-2`, `CC(=O)Oc1ccccc1C(=O)O` in `code[data-smiles]`, `a.compound` links `Salicylic acid` and `Acetic anhydride` under `Starting materials`, a link with text `Acylation`, links `sample-data` and `acetylation`, links `Katrin Lehmann` and `Anna Schmidt` to `/authors/klehmann/` and `/authors/aschmidt/`, the texts `AE-1/2`, `Teaching › First-year practical`, `2.5 h` and `No`, and `<time datetime="2026-10-19T23:46:11+02:00">`

#### Scenario: Panel labels follow the canonical order on every page
- **WHEN** a test scans every procedure page after a theme build
- **THEN** each page's `dt` texts are a subsequence of the canonical label list in its order, the declared procedure fields' shown labels standing in it, in declared order, between `Checked by` and `Created`; they include every label whose field the content file sets, except `Checked by` where the status is `checked`, with `Product` for one product and `Products` for several, and `Formula`, `MW` and `SMILES` exactly when there is one product, no page has an `ID`, `Scale` or `Yield` label, and whitespace follows every `</dt>`

#### Scenario: A product named like its procedure is linked
- **WHEN** a test scans `procedures/osdb-0001/index.html`, whose title and product name are both `Salicylic acid`, after a theme build
- **THEN** its panel's `Product` pair holds one `a.compound` to `/lab/registry/substances/salicylic-acid/` with the text `Salicylic acid`

#### Scenario: Panel of a procedure with two products
- **WHEN** a test scans `procedures/osdb-0907/index.html` after the two-product build of the requirement "Procedure page structure"
- **THEN** its panel has a `Products` pair with the `a.compound` links `trans-Stilbene` and `cis-Stilbene`, in that order, and no `Product`, `Formula`, `MW`, `CAS` or `SMILES` pair

#### Scenario: Declared fields in the German panel
- **WHEN** a test reads `procedures/osdb-0002/index.html` of a build of the test collection in locale `de`
- **THEN** its panel holds the pairs `Laborjournal` `AE-1/2`, `Projekt` `Lehre › Grundpraktikum`, `Arbeitszeit` `2,5 h` and `Schutzgas` `Nein`, in this order, between the `Autoren` pair and the `Erstellt` pair

### Requirement: Home page
The home page's `main` SHALL contain, in this order:
- `div.home-intro`, holding the `h1` `Synthetic procedures` and a `p.lede` with the text `The group's procedures, written in Org or Markdown to one schema.`;
- in a build with `params.lab` (site-build "Hugo configuration"), `section.home-lab`, holding the `h2` `Lab at a glance`, an `iframe.home-lab-frame` whose `src` is `/lab/summary/` and whose `title` is `Lab at a glance`, and a `p` with a link to `/lab/` whose text is `Open the lab overview`; without `params.lab` the page has no `section.home-lab`;
- `div.home-layout`, holding, in this order:
  - `section.home-recent`, with the `h2` `Recently updated`, then an `ol.recent-list` with one `li` per procedure for the first five published procedures, or all when there are fewer, ordered by `lastmod` as an instant, newest first, and by `id` ascending for equal instants. Each `li` holds an `a` linking the procedure page whose text is `<id> <title>`, then `<time datetime="<RFC 3339 lastmod>">YYYY-MM-DD</time>`. After the list, a `p` links `/procedures/?sort=modified` with the text `All procedures, recently updated first`;
  - `section.home-unchecked`, only when some published procedure has the status `draft`, with the `h2` `Not yet checked`, then an `ol.unchecked-list` with one `li` per draft for the first five drafts by `id` ascending, or all when there are fewer: the drafts the catalogue lists first under `/procedures/?status=draft`. Each `li` holds an `a` linking the procedure page whose text is `<id> <title>`, then `<time datetime="<RFC 3339 date>">YYYY-MM-DD</time>` of its creation. After the list, a `p` holds a link to `/procedures/?status=draft` with the text `All draft procedures`, then ` ` and a `span.count` reading `(<n>)`, `n` the number of drafts;
  - `section.home-browse`, with the `h2` `Browse`, then a `ul.browse-list` whose `li` entries hold, in this order, a link and then ` ` and a `span.count` reading `(<n>)`: `All procedures` to `/procedures/`, `n` the number of published procedures; `Reaction types` to `/reaction_types/`, `Tags` to `/tags/` and `Authors` to `/authors/`, each `n` the number of terms of that taxonomy in use; `Substances` to the lab's substance list `/lab/registry/`, `n` the number of substances in the registry; `Sequences` to `/sequences/`, `n` the number of published sequences.

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

### Requirement: Procedure section tabs
The catalogue at `/procedures/`, the general-procedures view `/general-procedures/`, the taxonomy pages `/reaction_types/`, `/tags/` and `/authors/`, and every term page SHALL have, as the first element of `main`, a `nav.section-tabs` carrying `aria-label="Procedures"`. It holds a `ul` whose `li` entries each hold one link, in this order: `/procedures/` with the text `All procedures`, `/general-procedures/` with `General procedures`, `/reaction_types/` with `Reaction types`, `/tags/` with `Tags` and `/authors/` with `Authors`. The link whose URL is the page's own URL carries `aria-current="page"`; on a term page the link of its taxonomy carries `aria-current="true"`. No other tab carries `aria-current`. No other page has a `nav.section-tabs`.

On screen the tabs form one row above the page's `h1`, wrapping on narrow windows, and the current tab is marked by more than colour alone.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

#### Scenario: Tabs on the listing pages
- **WHEN** a test scans `/procedures/`, `/general-procedures/`, the three taxonomy pages and every term page after a theme build in locale `en`
- **THEN** each page's `main` begins with `nav.section-tabs` carrying `aria-label="Procedures"`, whose links are the five stated targets and texts in order
- **AND** `/procedures/`, `/general-procedures/` and each taxonomy page mark their own tab with `aria-current="page"`, each term page marks its taxonomy's tab with `aria-current="true"`, and no other tab carries `aria-current`

#### Scenario: No tabs elsewhere
- **WHEN** a test scans every other HTML file under `public/` except files under `public/pagefind/`, after the same build
- **THEN** none has a `nav.section-tabs`

#### Scenario: Tabs in a browser
- **WHEN** the orchestrator opens `/procedures/`, `/tags/` and a reaction-type term page in a browser at 1280 and at 500 CSS pixels, light and dark (manual verification, tasks.md section 3)
- **THEN** the tabs sit in one row above the `h1`, wrap at 500 pixels without horizontal scrolling, and the current tab is underlined as well as coloured

### Requirement: Navigation
The site's pages and the lab application's pages SHALL show one navigation, defined once, in the menu `main` of `site/hugo.toml`, which alone decides its entries, their order, their grouping and the section each link stands for:
- An entry is a link, with a `url`, or a group, a label whose links name it as their `parent`. Its `identifier` is the key of its text among the interface strings (localization "Interface strings"). Entries are ordered by `weight`. A link may list in `params.paths` the paths of its section: every path that begins with one of them lies in that section.
- The navigation is a `nav` whose `aria-label` is the interface string `nav_site`, listing the entries in order: a link as a link with its text, a group as its label followed by a list of its links.
- Every page of a build shows the same navigation, the site's pages and the application's alike, except that a build without the lab application's views (site-build "Hugo configuration") leaves out every link whose `url` begins with `/lab/`, and every group left without links.
- The link whose `url` is the page's own path carries `aria-current="page"`. Otherwise the link whose section the page lies in carries `aria-current="true"`. No other link of the navigation carries `aria-current`.
- On screen, at a given window width, the site title, the search form and the navigation have the same position and size on every page, the site's and the application's alike, and the page's `main` begins at the same place. Every page's `h1` has the same font size.

#### Scenario: One navigation from the menu
- **WHEN** a test builds a copy of the test collection in locale `en` with the lab application's views, reads the menu `main` of `site/hugo.toml` and the interface strings, and scans every HTML page under `public/` except those under `public/pagefind/`
- **THEN** each page's header holds one `nav` labelled `Site` that lists the menu's entries in order of weight, each group as its label and a list of its links, each entry with its interface string as text, and each link with its `url`

#### Scenario: A build without the lab
- **WHEN** a test builds a copy of the test collection without the lab application's views and scans its pages
- **THEN** each page's `nav` lists the menu's entries less the links under `/lab/` and the groups left empty, and no `href` in any page's header resolves under `/lab/`

#### Scenario: Current link
- **WHEN** a test scans every page of a theme build
- **THEN** on each page the navigation's link to the page's own path, where there is one, carries `aria-current="page"`; otherwise the link whose section the page lies in, where there is one, carries `aria-current="true"`; and no other link carries `aria-current`

#### Scenario: The shell does not move
- **WHEN** the orchestrator measures the site title, the search form, the navigation, the start of `main` and the `h1` of the home page, `/procedures/`, a procedure page, `/lab/`, `/lab/registry/` and `/lab/tasks/`, signed in and not, in a browser at 1280 and at 500 CSS pixels (manual verification, tasks.md section 3)
- **THEN** at each width each of them has the same position and size on every page, and the `h1` the same font size

## REMOVED Requirements

### Requirement: Compound pages
**Reason**: The lab's substance page (lab-registry "Registry pages") shows a substance's record, the procedures that make and use it, its sequences, its route tree and its structure image; compound links lead there.

### Requirement: Compound directory
**Reason**: The compound catalogue and its table are gone; the lab's substance list replaces them.
