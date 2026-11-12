## MODIFIED Requirements

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

Validation checks each entry on its own, as stated above: the same compound may be a substrate of one entry and a product of another. Two entries of one procedure SHALL NOT have the same substrates and the same product compounds, each compared as a set, so that a sequence step's full signature names exactly one entry (synthesis-sequences "Sequence fields") and the import's signatures stay unique (collection-import "Import checks"); the later of two such entries is an error under `scope[n]` containing `the same substrates and products as entry <m>`. For everything else the site does with a procedure's products and substrates — the metadata panel, the precursor and used-in links, the compound pages and directory, the catalogue's Details view, the index terms and the SMILES index — the products of a general procedure are those of all its entries, and its substrates those of all its entries, each compound once, in the order of first appearance. The steps of a derived route are the exception: each entry is a step of its own, starting from that entry's substrates only (synthesis-routes "Derived routes").

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

#### Scenario: Two entries of one signature
- **WHEN** a general variant run gives the third entry the substrates `["acetic-acid"]` and the products `propyl-acetate` and `benzyl-acetate`, the second entry's compounds in another order, under the file name `OSDB-0140-same-signature.md`
- **THEN** it reports exactly one error, field `scope[3]`, containing `the same substrates and products as entry 2`
