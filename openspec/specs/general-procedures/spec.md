# general-procedures Specification

## Purpose
TBD - created by archiving change general-procedures. Update Purpose after archive.
## Requirements
### Requirement: Scope entries
A procedure MAY carry `scope`, a non-empty array of tables, the entries of a general procedure. A procedure with `scope` is a general procedure, and one without is a specific procedure. A general procedure SHALL NOT carry the top-level `products` or `substrates`; either is an error under its name containing `a general procedure lists them in scope`. Each entry holds:
- `substrates`: required, a non-empty list of compound keys, checked as procedure-schema "Substrates" checks the top-level field, against the entry's own products;
- `products`: required, checked as procedure-schema "Products" checks the top-level field;
- `scale`: optional, a string with the procedure-schema "Scale with unit" rule;
- `time`: optional, a string matching `^\d+([.,]\d+)?\s+(min|h|d)$`;
- `temperature`: optional, a finite number in °C (TOML integer or float; never boolean);
- `note`: optional, a non-empty string.

Entries are numbered from 1 in their order. A problem in entry `n` is reported under `scope[n].<key>`, one inside its `m`-th product under `scope[n].products[m].<key>`; an entry that is not a table is an error under `scope[n]` containing `must be a table`, and any other key in an entry is a warning containing `unknown field`. The further messages are:
- an empty array: `scope` containing `must not be empty`; a value that is not an array: `scope` containing `must be an array of tables`;
- `time`: `"<value>" must be a number followed by min, h or d, e.g. "2 h"`;
- `temperature`: `must be a number in °C, unquoted, e.g. 80`.

Validation checks each entry on its own, as stated above: the same compound may be a substrate of one entry and a product of another. For everything else the site does with a procedure's products and substrates — the metadata panel, the precursor and used-in links, the compound pages and directory, the catalogue's Details view, the index terms and the SMILES index — the products of a general procedure are those of all its entries, and its substrates those of all its entries, each compound once, in the order of first appearance.

The fixture `tests/fixtures/general/OSDB-0140-general.md` is the general baseline: a valid general procedure of three entries, the first with every optional key, the second with two products, the third with none of the optional keys. A general variant run writes it, with the stated change, as the only file of a fresh temporary content root and makes a fixture run on that root (procedure-validation "Fixture suite").

#### Scenario: General baseline is valid
- **WHEN** a fixture run on `general` completes
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Top-level products in a general procedure
- **WHEN** a general variant run adds `products = [{ compound = "ethyl-acetate", yield_percent = 85 }]` under the file name `OSDB-0140-general-products.md`
- **THEN** it reports exactly one error, field `products`, containing `a general procedure lists them in scope`

#### Scenario: Entry without substrates
- **WHEN** a general variant run removes `substrates` from the second entry under the file name `OSDB-0140-no-substrates.md`
- **THEN** it reports exactly one error, field `scope[2].substrates`, containing `required field missing`

#### Scenario: Time without a unit
- **WHEN** a general variant run sets the first entry's `time = "2 hours"` under the file name `OSDB-0140-bad-time.md`
- **THEN** it reports exactly one error, field `scope[1].time`, containing `must be a number followed by min, h or d`

#### Scenario: Temperature as a string
- **WHEN** a general variant run sets the first entry's `temperature = "80 °C"` under the file name `OSDB-0140-temperature-string.md`
- **THEN** it reports exactly one error, field `scope[1].temperature`, containing `must be a number in °C`

#### Scenario: Unknown compound in an entry
- **WHEN** a general variant run sets the compound of the third entry's product to `no-such-compound` under the file name `OSDB-0140-unknown.md`
- **THEN** it reports exactly one error, field `scope[3].products[1].compound`, containing `unknown compound "no-such-compound"`

#### Scenario: Empty scope
- **WHEN** a general variant run sets `scope = []` under the file name `OSDB-0140-empty-scope.md`
- **THEN** it reports exactly one error, field `scope`, containing `must not be empty`

### Requirement: Org scope table
In an Org source, the scope SHALL be written as an Org table directly preceded by the keyword line `#+NAME: scope`, the name compared case-insensitively, anywhere outside blocks. Its first row names the columns and a separator line follows it; every further row is an entry, in order. The columns are the entry keys `substrates`, `products`, `yield_percent`, `scale`, `time`, `temperature` and `note`, each at most once, the first three required. In a row:
- `substrates` and `products` hold compound keys separated by spaces;
- `yield_percent` holds one number per product, separated by spaces, in the order of `products`;
- `temperature` holds one number;
- `scale`, `time` and `note` hold their text, trimmed;
- a number may be written with a decimal comma (`45,5`);
- an empty cell leaves its key unset.

