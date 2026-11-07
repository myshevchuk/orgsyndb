## MODIFIED Requirements

### Requirement: Values beside compound links
Wherever the site writes an `a.compound`, the link to a compound's page, it SHALL follow the link with the values of the compound's fields declared `beside = true` (requirement "Field declarations") that the compound sets: one space, then a `span.compound-beside` whose text is `(`, those values in declared order, each written as the requirement "Field display" writes a value on a compound page and joined by `, `, then `)`, escaped once. A compound that sets no such field, and every compound of a collection that declares none, has no `span.compound-beside` after its link. The link's own text stays the compound's shown name. The `a.compound` links are those of the metadata panel's `Product` or `Products` and `Starting materials` (site-theme "Metadata panel"), the scope table (general-procedures "Scope table on the page"), the sequence scheme and the sequence directory (synthesis-sequences "Sequence pages"), and the route tree of a compound page (synthesis-routes "Routes on compound pages"). No other text that names a compound carries the values: not the key facts, the catalogue's details view, an image's `alt` or a page's title. `site/assets/css/base.css` gives `.compound-beside` the colour `var(--muted)`.

#### Scenario: Notes after every compound link
- **WHEN** a test scans every procedure page, every sequence page, `public/sequences/index.html` and every compound page after a theme build in locale `en`
- **THEN** each `a.compound` whose compound sets a field the test collection's `orgsyndb.toml` declares with `beside = true` is followed by a text node holding one space and then a `span.compound-beside` whose text is computed as stated from the registry and the field data, each other `a.compound` is followed by no `span.compound-beside`, and each link's text is its compound's shown name
- **AND** the `Product` value of `procedures/osdb-0002/index.html` reads `Acetylsalicylic acid (CH-0010, ASA)` and its `Starting materials` value `Salicylic acid, Acetic anhydride (Ac2O)`

#### Scenario: A number beside a German link
- **WHEN** a test builds a copy of the test collection in locale `de` after adding `beside = true` to the declaration of `stock` in its `orgsyndb.toml`, and reads `procedures/osdb-0007/index.html`
- **THEN** the `a.compound` to `ethyl-triphenylphosphoranylidene-acetate` in its `Ausgangsstoffe` value is followed by a `span.compound-beside` with the text `(12,5 g)`

#### Scenario: Markup in a value, and a compound without one
- **WHEN** a test builds a copy of the test collection in locale `en` after removing `beside = true` from the declaration of `item_number` in its `orgsyndb.toml` and setting the `short_name` of `acetone` to `<i>Me</i>2CO & co`, and reads `procedures/osdb-0006/index.html` and `procedures/osdb-0002/index.html`
- **THEN** the `a.compound` to `acetone` in the `Starting materials` value of OSDB-0006 is followed by a `span.compound-beside` whose text is `(<i>Me</i>2CO & co)`, and the value holds no `i` element
- **AND** the `Starting materials` value of OSDB-0002 reads `Salicylic acid, Acetic anhydride (Ac2O)`, and no `span.compound-beside` follows the `a.compound` to `salicylic-acid`, which sets no `short_name`

#### Scenario: The note is muted
- **WHEN** a test reads `site/assets/css/base.css`
- **THEN** a rule whose selector is `.compound-beside` sets `color: var(--muted)`
