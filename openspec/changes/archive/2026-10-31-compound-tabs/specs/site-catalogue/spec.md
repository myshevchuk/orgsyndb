## MODIFIED Requirements

### Requirement: Catalogue script
The catalogue, the term pages, `/general-procedures/`, `/compounds/` and its tab pages SHALL load one script, `/js/catalogue.<hash>.js`, with `defer`. It is built with Hugo Pipes by concatenating `site/assets/js/search-terms.js`, `catalogue-core.js` and `catalogue.js`, minified and fingerprinted. No other page loads it, and no page loads `pagefind-ui.js` or `pagefind-ui.css`. On a catalogue without `data-search="text"`, the script imports the Pagefind bundle only while the query is active, from `pagefind/pagefind.js` beside the directory of its own script URL (the URL `../pagefind/pagefind.js` resolved against it), so that the bundle loads under any path prefix. On the compound catalogue it never imports it.

#### Scenario: Script wiring
- **WHEN** a test scans every HTML page after a theme build
- **THEN** exactly the catalogue, the term pages, `/general-procedures/`, `/compounds/` and its tab pages load `/js/catalogue.<hash>.js`, which contains `OrgSynSearch`, `OrgSynCatalogue` and `pagefind/pagefind.js`, and no page references `pagefind-ui`

### Requirement: Compound catalogue
The page `/compounds/` SHALL be the compound catalogue: a catalogue of every compound of the registry whose facets are the fields its collection declares with `facet = true` (compound-fields "Field declarations"). Its `main` holds, when the collection declares a tabs field, the compound tabs (requirement "Compound tabs"), and then one `div.catalogue` carrying `data-catalogue`, `data-search="text"`, `data-text-empty` `No compounds match the search and filters.`, and `data-text-ignored` and `data-text-remove` with the procedure catalogue's texts. It holds, in this order:
1. `div.list-head`, holding the `h1` `Compounds` and `p.catalogue-count`, which carries `role="status"`, `data-catalogue-count` and `data-filtered="{shown} of {total} compounds"`, and whose text is `<n> compounds`, or `1 compound`, where `n` is the number of table rows.
2. A `noscript` element holding `p.catalogue-noscript`, whose text is `Search and filters need JavaScript. Without it, this page lists every compound.`
3. `div.catalogue-layout`, holding, when the collection declares a facet field, `div.catalogue-facets`, and then `div.catalogue-results`.

The parts are these:
- **Facets.** `div.catalogue-facets` carries `id="catalogue-facets"`, `data-catalogue-controls` and `hidden`, and holds an `h2` `Filters`, then one `details.facet` per facet field, in declared order, carrying `open` and `data-facet` with the field's key. Its `summary` carries an `id` and the field's shown label, and is followed by a `div` with `role="group"` and `aria-labelledby` naming that `id`, which holds one `label.facet-value` per value: an `input` with `type="checkbox"`, `name` the field's key and `value` the machine value, then `span.facet-label` with the value's display label, then an empty `span.facet-count`.
- **Facet values.** A `boolean` field lists `true` and `false`, in that order, each only when some compound sets it, with the display labels `Yes` and `No`. A `choice` field lists, in the field data's `order` (compound-fields "Field data for the site"), each value that some compound sets or that is an ancestor of a value some compound sets, with its shown label as the display label; its `label.facet-value` carries `style="--depth: <n>"`, where `n` is the number of the value's ancestors, and the screen stylesheet indents it by `n` steps.
- **Results.** `div.catalogue-results` holds `div.catalogue-toolbar`, with `data-catalogue-controls` and `hidden`, holding, when the page has facets, `button.facets-toggle` as the procedure catalogue's, then an empty `ul.catalogue-active` and `button.clear-all` `Clear all`; then `p.catalogue-message`, as the procedure catalogue's; then the compound table (site-theme "Compound directory"). The page has no sort select and no view select.
- **Rows.** Each body row of the table carries `data-id`, the compound's key; `data-title`, its shown name; `data-text`, its `name`, its `name_de` when set, its `formula`, its CAS number when set, its SMILES and its value of each `text` field declared with `search = true` that it sets, joined by single spaces; and, for each facet field, `data-<key>`, a JSON array of machine values: for a `boolean` field `"true"` or `"false"`, for a `choice` field each value the compound sets and each ancestor of one, each once; an unset field gives `[]`.
- **Search.** The site header's form (site-theme "Page shell") carries `data-catalogue-search`, its `action` resolves to `/compounds/`, and its input carries `id="catalogue-q"`, the `aria-label` `Search compounds` and the placeholder `Name, formula, CAS or SMILES`.

