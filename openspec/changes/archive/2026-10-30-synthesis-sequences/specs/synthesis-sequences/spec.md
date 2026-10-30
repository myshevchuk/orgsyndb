## ADDED Requirements

### Requirement: Sequence files
A collection's synthesis sequences SHALL be the files of its directory `md/sequences/`, each a Markdown file with `+++` TOML front matter named `SEQ-NNNN-short-slug.md`, the short slug matching `[a-z0-9]+(-[a-z0-9]+)*` and `SEQ-NNNN` equal to the file's `id`. A name MAY carry a language code, `de` or `en`, before its suffix, as a procedure's may: files with the same `id` are variants of one sequence, with the same base name and the same `target` and `steps`, checked and reported as localization "Procedure variants" checks procedures; title, dates and body may differ. A sequence carries no `authors`, so that it never joins the author taxonomy of the procedures; its steps credit their own authors. The build publishes one variant per ID, chosen as localization "Choosing the variant to publish" chooses a procedure's, and stages it in the collection's `build/content/sequences/`. The validator reads them from the directory its `--sequences` option names, and discovers them as it discovers procedures (procedure-validation "File discovery"), with `not a sequence file; ignored` for a file of another name. Front matter is parsed as for procedures, and a problem is reported on the sequence file's path. A file name that breaks the rule is a `file_name` error containing `must be named SEQ-NNNN-short-slug.md`, or `does not match id <id>`.

#### Scenario: Sequence file named after another ID
- **WHEN** a sequence fixture run on `valid/md` with `sequences-invalid/file-name` examines `SEQ-0002-mismatch.md`, whose `id` is `"SEQ-0003"`
- **THEN** it reports exactly one error, field `file_name`, containing `does not match id SEQ-0003`

#### Scenario: A German variant shares its steps
- **WHEN** a sequence variant run adds a `.de` variant of the baseline with a German title and body and, in a second run, also sets its `target` to `ethanol`
- **THEN** the first exits 0 and prints nothing, and the second reports exactly one error, on the German file, field `target`, naming the English file

### Requirement: Sequence fields
Every sequence SHALL carry these front-matter keys:
- `id`: a string matching `SEQ-NNNN`, four digits from `0001` to `9999`, used once per language code and once without one;
- `slug`: the `id` lowercased;
- `title`: a non-empty string;
- `date` and `lastmod`: offset datetimes, `lastmod` not earlier than `date`, checked as for procedures;
- `target`: a key of the compound registry, the compound the sequence makes;
- `steps`: an array of at least two tables, each holding `procedure`, the ID of a published procedure, and `entry`, an integer from 1 to the number of that procedure's scope entries, which a general procedure requires and a specific procedure refuses.

A missing key is an error containing `required field missing`. The procedure taxonomy keys `authors`, `tags` and `reaction_types` are errors containing `must not be set; a sequence joins no procedure taxonomy`, so that no build publishes a sequence among the procedures of a term page. Any other key is a warning containing `unknown field`, and any other key in a step a warning under `steps[n].<key>`. The messages are:
- `id`: `must match SEQ-NNNN` or `duplicate id <id>, also used by <path>`;
- `slug`: `must be "<value>" (the lowercased id)`;
- `target`: `unknown compound "<key>"`;
- `steps`: `must list at least two steps`;
- `steps[n].procedure`: `<id> not found in any content root`;
- `steps[n].entry`: `OSDB-NNNN is a general procedure; name one of its entries 1 to <count>`, `OSDB-NNNN has no scope entries`, or `must be between 1 and <count>`.

#### Scenario: Valid sequences
- **WHEN** a sequence fixture run on `valid/md` and `sequences-procedures` with `sequences` examines the committed sequences, one of them with a step that names entry 2 of the general baseline
- **THEN** it exits 0 and prints nothing to stdout

#### Scenario: Step of an unknown procedure
- **WHEN** a sequence variant run sets the second step's `procedure` to `OSDB-0999`
- **THEN** it reports exactly one error, field `steps[2].procedure`, containing `OSDB-0999 not found`

#### Scenario: General procedure without an entry
- **WHEN** a sequence variant run removes `entry` from the step that names the general baseline
- **THEN** it reports exactly one error on that step's `entry` containing `is a general procedure`

#### Scenario: One step only
- **WHEN** a sequence variant run keeps only the first step
- **THEN** it reports exactly one error, field `steps`, containing `must list at least two steps`

### Requirement: Sequence continuity
Each step of a sequence after the first SHALL start from a product of the step before it: some product of step `k` (of its entry, for a general procedure) is among the substrates of step `k+1` (of its entry). The compound that does so is the step's intermediate; when several do, the first in the products' order. The `target` SHALL be among the products of the last step. Problems are errors: `steps[k+1]` containing `starts from none of the products of step <k>`, and `target` containing `is not a product of the last step`. A step whose procedure is not found, or whose entry is missing or out of range, is left out of these checks. They run only on the reference variant of a sequence (localization "Procedure variants"), whose other variants must equal it, only when `steps` holds at least two tables, and the target check only when `target` is a registry key.

The fixture `tests/fixtures/sequences/SEQ-0001-baseline.md` is the sequence baseline, a valid two-step sequence; a sequence variant run changes it unless the scenario names another sequence.

#### Scenario: Broken chain
- **WHEN** a sequence variant run swaps its two steps
- **THEN** it reports one error on `steps[2]` containing `starts from none of the products of step 1`, and one on `target` containing `is not a product of the last step`

### Requirement: Sequence pages
The site SHALL publish every sequence at `/sequences/<slug>/`, whose `main` holds, in this order:
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

### Requirement: Sequences beside procedures and compounds
A procedure's metadata panel SHALL hold, after `Used in`, the pair `Sequences`, with one `a.sequence` per sequence that has the procedure as a step, linking its page with its title, by ID, and only when there is one. A compound page SHALL hold, after its `Used in` section, `section.compound-sequences` with the `h2` `Sequences` and a `ul` with one `li` per sequence whose `target` is the compound, by ID, linking its page with its title, only when there is one.

#### Scenario: Links to the demo sequence
- **WHEN** a test reads the pages of OSDB-0001, OSDB-0002 and the compound `acetylsalicylic-acid` after a theme build
- **THEN** both procedure panels have a `Sequences` pair linking `SEQ-0001`, and the compound page's `section.compound-sequences` links it

### Requirement: Sequence template
The file `templates/sequence.md` SHALL be a complete sequence using the placeholder ID `SEQ-0000` and slug `seq-0000`, whose front matter explains every key in TOML comments. Once `SEQ-0000` and `seq-0000` are replaced by a real ID and its lowercase form, and its two steps name existing procedures that chain, it validates with no error and no warning.

#### Scenario: Template validates
- **WHEN** a test copies `templates/sequence.md` into a temporary sequences directory as `SEQ-0001-template.md`, replaces the placeholders, and validates it against a copy of the test collection whose steps and target it names
- **THEN** it exits 0 and prints nothing to stdout
