## MODIFIED Requirements

### Requirement: Details view
Each catalogue row's `Procedure` cell SHALL hold, after the title link, a `div.row-details` with:
- a `dl` with one `dt`/`dd` pair per field that is set, labelled as the metadata panel labels them: `Product` or `Products` (the shown names of the products, joined by `, `, as text; absent when there is one product whose shown name equals the title), `Formula` (each digit run in `<sub>`), `MW` (`<mw> g/mol`) and `CAS`, these three only for a procedure with one product, from its compound, then `Yield` (written as the key facts write it, site-theme "Procedure page structure") and `Created` (`<time datetime="<RFC 3339 date>">YYYY-MM-DD</time>`), numbers with the site language's decimal separator;
- when a product's compound sets `structure_image`, an `img.row-structure` for the first such product, whose `src` resolves to the published image, with `alt` `Structure of <name>`, `loading="lazy"` and `decoding="async"`; otherwise no image and no placeholder.

The screen stylesheet hides `div.row-details` unless the catalogue carries `data-view="details"`. The Details view uses the same rows, order and controls as the table.

#### Scenario: Details markup
- **WHEN** a test scans `public/procedures/index.html` of a theme build that adds the catalogue fixtures to the test collection
- **THEN** each row's `div.row-details` has exactly the pairs that its content file and the registry give, in the stated order, OSDB-0003's row has the image with its `alt` and lazy loading, no other row has an `img`, and the fixture whose compound has no CAS number has no `CAS` pair

#### Scenario: Details in a browser
- **WHEN** the orchestrator switches `/procedures/` to Details, sorts it, filters it and opens it at 500 CSS pixels in both colour schemes (manual verification, tasks.md section 6)
- **THEN** the same IDs are listed in the same order as in the table view, the image is shown only for OSDB-0003, no cell shows a broken image or an empty link, and the text stays readable
