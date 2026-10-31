## MODIFIED Requirements

### Requirement: Compound pages
The site SHALL publish, for every compound of the registry, a page at `/compounds/<key>/`, made by a Hugo content adapter in `site/content/compounds/` from `site.Data.compounds` (site-build "Hugo configuration"). The page's display title is the compound's shown name (localization "German compound names"), and its `main` holds, in this order:
- the `h1` with that name;
- when the compound sets `structure_image`, a `figure.structure` holding an `img` whose `src` resolves to the published image and whose `alt` is `Structure of <name>`; otherwise no figure and no placeholder;
- a `dl.compound-facts` with the pairs `Formula`, `MW`, `CAS` (only when set) and `SMILES`, written as the metadata panel writes them, the SMILES with its copy button, followed by one pair for each field the collection declares and the compound sets, in declared order, its label and value written as compound-fields "Field display" states, with whitespace after each `</dt>`;
- `section.compound-made-by`, only when some published procedure has the compound among its products, with the `h2` `Made by` and a `ul` holding one `li` per such procedure, by ID, or, for a general procedure, one per entry that makes the compound, in entry order: an `a` linking the procedure page with the text `<ID> <title>`, then, for a general procedure, ` · entry <n>`, then ` · `, the yield of this compound in that procedure or entry as `<n> %`, then ` · ` and the procedure's status badge;
- `section.compound-used-in`, only when some published procedure has the compound among its `substrates`, with the `h2` `Used in` and a `ul` holding one `li` per such procedure, by ID: an `a` linking the procedure page with the text `<ID> <title>`, then ` · ` and its status badge.

- `section.compound-sequences`, as synthesis-sequences "Sequences beside procedures and compounds" states.

A compound page carries no `data-pagefind-body`, so the search index holds procedures only, and it loads no script but `site.js`.

#### Scenario: A page per compound
- **WHEN** a test scans `public/compounds/` after a theme build in locale `en`
- **THEN** every key of the test collection's registry has a page `compounds/<key>/index.html` whose `h1` is the compound's `name` and whose facts equal the registry's values, the declared fields the compound sets following `SMILES` in declared order, and no other compound page exists

#### Scenario: Made by and used in
- **WHEN** a test reads the pages of `salicylic-acid` and `methyl-salicylate` after the same build
- **THEN** the first's `Made by` list holds OSDB-0001 with `80 %` and its `Used in` list holds OSDB-0002
- **AND** the second has no `section.compound-made-by`, and its `Used in` list holds OSDB-0001

#### Scenario: Made by an entry of a general procedure
- **WHEN** a test reads the page of `1-biphenyl-4-yl-ethanol` after the same build
- **THEN** its `Made by` list holds OSDB-0005 with `90 %`, and the demo's general procedure with ` · entry 1 · ` and that entry's yield

#### Scenario: Compound pages are not indexed
- **WHEN** a test scans every compound page after the same build
- **THEN** none has an element with `data-pagefind-body`, and the image of `isopentyl-acetate` resolves to `public/structures/isopentyl-acetate.svg`

### Requirement: Compound directory
The page `/compounds/` SHALL hold the `h1` `Compounds`, then a `table.compound-table` with the header cells `Compound`, `Formula`, `MW` and `CAS`, then one header cell for each field the collection declares with `column = true`, in declared order, holding the field's shown label, then `Made by` and `Used in`, and one body row per compound of the registry, ordered by shown name. A row holds a link to the compound's page with its shown name, the formula with each digit run in `<sub>`, `<mw> g/mol`, the CAS number or an empty cell, for each column field the compound's value written as compound-fields "Field display" states or an empty cell when the compound does not set it, and the numbers of published procedures that make it and that use it. The header and body cells of a `number` field carry the class `num`. The directory holds no form and needs no JavaScript.

#### Scenario: Every compound is listed
- **WHEN** a test scans `public/compounds/index.html` after a theme build in locale `en`
- **THEN** its rows are the registry's compounds, each once, ordered by name, with the stated cells, and their counts equal those computed from the published content files
- **AND** its header cells are `Compound`, `Formula`, `MW`, `CAS`, the labels of the column fields that the test collection's `orgsyndb.toml` declares, in declared order, `Made by` and `Used in`

#### Scenario: Number and boolean columns
- **WHEN** a test builds a copy of the test collection in locale `en` after adding `column = true` to the declarations of `stock` and `in_house` in its `orgsyndb.toml`, and scans `public/compounds/index.html`
- **THEN** the header cells `Stock` and `Made in house` follow `Chemical class`, the header and body cells of `Stock` carry the class `num` and those of `Made in house` do not, a compound that sets neither field has an empty cell in both columns, `ethyl-triphenylphosphoranylidene-acetate` reads `12.5 g`, and a compound with `in_house = false` reads `No`

