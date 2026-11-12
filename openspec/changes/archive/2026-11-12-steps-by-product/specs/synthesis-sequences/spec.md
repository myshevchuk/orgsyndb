## MODIFIED Requirements

### Requirement: Sequence files
A collection's synthesis sequences SHALL be the files of its directory `md/sequences/`, each a Markdown file with `+++` TOML front matter named `SEQ-NNNN-short-slug.md`, the short slug matching `[a-z0-9]+(-[a-z0-9]+)*` and `SEQ-NNNN` equal to the file's `id`. A name MAY carry a language code, `de` or `en`, before its suffix, as a procedure's may: files with the same `id` are variants of one sequence, with the same base name and the same `target` and `steps`, compared as written, lists in order, checked and reported as localization "Procedure variants" checks procedures; title, dates and body may differ. A sequence carries no `authors`, so that it never joins the author taxonomy of the procedures; its steps credit their own authors. The build publishes one variant per ID, chosen as localization "Choosing the variant to publish" chooses a procedure's, and stages it in the collection's `build/content/sequences/`. The validator reads them from the directory its `--sequences` option names, and discovers them as it discovers procedures (procedure-validation "File discovery"), with `not a sequence file; ignored` for a file of another name. Front matter is parsed as for procedures, and a problem is reported on the sequence file's path. A file name that breaks the rule is a `file_name` error containing `must be named SEQ-NNNN-short-slug.md`, or `does not match id <id>`.

#### Scenario: Sequence file named after another ID
- **WHEN** a sequence fixture run on `valid/md` with `sequences-invalid/file-name` examines `SEQ-0002-mismatch.md`, whose `id` is `"SEQ-0003"`
- **THEN** it reports exactly one error, field `file_name`, containing `does not match id SEQ-0003`

#### Scenario: A German variant shares its steps
- **WHEN** a sequence variant run adds a `.de` variant of the baseline with a German title and body and, in a second run, also sets its `target` to `ethanol`
- **THEN** the first exits 0 and prints nothing, and the second reports exactly one error, on the German file, field `target`, naming the English file

### Requirement: Sequence continuity
Each step of a sequence after the first SHALL start from a product of the step before it: some product of step `k` (of its entry, for a general procedure) is among the substrates of step `k+1` (of its entry). The compound that does so is the step's intermediate; when several do, the first in the products' order. The `target` SHALL be among the products of the last step. Problems are errors: `steps[k+1]` containing `starts from none of the products of step <k>`, and `target` containing `is not a product of the last step`. A step whose procedure is not found, or whose entry cannot be resolved (Sequence fields), is left out of these checks. A step named by its full signature takes its intermediate in the order of its entry's products, not in the order the step lists them. They run only on the reference variant of a sequence (localization "Procedure variants"), whose other variants must equal it, only when `steps` holds at least two tables, and the target check only when `target` is a registry key.

The fixture `tests/fixtures/sequences/SEQ-0001-baseline.md` is the sequence baseline, a valid two-step sequence; a sequence variant run changes it unless the scenario names another sequence.

#### Scenario: Broken chain
- **WHEN** a sequence variant run swaps its two steps
- **THEN** it reports one error on `steps[2]` containing `starts from none of the products of step 1`, and one on `target` containing `is not a product of the last step`

#### Scenario: A reordered scope table
- **WHEN** a variant run moves the second entry of the general baseline to the end of its scope table, leaving the sequence that names it by `benzyl-acetate` as it is
- **THEN** it reports nothing, the step resolves to entry 3, and the manifest's step gives entry 3

### Requirement: Sequence fields
Every sequence SHALL carry these front-matter keys:
- `id`: a string matching `SEQ-NNNN`, four digits from `0001` to `9999`, used once per language code and once without one;
- `slug`: the `id` lowercased;
- `title`: a non-empty string;
- `date` and `lastmod`: offset datetimes, `lastmod` not earlier than `date`, checked as for procedures;
- `target`: a key of the compound registry, the compound the sequence makes;
- `steps`: an array of at least two tables, each holding `procedure`, the ID of a published procedure, and, for a general procedure only, the scope entry it carries out, named by its chemistry: `product`, a compound key that is a product of exactly one of the procedure's entries, or, where a product alone names more than one, `substrates` and `products`, lists of compound keys that are exactly the substrates and the product compounds of one entry, in any order. A step names its entry one way or the other, not both, and its lists name no compound twice; a specific procedure refuses all three keys. The entry a step names is its step's entry; the build and the manifest give it by its number, counted from 1 in file order.

