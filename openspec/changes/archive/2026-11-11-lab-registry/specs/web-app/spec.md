## MODIFIED Requirements

### Requirement: Collection index
`orgsyndb_web.index` SHALL read the JSON file `ORGSYNDB_INDEX`, the output of `orgsyndb index`, and read it again when the path the file resolves to or its modification time changes. It gives:

- the site language;
- the keys of the collection's compounds;
- the procedure IDs;
- the synthesis sequences, each with its ID and its steps' procedure IDs in order, taken from the front matter of the file the site publishes for that ID: the one in the site's language, else the one without a language code, else one in another language, as `pipeline` chooses.

`has_compound(key)` tells whether the index lists a compound of that key, so that the site has its page; `procedure_for(token)` returns the procedure ID when the index lists it; `sequence_for(token)` the sequence of that ID. The application takes no compound's name, molar mass or identifiers from the index: substances are the registry's (lab-registry "Substances"). A missing, unreadable or malformed file gives an empty index: the language `de` and no compounds, procedures or sequences; the application logs the problem once per change of the file and serves every page.

#### Scenario: Lookups in the demo collection
- **WHEN** a test points `ORGSYNDB_INDEX` at the output of `orgsyndb index` for a copy of the demo collection
- **THEN** `has_compound("cinnamic-acid")` is true and `has_compound("CH-0012")` false, `procedure_for("OSDB-0008")` returns `OSDB-0008`, `sequence_for("SEQ-0001")` has the steps `OSDB-0001` and `OSDB-0002`, and `procedure_for("OSDB-9999")` returns none

#### Scenario: No index
- **WHEN** `ORGSYNDB_INDEX` names a file that does not exist and a test client requests `/lab/tasks/`
- **THEN** the page answers 200 with `<html lang="de">`

#### Scenario: Index replaced
- **WHEN** a test writes an index with language `en`, reads it, then replaces the file with one of language `de` and a later modification time
- **THEN** the next read gives `de`

### Requirement: Page shell
Every page but the admin's and the summary's SHALL link, from `/lab/static/site/`, the site's own `tokens.css`, `base.css`, `screen.css` with `media="screen"` and `print.css` with `media="print"`, all collected from `site/assets/css/` of the same checkout, and then `/lab/static/lab.css`. Its `header.site-header` holds the site title linking to `/`, a `nav` labelled as the site's navigation with the application's views, each a link and the path its pages lie under, followed by the site's sections `/compounds/`, `/sequences/`, `/procedures/` and `/help/` under the site's labels. The views are `Bestand` (`Inventory`), linking to `/lab/inventory/end-products/`, its pages under `/lab/inventory/`; `Planung` (`Planning`), linking to `/lab/planning/`, its pages under `/lab/planning/`; `Aufgaben` (`Tasks`), linking to `/lab/tasks/`, its pages under `/lab/tasks/`; and `Substanzen` (`Substances`), linking to `/lab/registry/`, its pages under `/lab/registry/`. A view's link carries `aria-current="page"` on the page it links to and `aria-current="true"` on every other page under its view's path. The header ends with the signed-in user's initials and a sign-out button, or a link `Anmelden` (`Sign in`). A message confirming a saved change shows above the content. These pages carry no `script` element but the item list, whose one `script` element loads `/lab/static/lab.js` with `defer` (end-product-inventory "Item list"); the admin keeps Django's own pages and scripts. The summary, `/lab/summary/`, links the same five stylesheets and carries no `script` element, but no header, navigation or message; its `base` element sends its links to the top window, and it answers with `X-Frame-Options: SAMEORIGIN`, so that a page of the same host may frame it.

#### Scenario: Shell
- **WHEN** a test client requests `/lab/tasks/` signed in as `KL` and once not signed in
- **THEN** both pages link the five stylesheets in that order, the navigation lists `Bestand` and `Planung` without `aria-current`, `Aufgaben` with `aria-current="page"`, `Substanzen` without it, and then the four site sections in that order, the first shows `KL` and a sign-out form and the second a link to the sign-in page, and neither has a `script` element

#### Scenario: Navigation in the inventory
- **WHEN** a test client requests the item list and an item's page
- **THEN** the navigation's `Bestand` link carries `aria-current="page"` on the list and `aria-current="true"` on the item's page, and `Planung` and `Aufgaben` carry neither

#### Scenario: Navigation in the planning list
- **WHEN** a test client requests `/lab/planning/` and `/lab/planning/?all=1`
- **THEN** the navigation's `Planung` link carries `aria-current="page"` on both, and `Bestand` and `Aufgaben` carry neither

#### Scenario: A summary to frame
- **WHEN** a test client requests `/lab/summary/` and `/lab/tasks/`
- **THEN** the first links the five stylesheets, has a `base` with `target="_top"` and no `header` or `script` element, and answers with `X-Frame-Options: SAMEORIGIN`; the second answers with `X-Frame-Options: DENY`

#### Scenario: One script for the item list
- **WHEN** a test client requests the item list, an item's page and `/lab/planning/`
- **THEN** the item list has one `script` element, with `src` `/lab/static/lab.js` and `defer`, and the other two have none

## ADDED Requirements

### Requirement: Substance links
Wherever the application shows a substance, the substance of an item, a lot or a task among them, it SHALL show the substance's name (lab-registry "Substances") linking to its page, `/lab/registry/substances/<key>/`, except where a requirement links that name elsewhere, as the item list does for an item without an article number (end-product-inventory "Item list"). A form field for a substance takes its key and offers, through a `datalist`, every substance's key labelled with its name; an unknown key is an error at the field.

#### Scenario: A task's substance
- **WHEN** the demo data set is written and a test client requests `/lab/tasks/?state=all`
- **THEN** each task of `cinnamic-acid` shows `(E)-Zimtsäure` linking to `/lab/registry/substances/cinnamic-acid/`

## REMOVED Requirements

### Requirement: Compound links
**Reason**: Records refer to substances of the registry by foreign key; no text is looked up in the collection index any more, so there is no unknown compound to mark.
**Migration**: Substance links replace them; a substance's page links to the site's compound page when the index lists its key.
