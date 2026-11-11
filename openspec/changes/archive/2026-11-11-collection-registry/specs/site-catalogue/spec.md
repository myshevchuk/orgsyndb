## MODIFIED Requirements

### Requirement: Compound catalogue
The page `/compounds/` SHALL be the compound catalogue: a catalogue of every substance of the registry whose facets are the registry fields shown as facets, `chemical_class` and `group` (compound-fields "Registry fields"). Its `main` holds the compound tabs (requirement "Compound tabs"), and then one `div.catalogue` carrying `data-catalogue`, `data-search="text"`, `data-text-empty` `No compounds match the search and filters.`, and `data-text-ignored` and `data-text-remove` with the procedure catalogue's texts. It holds, in this order:
1. `div.list-head`, holding the `h1` `Compounds` and `p.catalogue-count`, which carries `role="status"`, `data-catalogue-count` and `data-filtered="{shown} of {total} compounds"`, and whose text is `<n> compounds`, or `1 compound`, where `n` is the number of table rows.
2. A `noscript` element holding `p.catalogue-noscript`, whose text is `Search and filters need JavaScript. Without it, this page lists every compound.`
3. `div.catalogue-layout`, holding `div.catalogue-facets` and then `div.catalogue-results`.

The parts are these:
- **Facets.** `div.catalogue-facets` carries `id="catalogue-facets"`, `data-catalogue-controls` and `hidden`, and holds an `h2` `Filters`, then one `details.facet` per facet field, in the registry fields' order, carrying `open` and `data-facet` with the field's key. Its `summary` carries an `id` and the field's shown label, and is followed by a `div` with `role="group"` and `aria-labelledby` naming that `id`, which holds one `label.facet-value` per value: an `input` with `type="checkbox"`, `name` the field's key and `value` the machine value, then `span.facet-label` with the value's display label, then an empty `span.facet-count`.
- **Facet values.** A facet field lists, in the field data's `order` (compound-fields "Field data for the site"), each term that some substance has or that is an ancestor of a term some substance has, with its shown label as the display label; its `label.facet-value` carries `style="--depth: <n>"`, where `n` is the number of the value's ancestors, and the screen stylesheet indents it by `n` steps.
- **Results.** `div.catalogue-results` holds `div.catalogue-toolbar`, with `data-catalogue-controls` and `hidden`, holding, when the page has facets, `button.facets-toggle` as the procedure catalogue's, then an empty `ul.catalogue-active` and `button.clear-all` `Clear all`; then `p.catalogue-message`, as the procedure catalogue's; then the compound table (site-theme "Compound directory"). The page has no sort select and no view select.
- **Rows.** Each body row of the table carries `data-id`, the substance's key; `data-title`, its shown name; `data-text`, its `name`, and those of its `name_de`, `formula`, CAS number, SMILES, article number and short name it has, joined by single spaces; and, for each facet field, `data-<key>`, a JSON array of the terms the substance has and each ancestor of one, each once; a field without a term gives `[]`.
- **Search.** The site header's form (site-theme "Page shell") carries `data-catalogue-search`, its `action` resolves to `/compounds/`, and its input carries `id="catalogue-q"`, the `aria-label` `Search compounds` and the placeholder `Name, formula, CAS or SMILES`.

The catalogue script makes the page interactive as the requirement "Catalogue in a browser" states: a value selects the compounds whose row carries it, so that a value of a vocabulary also selects the compounds filed under a value below it; the facets combine as the procedure catalogue's do; the search matches the rows' text through `match`; the rows keep their order by shown name. Its address holds the query and one parameter per selected value, named by the field's key, such as `/compounds/?q=ester&chemical_class=esters&group=reagents`. These texts are those of an English site; a German site has the German texts that the localization spec gives.

#### Scenario: The compound catalogue in the HTML
- **WHEN** a test scans `public/compounds/index.html` after a theme build in locale `en`
- **THEN** it has the stated elements, attributes and texts, its count reads `21 compounds`, its facets are `chemical_class` and `group`, in this order, labelled `Chemical class` and `Group`, and their values, labels, order and depths are those computed from the test collection's registry and field data
- **AND** every row's `data-id`, `data-title`, `data-text`, `data-chemical_class` and `data-group` equal the values computed from the registry and the field data, the `data-chemical_class` of `4-bromoacetophenone` holding exactly `aryl-ketones`, `ketones`, `carbonyl-compounds` and `aryl-halides`
- **AND** the header's form has the stated `action`, `id`, `aria-label` and placeholder

#### Scenario: A value set beside its ancestor
- **WHEN** a test builds a copy of the test collection in locale `en` after giving `acetone` the chemical classes `carbonyl-compounds` and `ketones` in the copy of its registry, and scans `public/compounds/index.html`
- **THEN** the `data-chemical_class` of the acetone row holds exactly `carbonyl-compounds` and `ketones`, each once