The catalogue script makes the page interactive as the requirement "Catalogue in a browser" states: a value selects the compounds whose row carries it, so that a value of a vocabulary also selects the compounds filed under a value below it; the facets combine as the procedure catalogue's do; the search matches the rows' text through `match`; the rows keep their order by shown name. Its address holds the query and one parameter per selected value, named by the field's key, such as `/compounds/?q=ester&chemical_class=esters&in_house=true`. These texts are those of an English site; a German site has the German texts that the localization spec gives.

#### Scenario: The compound catalogue in the HTML
- **WHEN** a test scans `public/compounds/index.html` after a theme build in locale `en`
- **THEN** it has the stated elements, attributes and texts, its count reads `20 compounds`, its facets are `chemical_class`, `in_house` and `group`, in this order, labelled `Chemical class`, `Made in house` and `Group`, and their values, labels, order and depths are those computed from the test collection's registry and field data
- **AND** every row's `data-id`, `data-title`, `data-text`, `data-chemical_class`, `data-in_house` and `data-group` equal the values computed from the registry and the field data, the `data-chemical_class` of `4-bromoacetophenone` holding exactly `aryl-ketones`, `ketones`, `carbonyl-compounds` and `aryl-halides`
- **AND** the header's form has the stated `action`, `id`, `aria-label` and placeholder

#### Scenario: A value set beside its ancestor
- **WHEN** a test builds a copy of the test collection in locale `en` after setting `chemical_class = ["carbonyl-compounds", "ketones"]` in `compounds/acetone.toml`, and scans `public/compounds/index.html`
- **THEN** the `data-chemical_class` of the acetone row holds exactly `carbonyl-compounds` and `ketones`, each once

#### Scenario: A collection without facet fields
- **WHEN** a test builds a copy of the test collection in locale `en` after removing every `facet = true` line from its `orgsyndb.toml`, and scans `public/compounds/index.html`
- **THEN** the catalogue has no `div.catalogue-facets` and no `button.facets-toggle`, and still has the count, the chips list, `Clear all`, the message, the table and the header's compound search

#### Scenario: Filtering and searching compounds
- **WHEN** the orchestrator opens `/compounds/` of the German demo build from `tools/orgsyndb serve`, ticks `Carbonylverbindungen`, then `Ja` under `Eigene Herstellung`, types `ester`, reloads, removes the chip of `Carbonylverbindungen`, goes Back, and opens `/compounds/?chemical_class=nope&sort=title` (manual verification, tasks.md section 3)
- **THEN** the rows narrow to the compounds filed under a carbonyl class, then to those made in house, then to those whose text contains `ester`, with the count, the facet counts, the chips and the address following each step; the reload keeps the address `/compounds/?q=ester&chemical_class=carbonyl-compounds&in_house=true`, removing the chip leaves `/compounds/?q=ester&in_house=true`, and Back restores the first address with its rows, counts and chips; and the last shows every compound, the ignored-parameters notice naming both parameters, and the address `/compounds/`


## ADDED Requirements

### Requirement: Compound tabs
When a collection declares a field with `tabs = true` (compound-fields "Field declarations"), the site SHALL publish a tab page for each top-level value of the field's vocabulary that some compound sets or that is an ancestor of a value some compound sets, at `/compounds/<field key>/<value>/`, and SHALL open `main` of `/compounds/` and of every tab page with the compound tabs. Without such a field there is neither a tab page nor the compound tabs.
- **Tabs.** A `nav.section-tabs` with the `aria-label` of the field's shown label holds a `ul` with one `li` per tab, each holding one `a`: first `All compounds`, linking `/compounds/`, then one per tab page, in the field data's `order` (compound-fields "Field data for the site"), with the value's shown label. The link of the page itself carries `aria-current="page"`.
- **Rows.** A tab page is a compound catalogue as the requirement "Compound catalogue" states, whose table holds the compounds that set the tab's value or a value filed under it in the tabs field, whether or not the field is a facet, by shown name. Its count counts those rows, and its facets list the values that some row of the page carries. Its `p.catalogue-noscript` reads `Search and filters need JavaScript. Without it, this page lists every compound of this tab.`
- **The tab's own value.** When the tabs field is also a facet, its facet on a tab page leaves out the tab's value; a value filed under the tab's value carries the depth of its number of ancestors less one, and every other value its own depth. Under a multiple-valued tabs field a compound may lie in several tabs, and its other values stay in the facet. A facet with no value to list on a tab page is left out, and a tab page left without a facet has no `div.catalogue-facets` and no `button.facets-toggle`.
- **Titles and search.** The `h1` and display title of a tab page are the value's shown label. The site header's form carries `data-catalogue-search`, its `action` resolves to the tab page, and its input carries `id="catalogue-q"`, the `aria-label` `Search compounds: <label>` and the placeholder `Name, formula, CAS or SMILES`.
- **Section.** A tab page lies in `/compounds/` for the navigation and carries no `data-pagefind-body`.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

