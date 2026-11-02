## MODIFIED Requirements

### Requirement: Compound pages
The site SHALL publish, for every compound of the registry, a page at `/compounds/<key>/`, made by a Hugo content adapter in `site/content/compounds/` from `site.Data.compounds` (site-build "Hugo configuration"). The page's display title is the compound's shown name (localization "German compound names"), and its `main` holds, in this order:
- the `h1` with that name;
- when the compound sets `structure_image`, a `figure.structure` holding an `img` whose `src` resolves to the published image and whose `alt` is `Structure of <name>`; otherwise no figure and no placeholder;
- a `dl.compound-facts` with the pairs `Formula`, `MW`, `CAS` (only when set) and `SMILES`, written as the metadata panel writes them, the SMILES with its copy button, followed by one pair for each field the collection declares and the compound sets, in declared order, its label and value written as compound-fields "Field display" states, with whitespace after each `</dt>`;
- `section.compound-made-by`, only when some published procedure has the compound among its products, with the `h2` `Made by` and a `ul` holding one `li` per such procedure, by ID, or, for a general procedure, one per entry that makes the compound, in entry order: an `a` linking the procedure page with the text `<ID> <title>`, then, for a general procedure, ` · entry <n>`, then ` · `, the yield of this compound in that procedure or entry as `<n> %`, then ` · ` and the procedure's status badge;
- `section.compound-used-in`, only when some published procedure has the compound among its `substrates`, with the `h2` `Used in` and a `ul` holding one `li` per such procedure, by ID: an `a` linking the procedure page with the text `<ID> <title>`, then ` · ` and its status badge;
- `section.compound-sequences`, as synthesis-sequences "Sequences beside procedures and compounds" states;
- `section.compound-routes`, as synthesis-routes "Routes on compound pages" states.

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