A missing key is an error containing `required field missing`. The procedure taxonomy keys `authors`, `tags` and `reaction_types` are errors containing `must not be set; a sequence joins no procedure taxonomy`, so that no build publishes a sequence among the procedures of a term page. Any other key is a warning containing `unknown field`, and any other key in a step a warning under `steps[n].<key>`. The messages are:
- `id`: `must match SEQ-NNNN` or `duplicate id <id>, also used by <path>`;
- `slug`: `must be "<value>" (the lowercased id)`;
- `target`: `unknown compound "<key>"`;
- `steps`: `must list at least two steps`;
- `steps[n].procedure`: `<id> not found in any content root`;
- `steps[n].product`: `OSDB-NNNN is a general procedure; name its entry by a product: <keys>`, listing the products of its entries in file order; `<key> is a product of no entry of OSDB-NNNN`; `<key> is a product of entries <m> and <n> of OSDB-NNNN; name the entry by its substrates and products`; or `OSDB-NNNN has no scope entries; remove product`;
- `steps[n].substrates` and `steps[n].products`: `no entry of OSDB-NNNN has these substrates and products`, `must be given with products` or `with substrates`, `must be a list of compound keys`, `must not list a compound twice`, or `OSDB-NNNN has no scope entries; remove <key>`;
- `steps[n]`: `name the entry by product or by substrates and products, not both`;
- `steps[n].entry`: `not a key of a step; name the entry by its product`.

#### Scenario: Valid sequences
- **WHEN** a sequence fixture run on `valid/md` and `sequences-procedures` with `sequences` examines the committed sequences, one of them with a step that names entry 2 of the general baseline by its product `benzyl-acetate`
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Step of an unknown procedure
- **WHEN** a sequence variant run sets the second step's `procedure` to `OSDB-0999`
- **THEN** it reports exactly one error, field `steps[2].procedure`, containing `OSDB-0999 not found`

#### Scenario: General procedure without an entry
- **WHEN** a sequence variant run removes `product` from the step that names the general baseline
- **THEN** it reports exactly one error on that step's `product` containing `is a general procedure` and `benzyl-acetate`

#### Scenario: A product of two entries
- **WHEN** a variant run gives the third entry of the general baseline the product `benzyl-acetate` in place of `methyl-benzoate`, so that the step naming it by `benzyl-acetate` names two entries
- **THEN** it reports exactly one error on that step's `product` containing `entries 2 and 3` and `substrates and products`, and naming the entry by `substrates = ["acetic-acid"]` and `products = ["propyl-acetate", "benzyl-acetate"]` reports nothing

#### Scenario: An entry number
- **WHEN** a sequence variant run gives the step that names the general baseline `entry = 2` in place of its product
- **THEN** it reports an error on that step's `entry` containing `name the entry by its product`

#### Scenario: One step only
- **WHEN** a sequence variant run keeps only the first step
- **THEN** it reports exactly one error, field `steps`, containing `must list at least two steps`

### Requirement: Sequence pages
The build SHALL stage each sequence with every step of a general procedure carrying `entry`, the number, counted from 1, of the entry it names (Sequence fields), so that the pages read the entry by its number. The site SHALL publish every sequence at `/sequences/<slug>/`, whose `main` holds, in this order:
- `header.sequence-header`, holding `p.sequence-id` with the ID, the `h1` with the title, and `dl.key-facts` with the pairs `Steps`, the number of steps, and `Overall yield`, the product of each step's yield of its intermediate and of the last step's yield of the target, as a percentage rounded once to the nearest whole number, halves up, `<n> %`;
- `figure.sequence-scheme`, holding an `ol` whose items are, in order: `li.sequence-compound` items for the substrates of the first step, then for each step a `li.sequence-step` and a `li.sequence-compound` for its intermediate, or for the target after the last step. A compound item holds, when the compound sets `structure_image`, an `img` with `alt` `Structure of <name>`, and an `a.compound` linking its page with its shown name. A step item holds `Step <k>`, the reaction-type label of its procedure and its yield of the following compound as `<n> %`;
- `ol.sequence-steps`, with one `li` per step: an `a` linking the procedure's page with the text `<ID> <title>`, then, for a general procedure, ` · entry <n>`, then ` · ` and the reaction-type label, ` · ` and the step's yield as `<n> %`, and ` · ` and the procedure's status badge;
- the rendered body.

A sequence page carries no `data-pagefind-body`. The page `/sequences/` holds the `h1` `Sequences` and a `table.sequence-table` with the header cells `Sequence`, `Target`, `Steps` and `Overall yield`, and one row per sequence by ID: a link to its page with its title, an `a.compound` for the target, the number of steps and the overall yield.

#### Scenario: Sequence page of the demo
- **WHEN** a test scans the page of `SEQ-0001` after a theme build in locale `en`
- **THEN** its key facts are `Steps` `2` and `Overall yield` `60 %`, its scheme lists `Methyl salicylate`, step 1, `Salicylic acid`, step 2 and `Acetylsalicylic acid`, and its steps link OSDB-0001 and OSDB-0002 in order

#### Scenario: Step of a general procedure
- **WHEN** a test scans the page of the demo sequence whose second step names an entry of a general procedure
- **THEN** that step's list item reads `entry <n>` after the title, and the scheme's following compound is that entry's product

#### Scenario: A German sequence page
- **WHEN** a test scans the page of `SEQ-0002` after a build of the test collection in locale `de`
- **THEN** its `h1` is the German variant's title, its key facts read `Stufen` `2` and `Gesamtausbeute` `77 %`, and its second step reads `Eintrag 1`

#### Scenario: Directory lists every sequence
- **WHEN** a test scans `public/sequences/index.html` after the same build
- **THEN** it has one row per sequence, by ID, with the stated cells
