# compound-fields Specification

## Purpose
Define the four registry fields every compound has: their values from the substance, the field data the build stages for the site, how the site writes a value, and the values written beside links to a compound.
## Requirements
### Requirement: Field data for the site
`pipeline.fields_data(settings, registry, language)` SHALL return the field data that the build stages as `build/data/fields.json` (build-script "build subcommand"), given the path of the collection's settings file, the collection's registry (compound-registry "Reading the registry") and the site's language. The data is a table whose keys are `compound` and `procedure`, and no other. `procedure` is as procedure-fields "Procedure field data" states. `compound` holds one table per registry field (Registry fields), in their order, each with these keys and no other:
- `key`, `type` and `column`, as Registry fields states them;
- `facet`: only for a `choice` field;
- `search` and `beside`: only for a `text` field;
- `label`: the field's shown label, the German one on a German site and the English one otherwise;
- `multiple` and `tabs`: only for a `choice` field;
- `values`: only for a `choice` field, a table holding every term of its vocabulary in the registry under the term's key, each a table of `label`, the term's shown label, its `label_de` on a German site when it has one and its `label` otherwise; `path`, the shown labels of the term's ancestors, outermost first, followed by its own; and `ancestors`, the keys of its ancestors, outermost first;
- `order`: only for a `choice` field, the keys of every term of its vocabulary, each top-level term followed by the terms filed under it, recursively, siblings in key order.

A settings file that does not exist, or that declares no procedure field, gives `procedure` the journal fields alone (procedure-fields "Journal fields"); `compound` always lists the four registry fields.

#### Scenario: Field data in both languages
- **WHEN** a test calls `fields_data` on the test collection's `orgsyndb.toml` and registry with the language `en`, and again with `de`
- **THEN** each lists under `compound` the four registry fields in order with the stated keys; `chemical_class` has `multiple` `true`, `column` `true` and `facet` `true`; `group` has `tabs` `true` and `multiple` `false`
- **AND** in `en` the term `ketones` of `chemical_class` has the label `Ketones` and the path `["Carbonyl compounds", "Ketones"]`, and in `de` the label `Ketone` and the path `["Carbonylverbindungen", "Ketone"]`; `article_number` has the label `Article no.` in `en` and `Artikelnr.` in `de`
- **AND** `article_number` and `short_name` have `search` `true` and `beside` `true`, the term `ketones` has the `ancestors` `["carbonyl-compounds"]`, and the `order` of `chemical_class` begins with `alcohols`, `aryl-halides`, `carbonyl-compounds`, `acid-derivatives`, `anhydrides` and `esters`

#### Scenario: Depth-first order
- **WHEN** a test calls `fields_data` with a registry whose chemical classes are `esters` and `ketones` under `carbonyl-compounds`, `alcohols`, and `aryl-ketones` under `ketones`
- **THEN** the `order` of `chemical_class` is `["alcohols", "carbonyl-compounds", "esters", "ketones", "aryl-ketones"]`, and `aryl-ketones` has the `ancestors` `["carbonyl-compounds", "ketones"]`

#### Scenario: No settings file
- **WHEN** a test calls `fields_data` on a path that does not exist, with the test collection's registry
- **THEN** its `procedure` lists the two journal fields alone and its `compound` lists the four registry fields

### Requirement: Field display
The site SHALL name a field, a registry field or a declared procedure field, by its shown label (requirement "Field data for the site") and write a value of it as text, escaped once, as follows:
- `text`: the value;
- `number`: the value written as the compound facts write the molecular weight, with the language's decimal separator, followed by a space and the `unit` when the field declares one;
- `boolean`: `Yes` or `No`, on a German site `Ja` or `Nein`;
- `choice`: on a compound page, the labels of each value's `path` joined by ` › `; in the compound directory, each value's own label. Several values are written in the compound's order, separated by `, `.

#### Scenario: Registry fields in English
- **WHEN** a test scans every compound page and the compound directory after a theme build in locale `en`
- **THEN** each value of a registry field that a substance has is written as stated, computed from the test collection's registry and field data

#### Scenario: Registry fields in German
- **WHEN** a test reads the compound pages of a build of the test collection in locale `de`
- **THEN** the registry fields carry their German labels, and a chemical class reads as the German labels of its path joined by ` › `