#### Scenario: Tabs in the HTML
- **WHEN** a test scans `public/compounds/index.html`, `public/compounds/group/purchased/index.html` and `public/compounds/group/synthesised/index.html` after a theme build in locale `en`
- **THEN** each opens `main` with the compound tabs `All compounds`, `Purchased` and `Synthesised`, in this order, labelled `Group`, the page's own link carrying `aria-current="page"`, and no other tab page exists under `public/compounds/group/`
- **AND** the `Purchased` page's rows are exactly the compounds whose `group` is `starting-materials` or `reagents`, by shown name, its `h1` and count read `Purchased` and `10 compounds`, its `group` facet lists `starting-materials` and `reagents` with the depth 0 and no `purchased`, its `chemical_class` facet lists exactly the values its rows carry, and its header form has the `action` `/compounds/group/purchased/` and the `aria-label` `Search compounds: Purchased`
- **AND** the header's `Compounds` link carries `aria-current="true"` on both tab pages

#### Scenario: Tabs by a multiple-valued field
- **WHEN** a test builds a copy of the test collection in locale `en` after moving the `tabs = true` line from the declaration of `group` to that of `chemical_class` in its `orgsyndb.toml` and adding to its `vocabularies/chemical-classes.toml` the top-level value `heterocycles` (`Heterocycles`, `Heterocyclen`), which no compound sets
- **THEN** the tab pages are exactly `/compounds/chemical_class/<value>/` for `carbonyl-compounds`, `alcohols`, `phenols`, `aryl-halides`, `organoboron-compounds` and `organophosphorus-compounds`, in this order after `All compounds`, and `/compounds/chemical_class/heterocycles/` does not exist
- **AND** `4-bromoacetophenone` is a row of both the `carbonyl-compounds` and the `aryl-halides` page; on the `carbonyl-compounds` page the `chemical_class` facet has no `carbonyl-compounds`, lists `aryl-ketones` with the depth 1 and `aryl-halides` with the depth 0; and the `organoboron-compounds` page, whose one compound sets no other class, has the facets `in_house` and `group` only
- **AND** `public/compounds/group/` does not exist

#### Scenario: A tabs field that is not a facet
- **WHEN** a test builds a copy of the test collection in locale `en` after removing the `facet = true` line from the declaration of `group` in its `orgsyndb.toml`
- **THEN** `public/compounds/group/purchased/index.html` lists exactly the ten purchased compounds and has no `group` facet

#### Scenario: Tabs in German
- **WHEN** a test reads `public/compounds/group/purchased/index.html` of a build of the test collection in locale `de`
- **THEN** its tabs read `Alle Verbindungen`, `Zugekauft` and `Selbst hergestellt`, its `h1` reads `Zugekauft`, its header search is labelled `Verbindungen durchsuchen: Zugekauft`, and its `noscript` note reads `Suche und Filter brauchen JavaScript. Ohne JavaScript zeigt diese Seite alle Verbindungen dieses Reiters.`

#### Scenario: A collection without a tabs field
- **WHEN** a test builds a copy of the test collection in locale `en` after removing the `tabs = true` line from its `orgsyndb.toml`
- **THEN** `public/compounds/index.html` has no `nav.section-tabs`, and `public/compounds/group/` does not exist

#### Scenario: Filtering within a tab
- **WHEN** the orchestrator opens `/compounds/group/purchased/` of the German demo build from `tools/orgsyndb serve`, ticks `Reagenzien`, types `acet`, follows the tab `Alle Verbindungen`, and goes Back (manual verification, tasks.md section 3)
- **THEN** the rows narrow to the purchased reagents and then to those whose text contains `acet`, the tab `Alle Verbindungen` opens `/compounds/` with every compound, and Back restores the tab page's address, rows, chips and counts
