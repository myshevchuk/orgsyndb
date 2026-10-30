## MODIFIED Requirements

### Requirement: Seed procedures
The repository SHALL ship at least these two seed procedures, linked through the compound one makes and the other starts from, across the two source trees:
- `org/procedures/OSDB-0001-salicylic-acid.org`: salicylic acid by hydrolysis of methyl salicylate with aqueous sodium hydroxide, then acidification. `reaction_types` is `["hydrolysis"]`, `substrates` is `["methyl-salicylate"]`, and its one product is `salicylic-acid` (C7H6O3, MW 138.12, CAS `69-72-7`).
- `md/procedures/OSDB-0002-aspirin.md`: acetylsalicylic acid by acetylation of salicylic acid with acetic anhydride and a phosphoric acid catalyst. `reaction_types` is `["acylation"]`, `substrates` is `["salicylic-acid", "acetic-anhydride"]`, and its one product is `acetylsalicylic-acid` (C9H8O4, MW 180.16, CAS `50-78-2`).

#### Scenario: Seeds exist with their link
- **WHEN** a test reads the two seed files, taking the Org seed's custom-front-matter lines from the source
- **THEN** both exist, their `id` values are `OSDB-0001` and `OSDB-0002`, their reaction types are `hydrolysis` and `acylation`, the Org seed's one product is `salicylic-acid`, and the Markdown seed's `substrates` is `["salicylic-acid", "acetic-anhydride"]`

### Requirement: Quantities agree
Every sample procedure's Reagents table SHALL have the columns `Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv`, or `Reagenz | CAS | M (g/mol) | Menge | mmol | Äquiv.` in a German sample, and its numbers SHALL agree with each other and with the front matter. A German table may write decimal commas. A row whose `mmol` or `Equiv` is `cat.` (German `kat.`) is a catalyst and is exempt from the rules below.
- **Mass and moles.** Where `Amount` begins with a mass `<number> g`, `mmol` equals `1000 × mass / MW` within 1 %.
- **Limiting reagent.** Exactly one row has `Equiv` `1.0`. Every other row's `Equiv` equals its `mmol` divided by that row's `mmol`, within 0.05.
- **Scale.** When `scale` is given in `mmol`, its number equals the limiting row's `mmol` within 1 %.
- **Compound weights.** The `mw` of every compound of the demo registry equals the formula weight of its `formula`, computed from standard atomic weights (B 10.81, C 12.011, H 1.008, N 14.007, O 15.999, Na 22.990, P 30.974, S 32.06, Cl 35.45, K 39.098, Br 79.904), within 0.02 g/mol.
- **CAS numbers.** Every CAS number in the table passes the CAS check-digit rule.

#### Scenario: Seed tables are consistent
- **WHEN** a test parses the Reagents table of every sample procedure, in either language (an Org table or a Markdown pipe table, in the source file), reads every compound file of the demo registry, and applies the rules above
- **THEN** every rule holds for every row and every compound

#### Scenario: Translated sample tables are consistent (checker)
- **WHEN** a test gives the checker a German table with decimal commas and `kat.` rows, then the same table with a wrong `mmol`, then an English table under a German file name
- **THEN** it accepts the first and rejects the other two

<!-- Reason: the counts are of the English originals. -->

### Requirement: Theme sample set
The repository SHALL ship, besides the two seeds, these six sample procedures:

| File | Product | Reaction type | Substrates |
|---|---|---|---|
| `org/procedures/OSDB-0003-isopentyl-acetate.org` | `isopentyl-acetate` (C7H14O2, CAS `123-92-2`), by Fischer esterification of isopentyl alcohol with acetic acid | `esterification` | `isopentyl-alcohol`, `acetic-acid` |
| `org/procedures/OSDB-0004-4-acetylbiphenyl.org` | `4-acetylbiphenyl` (C14H12O, CAS `92-91-1`), by Suzuki coupling of 4′-bromoacetophenone with phenylboronic acid | `cross-coupling` | `4-bromoacetophenone`, `phenylboronic-acid` |
| `md/procedures/OSDB-0005-1-biphenyl-4-yl-ethanol.md` | `1-biphenyl-4-yl-ethanol` (C14H14O, CAS `3562-73-0`), by sodium borohydride reduction of 4-acetylbiphenyl | `reduction` | `4-acetylbiphenyl` |
| `md/procedures/OSDB-0006-dibenzylideneacetone.md` | `dibenzylideneacetone` (C17H14O, CAS `538-58-9`), by Claisen–Schmidt condensation of benzaldehyde with acetone | `aldol-condensation` | `benzaldehyde`, `acetone` |
| `org/procedures/OSDB-0007-ethyl-cinnamate.org` | `ethyl-cinnamate`, ethyl (E)-cinnamate (C11H12O2, CAS `103-36-6`), by Wittig olefination of benzaldehyde with ethyl (triphenylphosphoranylidene)acetate | `olefination` | `benzaldehyde`, `ethyl-triphenylphosphoranylidene-acetate` |
| `md/procedures/OSDB-0008-cinnamic-acid.md` | `cinnamic-acid`, (E)-cinnamic acid (C9H8O2, CAS `140-10-3`), by saponification of ethyl (E)-cinnamate with aqueous sodium hydroxide in ethanol, then acidification with hydrochloric acid | `hydrolysis` | `ethyl-cinnamate` |

