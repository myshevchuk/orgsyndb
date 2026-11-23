## MODIFIED Requirements

### Requirement: Quantities agree
Every sample procedure's Reagents table SHALL have the columns `Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv`, or `Reagenz | CAS | M (g/mol) | Menge | mmol | Äquiv.` in a German sample, and its numbers SHALL agree with each other and with the front matter. A German table may write decimal commas. A row whose `mmol` or `Equiv` is `cat.` (German `kat.`) is a catalyst, and a row whose `mmol` and `Equiv` are both `–` is a solvent or an auxiliary such as a drying agent; both are exempt from the rules below but the last.
- **Mass and moles.** Where `Amount` begins with a mass `<number> g`, `mmol` equals `1000 × mass / MW` within 1 %.
- **Limiting reagent.** Exactly one row has `Equiv` `1.0`. Every other row's `Equiv` equals its `mmol` divided by that row's `mmol`, within 0.05.
- **Scale.** When `scale` is given in `mmol`, its number equals the limiting row's `mmol` within 1 %.
- **Compound weights.** The `mw` of every substance of the demo registry that has a `formula` and an `mw` equals the formula weight of its `formula`, computed from standard atomic weights (Li 6.94, B 10.81, C 12.011, H 1.008, N 14.007, O 15.999, Na 22.990, Mg 24.305, P 30.974, S 32.06, Cl 35.45, K 39.098, Fe 55.845, Cu 63.546, Br 79.904, Pd 106.42, I 126.904), within 0.02 g/mol.
- **CAS numbers.** Every CAS number in the table passes the CAS check-digit rule.

#### Scenario: Seed tables are consistent
- **WHEN** a test parses the Reagents table of every sample procedure, in either language (an Org table or a Markdown pipe table, in the source file), reads every compound file of the demo registry, and applies the rules above
- **THEN** every rule holds for every row and every compound

#### Scenario: Translated sample tables are consistent (checker)
- **WHEN** a test gives the checker a German table with decimal commas, `kat.` rows and a solvent row of `–`, then the same table with a wrong `mmol`, then an English table under a German file name, then the first table with a solvent row whose CAS fails the check digit
- **THEN** it accepts the first and rejects the other three

<!-- Reason: the counts are of the English originals. -->

### Requirement: Theme sample set
The repository SHALL ship, besides the two seeds, these six sample procedures, among others of its choosing:

| File | Product | Reaction type | Substrates |
|---|---|---|---|
| `org/procedures/OSDB-0003-isopentyl-acetate.org` | `isopentyl-acetate` (C7H14O2, CAS `123-92-2`), by Fischer esterification of isopentyl alcohol with acetic acid | `esterification` | `isopentyl-alcohol`, `acetic-acid` |
| `org/procedures/OSDB-0004-4-acetylbiphenyl.org` | `4-acetylbiphenyl` (C14H12O, CAS `92-91-1`), by Suzuki coupling of 4′-bromoacetophenone with phenylboronic acid | `cross-coupling` | `4-bromoacetophenone`, `phenylboronic-acid` |
| `md/procedures/OSDB-0005-1-biphenyl-4-yl-ethanol.md` | `1-biphenyl-4-yl-ethanol` (C14H14O, CAS `3562-73-0`), by sodium borohydride reduction of 4-acetylbiphenyl | `reduction` | `4-acetylbiphenyl` |
| `md/procedures/OSDB-0006-dibenzylideneacetone.md` | `dibenzylideneacetone` (C17H14O, CAS `538-58-9`), by Claisen–Schmidt condensation of benzaldehyde with acetone | `aldol-condensation` | `benzaldehyde`, `acetone` |
| `org/procedures/OSDB-0007-ethyl-cinnamate.org` | `ethyl-cinnamate`, ethyl (E)-cinnamate (C11H12O2, CAS `103-36-6`), by Wittig olefination of benzaldehyde with ethyl (triphenylphosphoranylidene)acetate | `olefination` | `benzaldehyde`, `ethyl-triphenylphosphoranylidene-acetate` |
| `md/procedures/OSDB-0008-cinnamic-acid.md` | `cinnamic-acid`, (E)-cinnamic acid (C9H8O2, CAS `140-10-3`), by saponification of ethyl (E)-cinnamate with aqueous sodium hydroxide in ethanol, then acidification with hydrochloric acid | `hydrolysis` | `ethyl-cinnamate` |

