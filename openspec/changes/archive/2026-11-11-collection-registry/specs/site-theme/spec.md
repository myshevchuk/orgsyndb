## MODIFIED Requirements

### Requirement: Precursor and used-in links
A procedure's precursors SHALL be the other published procedures that have among their products a compound of its `substrates`, and the procedures it is used in SHALL be the other published procedures that have among their `substrates` a compound of its products. The `Precursors` value holds one `a.precursor` per precursor and the `Used in` value one `a.used-in` per procedure it is used in, each linking that procedure's page with the text `<ID> <title>`, ordered by ID. A procedure with no precursor has no `Precursors` pair, and one used in no other procedure has no `Used in` pair.

#### Scenario: Links resolve in both directions
- **WHEN** a test scans every procedure page after a theme build, resolves each `a.precursor` and `a.used-in` `href` against the page's URL, and derives the precursor relation from the content files' `products` and `substrates`
- **THEN** every link resolves to an existing procedure page
- **AND** for every pair where A is a precursor of B, B's page has an `a.precursor` to A and A's page has an `a.used-in` to B
- **AND** no other `a.precursor` or `a.used-in` exists

#### Scenario: The shipped chains
- **WHEN** the same test reads the pages of OSDB-0001, 0002, 0004, 0005, 0007, 0008 and 0009
- **THEN** OSDB-0002, 0005, 0008 and 0009 each have one `a.precursor`, to OSDB-0001, 0004, 0007 and 0004 respectively
- **AND** OSDB-0001 and 0007 each have one `a.used-in`, back to OSDB-0002 and 0008, and OSDB-0004 has two, to OSDB-0005 and OSDB-0009

#### Scenario: A second route
- **WHEN** a test scans the pages of OSDB-0001, OSDB-0002 and OSDB-0908 after a theme build that adds `tests/fixtures/theme/OSDB-0908-second-route.md`, which makes `salicylic-acid` and names no substrate the demo procedures make, with the substances it names added to the registry of the copy from the fixture registry
- **THEN** OSDB-0002 has two `a.precursor`, to OSDB-0001 and OSDB-0908, in that order, and OSDB-0908 has one `a.used-in`, to OSDB-0002

### Requirement: Compound directory
The page `/compounds/` SHALL be the compound catalogue (site-catalogue "Compound catalogue"), whose results end with a `table.compound-table` with the header cells `Compound`, `Formula`, `MW` and `CAS`, then one header cell for each registry field shown as a column, `Article no.` and `Chemical class` in that order (compound-fields "Registry fields"), holding the field's shown label, then `Made by` and `Used in`, and one body row per substance of the registry, ordered by shown name. A row holds a link to the compound's page with its shown name, the formula with each digit run in `<sub>` or an empty cell, `<mw> g/mol` or an empty cell, the CAS number or an empty cell, for each column field the substance's value written as compound-fields "Field display" states or an empty cell when it has none, and the numbers of published procedures that make it and that use it. Without JavaScript the page shows the complete table and no control.

#### Scenario: Every compound is listed
- **WHEN** a test scans `public/compounds/index.html` after a theme build in locale `en`
- **THEN** its rows are the registry's compounds, each once, ordered by name, with the stated cells, and their counts equal those computed from the published content files
- **AND** its header cells are `Compound`, `Formula`, `MW`, `CAS`, `Article no.`, `Chemical class`, `Made by` and `Used in`

#### Scenario: Empty cells
- **WHEN** a test scans `public/compounds/index.html` after a theme build of the test collection in locale `en`
- **THEN** the row of `new-compound-7`, which has no formula, molar mass or CAS number, has empty cells for them, and the row of `acetylsalicylic-acid` reads `CH-0010` under `Article no.`

### Requirement: Compound pages
The site SHALL publish, for every compound of the registry, a page at `/compounds/<key>/`, made by a Hugo content adapter in `site/content/compounds/` from `site.Data.compounds` (site-build "Hugo configuration"). The page's display title is the compound's shown name (localization "German compound names"), and its `main` holds, in this order:
- the `h1` with that name;
- when the substance has a structure image (compound-registry "Structure images by key"), a `figure.structure` holding an `img` whose `src` resolves to the published image and whose `alt` is `Structure of <name>`; otherwise no figure and no placeholder;
- a `dl.compound-facts` with the pairs `Formula`, `MW`, `CAS` and `SMILES`, each only when the substance has it, written as the metadata panel writes them, the SMILES with its copy button, followed by one pair for each registry field the substance has, in the registry fields' order, its label and value written as compound-fields "Field display" states, with whitespace after each `</dt>`;
- `section.compound-made-by`, only when some published procedure has the compound among its products, with the `h2` `Made by` and a `ul` holding one `li` per such procedure, by ID, or, for a general procedure, one per entry that makes the compound, in entry order: an `a` linking the procedure page with the text `<ID> <title>`, then, for a general procedure, ` · entry <n>`, then ` · `, the yield of this compound in that procedure or entry as `<n> %`, then ` · ` and the procedure's status badge;
- `section.compound-used-in`, only when some published procedure has the compound among its `substrates`, with the `h2` `Used in` and a `ul` holding one `li` per such procedure, by ID: an `a` linking the procedure page with the text `<ID> <title>`, then ` · ` and its status badge;
- `section.compound-sequences`, as synthesis-sequences "Sequences beside procedures and compounds" states;
- `section.compound-routes`, as synthesis-routes "Routes on compound pages" states.