#### Scenario: Filtering and searching compounds
- **WHEN** the orchestrator opens `/compounds/` of the German demo build from `tools/orgsyndb serve`, ticks `Carbonylverbindungen`, then `Reagenzien` under `Gruppe`, types `ester`, reloads, removes the chip of `Carbonylverbindungen`, goes Back, and opens `/compounds/?chemical_class=nope&sort=title` (manual verification, tasks.md section 3)
- **THEN** the rows narrow to the compounds filed under a carbonyl class, then to the reagents among them, then to those whose text contains `ester`, with the count, the facet counts, the chips and the address following each step; the reload keeps the address `/compounds/?q=ester&chemical_class=carbonyl-compounds&group=reagents`, removing the chip leaves `/compounds/?q=ester&group=reagents`, and Back restores the first address with its rows, counts and chips; and the last shows every compound, the ignored-parameters notice naming both parameters, and the address `/compounds/`

### Requirement: Compound tabs
The site SHALL publish, for the registry field shown as tabs, `group` (compound-fields "Registry fields"), a tab page for each top-level term of its vocabulary that some substance has or that is an ancestor of a term some substance has, at `/compounds/group/<term>/`, and SHALL open `main` of `/compounds/` and of every tab page with the compound tabs.
- **Tabs.** A `nav.section-tabs` with the `aria-label` of the field's shown label holds a `ul` with one `li` per tab, each holding one `a`: first `All compounds`, linking `/compounds/`, then one per tab page, in the field data's `order` (compound-fields "Field data for the site"), with the value's shown label. The link of the page itself carries `aria-current="page"`.
- **Rows.** A tab page is a compound catalogue as the requirement "Compound catalogue" states, whose table holds the substances whose group is the tab's term or a term filed under it, by shown name. Its count counts those rows, and its facets list the values that some row of the page carries. Its `p.catalogue-noscript` reads `Search and filters need JavaScript. Without it, this page lists every compound of this tab.`
- **The tab's own term.** The `group` facet on a tab page leaves out the tab's term; a term filed under it carries the depth of its number of ancestors less one. A facet with no term to list on a tab page is left out, and a tab page left without a facet has no `div.catalogue-facets` and no `button.facets-toggle`.
- **Titles and search.** The `h1` and display title of a tab page are the value's shown label. The site header's form carries `data-catalogue-search`, its `action` resolves to the tab page, and its input carries `id="catalogue-q"`, the `aria-label` `Search compounds: <label>` and the placeholder `Name, formula, CAS or SMILES`.
- **Section.** A tab page lies in `/compounds/` for the navigation and carries no `data-pagefind-body`.

These texts are those of an English site; a German site has the German texts that the localization spec gives.

#### Scenario: Tabs in the HTML
- **WHEN** a test scans `public/compounds/index.html`, `public/compounds/group/purchased/index.html` and `public/compounds/group/synthesised/index.html` after a theme build in locale `en`
- **THEN** each opens `main` with the compound tabs `All compounds`, `Purchased` and `Synthesised`, in this order, labelled `Group`, the page's own link carrying `aria-current="page"`, and no other tab page exists under `public/compounds/group/`
- **AND** the `Purchased` page's rows are exactly the compounds whose `group` is `starting-materials` or `reagents`, by shown name, its `h1` and count read `Purchased` and `10 compounds`, its `group` facet lists `starting-materials` and `reagents` with the depth 0 and no `purchased`, its `chemical_class` facet lists exactly the values its rows carry, and its header form has the `action` `/compounds/group/purchased/` and the `aria-label` `Search compounds: Purchased`
- **AND** the header's `Compounds` link carries `aria-current="true"` on both tab pages

#### Scenario: Tabs in German
- **WHEN** a test reads `public/compounds/group/purchased/index.html` of a build of the test collection in locale `de`
- **THEN** its tabs read `Alle Verbindungen`, `Zugekauft` and `Selbst hergestellt`, its `h1` reads `Zugekauft`, its header search is labelled `Verbindungen durchsuchen: Zugekauft`, and its `noscript` note reads `Suche und Filter brauchen JavaScript. Ohne JavaScript zeigt diese Seite alle Verbindungen dieses Reiters.`

#### Scenario: Filtering within a tab
- **WHEN** the orchestrator opens `/compounds/group/purchased/` of the German demo build from `tools/orgsyndb serve`, ticks `Reagenzien`, types `acet`, follows the tab `Alle Verbindungen`, and goes Back (manual verification, tasks.md section 3)
- **THEN** the rows narrow to the purchased reagents and then to those whose text contains `acet`, the tab `Alle Verbindungen` opens `/compounds/` with every compound, and Back restores the tab page's address, rows, chips and counts