Each procedure has the one product its row names, with the yield its previous front matter gave. The full set meets the following:
- **Formats.** The samples without a language code are Org and Markdown procedures, the four Org samples named here among the Org ones and the general procedure of the requirement "Demo general procedure" among the Markdown ones, with at least five distinct reaction types among them.
- **Compound CAS.** Every substance of the demo registry that a sample names has a `cas` that resolves to that compound on PubChem. The orchestrator checks this during review, because the tests cannot reach the network.
- **Tags.** Every sample has at least one tag besides `sample-data`.
- **Structure image.** The demo registry gives every substance with a SMILES a molfile, and `webapp/demo/substances/isopentyl-acetate/structure.svg`, beside the registry, holds the drawn image of `isopentyl-acetate` for builds from the registry file (compound-registry "Structure images"). The demo collection's `static/structures/` holds no file named after a substance.
- **Chains.** Besides the seeds' OSDB-0001 → OSDB-0002 through `salicylic-acid`, OSDB-0004 → OSDB-0005 and OSDB-0004 → OSDB-0009 through `4-acetylbiphenyl`, and OSDB-0007 → OSDB-0008 through `ethyl-cinnamate`, are chains: the first procedure makes the compound and the second starts from it. Each of these chains leads from an Org procedure to a Markdown one. Any sample may start from a compound another sample makes, and a procedure may both start from one sample's product and make another's substrate.
- **Long sample.** OSDB-0004 is the long sample: at least 15 numbered steps under `Procedure` and at least 6 numbered notes under `Notes`. Its Reagents table holds at least four non-catalyst rows, and the longest cell text of its `Reagent` column has at least 40 characters.

#### Scenario: Set, counts and chain
- **WHEN** a test reads every sample procedure
- **THEN** the files above exist with those IDs, reaction types, products and substrates, the samples are Org and Markdown procedures with at least five distinct reaction types
- **AND** in each chain named above the procedure making the compound is an Org file and the one starting from it a Markdown file
- **AND** every substance of the demo registry that a sample names has a `cas` that passes the check-digit rule, and every sample has a tag besides `sample-data`

#### Scenario: Structure image is present
- **WHEN** a test reads the demo registry, the files beside it and the demo collection's static files
- **THEN** every substance with a `smiles` has a `molfile` string and `new-compound-7` the `molfile` `null`, `webapp/demo/substances/` holds exactly `isopentyl-acetate/structure.svg`, and no file of `examples/demo/static/structures/` is named `<key>.svg` or `<key>.png` for a substance's key

#### Scenario: Long sample
- **WHEN** a test reads `org/procedures/OSDB-0004-4-acetylbiphenyl.org`
- **THEN** its `Procedure` section has at least 15 numbered items, its `Notes` section at least 6, and its Reagents table at least four rows whose `mmol` is not `cat.`, one of them with a `Reagent` cell of at least 40 characters

### Requirement: Demo collection
The sample procedures SHALL form the demo collection `examples/demo/` of the application, a complete collection as the `collection` capability defines it, with the scheme image of its general procedure in `examples/demo/static/structures/` and the sequences in `examples/demo/md/sequences/`. Its registry is the lab demo's, `webapp/demo/registry.json`, which its `orgsyndb.toml` names as `registry = "../../webapp/demo/registry.json"` (compound-registry "Registry source"), with the structure images of its substances beside it in `webapp/demo/substances/` (compound-registry "Structure images"). The registry holds a substance for every compound a sample names, as product or substrate, and for every chemical of a sample's Reagents table (Reagents in the registry); `new-compound-7`, the lab demo's article `NV-0007` (lab-demo "Demo inventory"); and commercial chemicals that no sample names, each with the group `reagents` or `starting-materials`. Every substance has a `name_de`. Every path that this capability names under `org/procedures/` or `md/procedures/` is relative to `examples/demo/`. The application's own root holds no `org/`, `md/` or `site/static/` directory, and the demo holds no `compounds/` and no `vocabularies/`.