Each procedure has the one product its row names, with the yield its previous front matter gave. The full set meets the following:
- **Counts.** There are exactly four Org and four Markdown sample procedures without a language code, with at least five distinct reaction types among them. Their German variants are not counted.
- **Compound CAS.** Every compound of the demo registry has a `cas` that resolves to that compound on PubChem. The orchestrator checks this during review, because the tests cannot reach the network.
- **Tags.** Every sample has at least one tag besides `sample-data`.
- **Structure image.** The compound `isopentyl-acetate` sets `structure_image = "structures/isopentyl-acetate.svg"`.
- **Chains.** Besides the seeds' OSDB-0001 → OSDB-0002 through `salicylic-acid`, OSDB-0004 → OSDB-0005 through `4-acetylbiphenyl` and OSDB-0007 → OSDB-0008 through `ethyl-cinnamate` are chains: the first procedure makes the compound and the second starts from it. Each chain leads from an Org procedure to a Markdown one. No other compound is both made by one sample and a substrate of another, and no procedure needs both a precursor and a used-in link.
- **Long sample.** OSDB-0004 is the long sample: at least 15 numbered steps under `Procedure` and at least 6 numbered notes under `Notes`. Its Reagents table holds at least four non-catalyst rows, and the longest cell text of its `Reagent` column has at least 40 characters.

#### Scenario: Set, counts and chain
- **WHEN** a test reads every sample procedure
- **THEN** the files above exist with those IDs, reaction types, products and substrates, there are four Org and four Markdown samples without a language code, and at least five distinct reaction types
- **AND** in every chain the procedure making the compound is an Org file and the one starting from it a Markdown file
- **AND** every compound of the demo registry has a `cas` that passes the check-digit rule, and every sample has a tag besides `sample-data`

#### Scenario: Structure image is set
- **WHEN** a test reads `compounds/isopentyl-acetate.toml` of the demo collection
- **THEN** it sets `structure_image` to `structures/isopentyl-acetate.svg`, and `static/structures/isopentyl-acetate.svg` exists

#### Scenario: Long sample
- **WHEN** a test reads `org/procedures/OSDB-0004-4-acetylbiphenyl.org`
- **THEN** its `Procedure` section has at least 15 numbered items, its `Notes` section at least 6, and its Reagents table at least four rows whose `mmol` is not `cat.`, one of them with a `Reagent` cell of at least 40 characters

### Requirement: Demo collection
The sample procedures SHALL form the demo collection `examples/demo/` of the application, a complete collection as the `collection` capability defines it, with the structure images in `examples/demo/static/structures/` and the compound registry in `examples/demo/compounds/`. The registry holds a file for every compound a sample names, as product or substrate, and no other file, and every compound sets `name_de`. Every path that this capability names under `org/procedures/` or `md/procedures/` is relative to `examples/demo/`. The application's own root holds no `org/`, `md/` or `site/static/` directory.

#### Scenario: Samples live in the demo collection
- **WHEN** a test inspects the application
- **THEN** `examples/demo/orgsyndb.toml` exists, `examples/demo/org/procedures/OSDB-0001-salicylic-acid.org` and `examples/demo/md/procedures/OSDB-0002-aspirin.md` exist, the demo registry's file names are exactly the keys the samples name, each with `.toml`, and neither `org/`, `md/` nor `site/static/` exists at the application root

### Requirement: German sample translations
Every sample procedure of the theme sample set and the seeds SHALL have a German variant beside it, in the same format, named with `.de` before the suffix (for example `org/procedures/OSDB-0001-salicylic-acid.de.org` and `md/procedures/OSDB-0002-aspirin.de.md`). Each translation meets the localization spec, carries the same `authors` as its original, has a Reagents table with as many rows as the original's, and writes decimal commas in its text and table. The German long sample has at least 15 numbered steps under `Durchführung` and at least 6 numbered notes under `Anmerkungen`.

#### Scenario: Every sample has a German translation
- **WHEN** a test reads each sample and its `.de` twin
- **THEN** the twin exists, has the same `id`, `status`, `reaction_types`, `tags`, `products`, `substrates` and `authors`, and as many table rows
- **AND** the German OSDB-0004 has at least 15 steps and 6 notes