A compound page carries no `data-pagefind-body`, so the search index holds procedures only, and it loads no script but `site.js`.

#### Scenario: A page per compound
- **WHEN** a test scans `public/compounds/` after a theme build in locale `en`
- **THEN** every key of the test collection's registry has a page `compounds/<key>/index.html` whose `h1` is the compound's `name` and whose facts equal the registry's values, the registry fields the substance has following `SMILES` in their order, and no other compound page exists; the page of `new-compound-7` has no `Formula`, `MW` or `SMILES` pair

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

### Requirement: Procedure page structure
Each procedure page's `main` element SHALL contain, in document order:
1. the sample banner, when the requirement "Sample banner" applies;
2. `header.procedure-header`, holding:
   - `p.procedure-id`, containing the ID in an element with `data-pagefind-meta="id"`, then the status badge `span.badge.badge--<status>` whose text is the status, then, when the status is `checked` and the procedure sets `checked_by`, the sign-off `span.sign-off` with the text `by <names>`, the names joined by `, `, so that the line reads `OSDB-0921 checked by B. Example`;
   - the `h1` with the title;
   - `dl.key-facts`, holding a `dt`/`dd` pair `Scale` and a pair `Yield`, with whitespace after each `</dt>`. With one product the `Yield` value is `<n> %`; with several it lists every product as `<n> % <name>`, in `products` order, joined by `, `, where `<name>` is the compound's shown name (localization "German compound names"). For a general procedure the `Yield` value is the range of the yields of all its entries' products, `<min>–<max> %`, or `<n> %` when they are all equal;
   - the print facts of the print-layout spec;
   - `p.actions`, holding `button.print-button` with `type="button"`, the attribute `data-print`, the text `Print / Save as PDF` and the attribute `hidden`;
   - the structure figures of the requirement "Structure image slot";
3. `article.procedure`, the only element with `data-pagefind-body`, holding in order:
   - the details wrapper, holding the metadata panel;
   - the rendered body;
   - the index-terms element and then the SMILES index element of the site-search spec.

#### Scenario: Header and body in order
- **WHEN** a test scans `procedures/osdb-0002/index.html` and `procedures/osdb-0001/index.html` after a theme build
- **THEN** each has the elements in the stated order, the `h1`, the visible ID, the key facts and the structure figure lie outside the `article`, and the `article` contains the `Summary` heading after the metadata panel

#### Scenario: Key facts and sign-off
- **WHEN** a test scans `procedures/osdb-0002/index.html` after a theme build, and `procedures/osdb-0921/index.html` and `procedures/osdb-0923/index.html` after a build that adds the catalogue fixtures to the test collection
- **THEN** OSDB-0002's key facts are `Scale` `20 mmol` and `Yield` `75 %`, and it has no sign-off
- **AND** the ID line of OSDB-0921, which is checked by B. Example, reads `OSDB-0921 checked by B. Example`, and OSDB-0923, a draft, has no sign-off

#### Scenario: Yields of two products
- **WHEN** a test scans `procedures/osdb-0907/index.html` after a theme build that adds the two-product fixture `tests/fixtures/theme/OSDB-0907-two-products.md`, with `scale = "10 mmol"` and the products `trans-stilbene` at 45 % and `cis-stilbene` at 30 %, to a copy of the test collection whose registry gains the substances it names from the fixture registry `tests/fixtures/registry.json`
- **THEN** its key facts are `Scale` `10 mmol` and `Yield` `45 % trans-Stilbene, 30 % cis-Stilbene`

#### Scenario: Yields of a general procedure
- **WHEN** a test scans the page of the test collection's general procedure after a theme build in locale `en`
- **THEN** its `Yield` key fact is the range from the lowest to the highest yield of its entries' products, written `<min>–<max> %`