The demo registry gives the registry fields values of every kind (compound-fields "Registry fields"):
- **Vocabularies.** Every term of each vocabulary has a `label_de`, and every reaction type a sample procedure names is a reaction type of the registry. Some chemical class has two ancestors. The groups are `purchased` (`Purchased`, `Zugekauft`), with `starting-materials` (`Starting materials`, `Ausgangsstoffe`) and `reagents` (`Reagents`, `Reagenzien`) filed under it, and `synthesised` (`Synthesised`, `Selbst hergestellt`), with `intermediates` (`Intermediates`, `Zwischenprodukte`) and `final-products` (`Final products`, `Endprodukte`) filed under it.
- **Values.** Every substance has chemical classes and a group of `starting-materials`, `reagents`, `intermediates` or `final-products`, each of them had by some substance; a substance that a sample makes and another sample starts from has the group `intermediates` unless it has an article number. An article number is had by exactly the final products the lab demo delivers, among them `1-4-bromophenyl-ethanol` (`CH-0001`), `1-biphenyl-4-yl-ethanol` (`CH-0002`), `acetylsalicylic-acid` (`CH-0010`), `cinnamic-acid` (`CH-0012`), `dibenzylideneacetone` (`CH-0013`) and `isopentyl-acetate` (`CH-0016`), and by `new-compound-7` (`NV-0007`); each is of the form `CH-<nnnn>` but that of `new-compound-7`. At least one substance has two chemical classes, and at least one a class with two ancestors. Some substances have a `short_name` and some do not.

The demo also sets the journal fields (procedure-fields "Journal fields") and declares procedure fields of the other two types (procedure-fields "Procedure field declarations"):
- **Declarations.** `examples/demo/orgsyndb.toml` declares, in this order, `working_time` (`number`, `unit = "h"`, `min = 0`) and `inert_atmosphere` (`boolean`, `facet`), labelled `Working time` and `Arbeitszeit`, and `Inert atmosphere` and `Schutzgas`. Neither is `required`.
- **Notebooks.** The registry lists the notebooks `AE-1`, `AE-2`, `CE-1` and `CE-3` (lab-demo "Demo notebooks"), and every `notebook` a sample sets names one of them.
- **Vocabulary.** The registry's projects are `teaching` (`Teaching`, `Lehre`), with `first-year-practical` (`First-year practical`, `Grundpraktikum`) and `advanced-practical` (`Advanced practical`, `Fortgeschrittenenpraktikum`) filed under it, and `research` (`Research`, `Forschung`), with `biaryls` (`Biaryls`, `Biaryle`) and `cinnamates` (`Cinnamates`, `Zimtsäurederivate`) filed under it, and no other.
- **Values.** Every sample procedure, in either language and either format, the general procedure included, sets `notebook` and `project`, a `project` of `first-year-practical`, `advanced-practical`, `biaryls` or `cinnamates`, each of them set by some procedure; its language variants set the same values. Some procedures set `working_time` and some do not, and at least one `working_time` is not a whole number. `inert_atmosphere` is `true` for at least one procedure of a research project, `false` for at least one procedure, and unset for at least one. `OSDB-0002` sets `notebook = "AE-1/2"`, `project = "first-year-practical"`, `working_time = 2.5` and `inert_atmosphere = false`.

#### Scenario: Samples live in the demo collection
- **WHEN** a test inspects the application
- **THEN** `examples/demo/orgsyndb.toml` exists, `examples/demo/org/procedures/OSDB-0001-salicylic-acid.org` and `examples/demo/md/procedures/OSDB-0002-aspirin.md` exist, every key the samples name is a substance of the demo registry, every substance of the registry is named by a sample, carries the CAS number of a sample's Reagents row or is `new-compound-7`, or has the group `reagents` or `starting-materials`, and some substance of those groups is named by no sample, neither `examples/demo/compounds/` nor `examples/demo/vocabularies/` exists, and neither `org/`, `md/` nor `site/static/` exists at the application root

#### Scenario: The demo's registry and fields
- **WHEN** a test reads `examples/demo/orgsyndb.toml`, the demo registry and the demo's sample procedures
- **THEN** the declarations, the vocabularies, the substances' values and the procedures' values meet the rules above

### Requirement: German sample translations
Every sample procedure SHALL have a German variant beside it, in the same format, named with `.de` before the suffix (for example `org/procedures/OSDB-0001-salicylic-acid.de.org` and `md/procedures/OSDB-0002-aspirin.de.md`). Each translation meets the localization spec, carries the same `authors` as its original, has a Reagents table with as many rows as the original's, and writes decimal commas in its text and table. The German long sample has at least 15 numbered steps under `Durchführung` and at least 6 numbered notes under `Anmerkungen`.

#### Scenario: Every sample has a German translation
- **WHEN** a test reads each sample and its `.de` twin
- **THEN** the twin exists, has the same `id`, `status`, `reaction_types`, `tags`, `products`, `substrates` and `authors`, and as many table rows
- **AND** the German OSDB-0004 has at least 15 steps and 6 notes