### Requirement: Test collection
The repository SHALL ship the test collection `tests/fixtures/collection/`, a complete collection as the `collection` capability defines it that holds every sample procedure of the demo collection, in either language, as a Markdown procedure, and that has no `org/` directory. The paths in this requirement are written out in full. The test collection meets all of the following:
- **Copies.** `tests/fixtures/collection/orgsyndb.toml`, `tests/fixtures/collection/.gitignore` and every file under `tests/fixtures/collection/static/` and `tests/fixtures/collection/compounds/` are byte-identical to the demo collection's files at the same relative paths, and the test collection's `static/` and `compounds/` hold no other file.
- **File names.** `tests/fixtures/collection/md/procedures/` holds exactly one file for each sample procedure file of the demo collection, `examples/demo/org/procedures/<stem>.org` or `examples/demo/md/procedures/<stem>.md`, named `<stem>.md`, and no other file.
- **Markdown samples.** The file for a Markdown sample is byte-identical to it.
- **Converted samples.** The file for an Org sample is a hand-written Markdown procedure, in the form of the demo's Markdown samples, that agrees with its Org source as follows:
  - Its front matter has exactly the keys of the Org source's custom-front-matter lines, with equal values, `title`, `slug`, `tags`, `date` and `lastmod`, and `ai_model` exactly when `#+AI_MODEL` names a model. `title`, `slug` and `ai_model` equal `#+TITLE`, `#+HUGO_SLUG` and `#+AI_MODEL`, and `tags` lists the words of `#+HUGO_TAGS` in their order.
  - `date` and `lastmod` are offset datetimes whose local date and time equal `#+CREATED` and `#+LAST_MODIFIED`, with a Europe/Berlin offset in force at that time; where a time in the autumn fall-back hour names two instants, the offsets are those of the instants the export chooses (org-export "Exported timestamps").
  - Its body holds no text before its first heading, and its `##` headings are the Org source's top-level headings, in the same order.
  - Its Reagents table has the same rows as the Org source's, header included, each row compared as its list of stripped cells, with separator lines left out.
  - Each section's text, with its table lines left out, equals the text of the Org section of the same name once both are normalised: every run of whitespace is replaced by one space, leading and trailing whitespace is dropped, and every emphasis span is replaced by its inner text `x`. In the Org text an emphasis span is `/x/`, `*x*`, `=x=`, `~x~`, `+x+` or `_x_` as Org's emphasis syntax defines it: the opening marker follows the start of the text, whitespace or one of `-('"{`, `x` neither begins nor ends with whitespace, and the closing marker precedes the end of the text, whitespace or one of `-.,:!?;'")}\[`. In the Markdown text it is `**x**`, `*x*`, `` `x` `` or `_x_`, where `x` neither begins nor ends with whitespace and neither underscore of `_x_` is inside a word. Every other character is kept, such as the `=` of `C=O` and the `/` of `E/Z`.

Integration tests that build, validate, serve or print a collection and do not exercise the Org export SHALL work on a copy of the test collection. Integration tests that exercise the Org export work on a copy of the demo collection, and those among them that need Emacs skip when `emacs` is absent, with a reason that names it.

#### Scenario: The test collection mirrors the demo
- **WHEN** a test lists `tests/fixtures/collection/` and compares it with `examples/demo/`
- **THEN** `orgsyndb.toml`, `.gitignore` and every file under `static/` and `compounds/` are byte-identical to the demo's, `static/structures/isopentyl-acetate.svg` and `compounds/salicylic-acid.toml` among them, and no `org/` directory exists
- **AND** `md/procedures/` holds exactly the 16 file names derived from the demo's sample procedure files, and the file for each of the eight Markdown samples is byte-identical to it

#### Scenario: Converted samples agree with their Org sources
- **WHEN** a test reads each of the eight Org samples of the demo collection, in either language, and its file in `tests/fixtures/collection/md/procedures/`
- **THEN** front matter, `date` and `lastmod`, headings, Reagents rows and section texts agree as stated above

#### Scenario: The agreement check (checker)
- **WHEN** a test gives the agreement check an Org source and a Markdown procedure that agree except that the Markdown text is wrapped at other columns and writes the Org source's `/italic/` as `*italic*`, then the same Markdown procedure with, in turn, one word of a section changed, `C=O` in a section written `CO`, `E/Z` in a section written `EZ`, one Reagents cell changed, one heading renamed, `lastmod` one minute later, the `+02:00` offset of a summer `date` written `+01:00`, and an extra front-matter key
- **THEN** it accepts the first and rejects each of the others

#### Scenario: The agreement check (checker, no AI model)
- **WHEN** a test gives the agreement check that Org source without its `#+AI_MODEL` line, first with the agreeing Markdown procedure without its `ai_model` line, then with the agreeing Markdown procedure unchanged
- **THEN** it accepts the first and rejects the second

#### Scenario: The suite runs without Emacs
- **WHEN** the orchestrator runs `python3 -m pytest tests` with a `PATH` that holds no `emacs` but every other tool the suite uses, with the ox-hugo and Pagefind caches present (manual verification, tasks.md section 5)
- **THEN** the suite passes, and every skipped test exercises the Org export and skips with a reason that names `emacs`