The export writes the entries as the `scope` front matter, each product as `{ compound, yield_percent }`, and within each entry writes `products` after the entry's other keys, so that tomelr does not place them inside the last product table. It leaves the table and its `#+NAME` line out of the exported body. It reports these problems of the source, as errors with field `scope`, under org-export "Org sources and their problems", so that a source with one is not exported:
- a second table named `scope`: `appears more than once`;
- a column outside the seven: `"<name>" is not a scope column`;
- a column named twice: `column "<name>" appears more than once`;
- a required column missing: `column "<name>" missing`;
- a row whose number of yields differs from its number of products: `row <n>: <p> products but <y> yields`;
- a yield or temperature that is not a number: `row <n>: "<cell>" is not a number`.

Rows are counted from 1 after the separator line.

#### Scenario: Scope table exports to front matter
- **WHEN** an integration test exports `tests/fixtures/export/OSDB-0909-scope-table.org`, whose table named `scope` has the columns `substrates`, `products`, `yield_percent`, `time`, `temperature` and `note` and three rows, one with two products and the yields `45,5 30`, one with an empty `time` cell
- **THEN** `tomllib` parses its export with a `scope` of three tables whose keys and values equal those the rows give, `45.5` and `30` among them, and with no `time` key in the entry whose cell was empty
- **AND** the exported body contains no table row of the scope table and no `#+NAME`

#### Scenario: Malformed scope tables
- **WHEN** an ERT test examines, each alone in a temporary directory `R`, copies of `tests/fixtures/export/OSDB-0909-scope-table.org` with, in turn, a column `solvent` added; the `products` column removed; the first row's `yield_percent` cell set to `45`; its `temperature` cell set to `hot`; and a second table named `scope` added
- **THEN** the problem lines are exactly, in turn, with `P` for `R/OSDB-0909-scope-table.org`: `P:scope: error: "solvent" is not a scope column`; `P:scope: error: column "products" missing`; `P:scope: error: row 1: 2 products but 1 yields`; `P:scope: error: row 1: "hot" is not a number`; and `P:scope: error: appears more than once`

### Requirement: Scope table on the page
A general procedure's page SHALL hold, inside `article.procedure` after the details wrapper and before the rendered body, a `section.scope` with the `h2` `Scope` and a `table.scope-table`. Its header cells are `Entry`, `Starting materials`, `Products` and `Yield`, then `Scale`, `Time`, `Temperature` and `Note`, each of the last four only when some entry sets its key. Each entry gives one body row, in order, whose cells hold:
- the entry's number;
- one `a.compound` per substrate, linking its compound page with the compound's shown name, joined by `, `;
- per product, when its compound sets `structure_image`, an `img.scope-structure` with `alt` `Structure of <name>`, `loading="lazy"` and `decoding="async"`, then an `a.compound` linking its compound page with its shown name; the products separated by `, `;
- the yields as `<n> %`, in product order, joined by `, `;
- the scale, the time, the temperature as `<t> °C` and the note, as set, an unset key giving an empty cell.

Numbers are written with the site language's decimal separator. A specific procedure's page has no `section.scope`.

#### Scenario: Scope table of a general procedure
- **WHEN** a test scans the page of the test collection's general procedure after a theme build in locale `en`
- **THEN** its `section.scope` lies between the details wrapper and the `Summary` heading, its header cells are those its entries' keys call for, in order, and its rows give each entry's compounds, links, yields and deviations as stated

#### Scenario: No scope table on a specific procedure
- **WHEN** a test scans every other procedure page of the same build
- **THEN** none has a `section.scope`

### Requirement: General procedures view
The site SHALL publish `/general-procedures/`, a catalogue page whose rows are the published general procedures, by ID, with the `kind` facet fixed to `general` as a term page fixes its term (site-catalogue "Catalogue pages" and "Fixed scope on term pages"). It opens with the section tabs (site-theme "Procedure section tabs") and lies in `/procedures/` for the navigation. Its `h1` and display title are `General procedures`; its scope line reads `Only general procedures`, then ` · ` and the `Browse all procedures` link; its header search is labelled `Search general procedures` with the placeholder `Search these procedures`.

#### Scenario: The view lists the general procedures
- **WHEN** a test scans `public/general-procedures/index.html` after a theme build in locale `en`
- **THEN** its rows are exactly the published general procedures, by ID, its fixed facet is `kind` with the one checked, disabled value `general`, and its scope line and header search carry the stated texts