### Requirement: Test collection
The repository SHALL ship the test collection `tests/fixtures/collection/`, a complete collection as the `collection` capability defines it that holds every sample procedure of the demo collection, in either language, as a Markdown procedure, and that has no `org/` directory. The paths in this requirement are written out in full. The test collection meets all of the following:
- **Copies.** `tests/fixtures/collection/.gitignore` and every file under `tests/fixtures/collection/static/` and `tests/fixtures/collection/md/sequences/` are byte-identical to the demo collection's files at the same relative paths, and the test collection's `static/` and `md/sequences/` hold no other file. `tests/fixtures/collection/substances/` holds the paths `webapp/demo/substances/` holds, each byte-identical to the demo's, and no other file. `tests/fixtures/collection/registry.json` is the demo registry, `webapp/demo/registry.json`, with the test fixtures' fictitious accounts added to its `accounts` and its `digest` made to agree, and `tests/fixtures/collection/orgsyndb.toml` is the demo's with `registry = "registry.json"` in place of its `registry`. The test collection has no `compounds/` and no `vocabularies/`.
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
- **THEN** `.gitignore` and every file under `static/` are byte-identical to the demo's, `static/structures/aryl-ketone-reduction.svg` among them, every file under `substances/` is byte-identical to the one at its path under `webapp/demo/substances/`, and the two hold the same paths, `registry.json` equals the demo registry but for its `accounts`, which add the test fixtures' fictitious accounts to the demo's, and its `digest`, `orgsyndb.toml` differs from the demo's only in `registry`, and no `org/` directory exists
- **AND** `md/procedures/` holds exactly the file names derived from the demo's sample procedure files, and the file for each Markdown sample file is byte-identical to it

#### Scenario: Converted samples agree with their Org sources
- **WHEN** a test reads each Org sample of the demo collection, in either language, and its file in `tests/fixtures/collection/md/procedures/`
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

### Requirement: Demo sequences
The demo collection SHALL ship synthesis sequences, each in English and with a German variant (`.de`) sharing its `target` and `steps`: these two among them, and among the others sequences of three and of four steps. Each sequence's target is a substance with an article number, and each of its steps but the first starts from the product of the step before it:
- `md/sequences/SEQ-0001-aspirin-from-wintergreen.md`: "Aspirin from oil of wintergreen", the steps OSDB-0001 and OSDB-0002, the target `acetylsalicylic-acid`; its notes say that the salicylic acid is dried before the acetylation;
- `md/sequences/SEQ-0002-biphenylyl-ethanol.md`: "1-(Biphenyl-4-yl)ethanol from 4′-bromoacetophenone", the steps OSDB-0004 and entry 1 of OSDB-0009, the target `1-biphenyl-4-yl-ethanol`.

All validate cleanly with the demo's procedures and registry, and their German variants are written in German. A substance that one step of a sequence makes and the next starts from has the group `intermediates`.

#### Scenario: The demo's sequences
- **WHEN** a test reads `examples/demo/md/sequences/` and validates a copy of the demo collection
- **THEN** it holds the two sequences and their `.de` variants with the stated steps and targets, a sequence of three steps and one of four, every sequence with a `.de` variant sharing its steps and target and its steps chained as stated, and validation prints no problem line

## ADDED Requirements

### Requirement: Reagents in the registry
Every chemical that a sample procedure's text uses, water, ice and the inert gas of a protective atmosphere excepted, SHALL be a row of its Reagents table: the substrates, reagents and catalysts, the solvents of the reaction and of the workup, and the acids, bases, salts and drying agents of the workup. A solution is listed as its solute, such as hydrochloric acid as hydrogen chloride, with the concentration in `Amount`. The CAS number of every row is the `cas` of exactly one substance of the demo registry, and a German table has the same rows with the same CAS numbers as its original.

#### Scenario: Every row is a registry substance
- **WHEN** a test parses the Reagents table of every sample procedure, in either language, and reads the demo registry
- **THEN** every row's CAS number is the `cas` of exactly one substance, and each German table lists the CAS numbers of its original in the same order

#### Scenario: Review of the tables
- **WHEN** the orchestrator reviews each sample procedure before archiving this change
- **THEN** every chemical its text uses, water, ice and inert gas excepted, is a row of its Reagents table