#### Scenario: Markup in a label or a value is text
- **WHEN** a test builds a copy of the test collection in locale `en` after setting the `short_name` of `acetone` in its registry to `<i>Me</i>2CO & co` and the `label` of the chemical class `ketones` to `Ketones <b>&</b>`
- **THEN** the facts of the page of `acetone` hold a `dd` whose text is `<i>Me</i>2CO & co`, the page of a ketone shows its class as text ending in `Ketones <b>&</b>`, and neither page holds a `b` or `i` element

### Requirement: Values beside compound links
Wherever the site writes an `a.compound`, the link to a compound's page, it SHALL follow the link with the values of the registry fields shown beside a link (Registry fields), the article number and the short name, that the substance has: one space, then a `span.compound-beside` whose text is `(`, those values in declared order, each written as the requirement "Field display" writes a value on a compound page and joined by `, `, then `)`, escaped once. A substance that has neither has no `span.compound-beside` after its link. The link's own text stays the compound's shown name. The `a.compound` links are those of the metadata panel's `Product` or `Products` and `Starting materials` (site-theme "Metadata panel"), the scope table (general-procedures "Scope table on the page"), the sequence scheme and the sequence directory (synthesis-sequences "Sequence pages"), and the route tree of a compound page (synthesis-routes "Routes on compound pages"). No other text that names a compound carries the values: not the key facts, the catalogue's details view, an image's `alt` or a page's title. `site/assets/css/base.css` gives `.compound-beside` the colour `var(--muted)`.

#### Scenario: Notes after every compound link
- **WHEN** a test scans every procedure page, every sequence page, `public/sequences/index.html` and every compound page after a theme build in locale `en`
- **THEN** each `a.compound` whose substance has an article number or a short name in the test collection's registry is followed by a text node holding one space and then a `span.compound-beside` whose text is computed as stated from the registry and the field data, each other `a.compound` is followed by no `span.compound-beside`, and each link's text is its compound's shown name
- **AND** the `Product` value of `procedures/osdb-0002/index.html` reads `Acetylsalicylic acid (CH-0010, ASA)` and its `Starting materials` value `Salicylic acid, Acetic anhydride (Ac2O)`

#### Scenario: Markup in a value, and a compound without one
- **WHEN** a test builds a copy of the test collection in locale `en` after setting the `short_name` of `acetone` in its registry to `<i>Me</i>2CO & co`, and reads `procedures/osdb-0006/index.html` and `procedures/osdb-0002/index.html`
- **THEN** the `a.compound` to `acetone` in the `Starting materials` value of OSDB-0006 is followed by a `span.compound-beside` whose text is `(<i>Me</i>2CO & co)`, and the value holds no `i` element
- **AND** the `Starting materials` value of OSDB-0002 reads `Salicylic acid, Acetic anhydride (Ac2O)`, and no `span.compound-beside` follows the `a.compound` to `salicylic-acid`, which has neither an article number nor a short name

#### Scenario: The note is muted
- **WHEN** a test reads `site/assets/css/base.css`
- **THEN** a rule whose selector is `.compound-beside` sets `color: var(--muted)`

### Requirement: Registry fields
The tools SHALL give every compound four fields from its substance in the collection's registry, in this order, with these types, labels and presentation:

| key | value | type | label (English, German) | presentation |
|---|---|---|---|---|
| `article_number` | the substance's `article_number` | `text` | `Article no.`, `Artikelnr.` | `column`, `search`, `beside` |
| `short_name` | its `short_name` | `text` | `Short name`, `Kurzname` | `search`, `beside` |
| `chemical_class` | its `chemical_classes`, in their order | `choice`, `multiple`, vocabulary `chemical-classes` | `Chemical class`, `Stoffklasse` | `column`, `facet` |
| `group` | its `group` | `choice`, vocabulary `inventory-groups` | `Group`, `Gruppe` | `facet`, `tabs` |

A field marked `column` is a column of the compound directory (site-theme "Compound directory"); `search` makes the compound catalogue's search match its values; `beside` writes its value after links to the compound (Values beside compound links); `facet` offers it as a filter of the catalogue; and `tabs` divides the compound directory into tabs by its top-level terms (site-catalogue "Compound tabs"). A substance without a value of a field does not have that field. A collection declares no compound field: `fields.compound` in `orgsyndb.toml` is a configuration error naming `fields.compound` (procedure-fields "Procedure declaration errors are configuration errors").

#### Scenario: Fields of a numbered substance
- **WHEN** the test collection is built and its registry gives `acetylsalicylic-acid` the article number `CH-0010`, the short name `ASA`, a chemical class and a group
- **THEN** its compound page lists the four fields with those values, and the compound directory shows `CH-0010` and the class in their columns

