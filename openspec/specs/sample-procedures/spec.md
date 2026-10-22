# sample-procedures Specification

## Purpose
Define the sample procedures shipped as the demo collection `examples/demo/`: their marking as sample data, benign textbook chemistry, and quantities that agree with each other.

## Requirements

### Requirement: Seed procedures
The repository SHALL ship at least these two seed procedures, linked as precursor and product across the two source trees:
- `org/procedures/OSDB-0001-salicylic-acid.org`: salicylic acid by hydrolysis of methyl salicylate with aqueous sodium hydroxide, then acidification. `reaction_types` is `["hydrolysis"]`, and the product is salicylic acid (C7H6O3, MW 138.12, CAS `69-72-7`).
- `md/procedures/OSDB-0002-aspirin.md`: acetylsalicylic acid by acetylation of salicylic acid with acetic anhydride and a phosphoric acid catalyst. `reaction_types` is `["acylation"]`, the product is acetylsalicylic acid (C9H8O4, MW 180.16, CAS `50-78-2`), and `precursors` is `["OSDB-0001"]`.

#### Scenario: Seeds exist with their link
- **WHEN** a test reads the two seed files, taking the Org seed's custom-front-matter lines from the source
- **THEN** both exist, their `id` values are `OSDB-0001` and `OSDB-0002`, their reaction types are `hydrolysis` and `acylation`, and the Markdown seed's `precursors` is `["OSDB-0001"]`

### Requirement: Sample marking
Every sample procedure SHALL have `status = "draft"` and `sample-data` among its `tags`. Its `authors` are fictitious names of the form `<Initial>. Example`, and it names the model that wrote it:
- Org sources carry `#+AI_MODEL` set to the writing model's exact identifier, never `none`.
- Markdown sources carry `ai_model` set to the same kind of identifier.

The Summary section states that the procedure is sample data whose quantities are not experimentally verified.

#### Scenario: Seeds are marked as samples
- **WHEN** a test reads every sample procedure
- **THEN** each has `status` equal to `draft` and `sample-data` in its tags, every author matches `^[A-Z]\. Example$`, and its `#+AI_MODEL` or `ai_model` is present and is not `none`
- **AND** its Summary section contains `not experimentally verified`

### Requirement: Benign textbook chemistry
Every sample procedure SHALL describe a well-known textbook reaction suitable for an undergraduate teaching laboratory, and nothing energetic, highly toxic, controlled or dual-use. Its `references` cite only real, published sources, without page numbers or details that cannot be checked. Its `hazards` and its "Hazards and Waste Disposal" section name the main hazards of the reagents and the product.

#### Scenario: Review before archive
- **WHEN** the orchestrator reviews each sample procedure before archiving this change
- **THEN** the reaction, reagents and conditions are textbook-standard and benign, and every citation names a real published source

### Requirement: Quantities agree
Every sample procedure's Reagents table SHALL have the columns `Reagent | CAS | MW (g/mol) | Amount | mmol | Equiv`, and its numbers SHALL agree with each other and with the front matter. A row whose `mmol` or `Equiv` is `cat.` is a catalyst and is exempt from the rules below.
- **Mass and moles.** Where `Amount` begins with a mass `<number> g`, `mmol` equals `1000 × mass / MW` within 1 %.
- **Limiting reagent.** Exactly one row has `Equiv` `1.0`. Every other row's `Equiv` equals its `mmol` divided by that row's `mmol`, within 0.05.
- **Scale.** When `scale` is given in `mmol`, its number equals the limiting row's `mmol` within 1 %.
- **Product weight.** `product.mw` equals the formula weight of `product.formula`, computed from standard atomic weights (C 12.011, H 1.008, N 14.007, O 15.999, Na 22.990, P 30.974, S 32.06, Cl 35.45, K 39.098, Br 79.904), within 0.02 g/mol.
- **CAS numbers.** Every CAS number in the table passes the CAS check-digit rule.

#### Scenario: Seed tables are consistent
- **WHEN** a test parses the Reagents table of every sample procedure (an Org table or a Markdown pipe table, in the source file) and applies the rules above
- **THEN** every rule holds for every row

### Requirement: Samples validate and export cleanly
The sample procedures SHALL produce no validator problem line at all, neither error nor warning, both as sources and after export.

#### Scenario: Clean validation of the shipped tree
- **WHEN** an integration test runs `tools/orgsyndb -C <copy of examples/demo> validate`
- **THEN** it exits 0, and no line of the form `<path>:<field>: <severity>: <message>` is printed

### Requirement: Theme sample set
The repository SHALL ship, besides the two seeds, these six sample procedures:

| File | Product | Reaction type | Precursors |
|---|---|---|---|
| `org/procedures/OSDB-0003-isopentyl-acetate.org` | isopentyl acetate (C7H14O2, CAS `123-92-2`), by Fischer esterification of isopentyl alcohol with acetic acid | `esterification` | none |
| `org/procedures/OSDB-0004-4-acetylbiphenyl.org` | 4-acetylbiphenyl (C14H12O, CAS `92-91-1`), by Suzuki coupling of 4′-bromoacetophenone with phenylboronic acid | `cross-coupling` | none |
| `org/procedures/OSDB-0005-1-biphenyl-4-yl-ethanol.org` | 1-(biphenyl-4-yl)ethanol (C14H14O, CAS `3562-73-0`), by sodium borohydride reduction of 4-acetylbiphenyl | `reduction` | `OSDB-0004` |
| `org/procedures/OSDB-0006-dibenzylideneacetone.org` | dibenzylideneacetone (C17H14O, CAS `538-58-9`), by Claisen–Schmidt condensation of benzaldehyde with acetone | `aldol-condensation` | none |
| `org/procedures/OSDB-0007-ethyl-cinnamate.org` | ethyl (E)-cinnamate (C11H12O2, CAS `103-36-6`), by Wittig olefination of benzaldehyde with ethyl (triphenylphosphoranylidene)acetate | `olefination` | none |
| `md/procedures/OSDB-0008-cinnamic-acid.md` | (E)-cinnamic acid (C9H8O2, CAS `140-10-3`), by saponification of ethyl (E)-cinnamate with aqueous sodium hydroxide in ethanol, then acidification with hydrochloric acid | `hydrolysis` | `OSDB-0007` |

The full set meets the following:
- **Counts.** There are exactly six Org and two Markdown sample procedures, with at least five distinct reaction types among them.
- **Product CAS.** Every sample's `product` has a `cas` that resolves to that product on PubChem. The orchestrator checks this during review, because the tests cannot reach the network.
- **Tags.** Every sample has at least one tag besides `sample-data`.
- **Structure image.** OSDB-0003 sets `structure_image = "structures/osdb-0003.svg"`.
- **Chains.** Besides the seeds' OSDB-0001 → OSDB-0002, OSDB-0004 → OSDB-0005 and OSDB-0007 → OSDB-0008 are precursor chains. No procedure needs both a precursor and a used-in link.
- **Long sample.** OSDB-0004 is the long sample: at least 15 numbered steps under `Procedure` and at least 6 numbered notes under `Notes`. Its Reagents table holds at least four non-catalyst rows, and the longest cell text of its `Reagent` column has at least 40 characters.

#### Scenario: Set, counts and chain
- **WHEN** a test reads every sample procedure
- **THEN** the files above exist with those IDs, reaction types and precursors, there are six Org and two Markdown samples, and at least five distinct reaction types
- **AND** every product has a `cas` that passes the check-digit rule, and every sample has a tag besides `sample-data`

#### Scenario: Structure image is set
- **WHEN** a test reads `org/procedures/OSDB-0003-isopentyl-acetate.org`
- **THEN** its custom-front-matter lines set `structure_image` to `structures/osdb-0003.svg`, and `static/structures/osdb-0003.svg` exists

#### Scenario: Long sample
- **WHEN** a test reads `org/procedures/OSDB-0004-4-acetylbiphenyl.org`
- **THEN** its `Procedure` section has at least 15 numbered items, its `Notes` section at least 6, and its Reagents table at least four rows whose `mmol` is not `cat.`, one of them with a `Reagent` cell of at least 40 characters

### Requirement: Demo collection
The sample procedures SHALL form the demo collection `examples/demo/` of the application, a complete collection as the `collection` capability defines it, with the structure images in `examples/demo/static/structures/`. Every path that this capability names under `org/procedures/` or `md/procedures/` is relative to `examples/demo/`. The application's own root holds no `org/`, `md/` or `site/static/` directory.

#### Scenario: Samples live in the demo collection
- **WHEN** a test inspects the application
- **THEN** `examples/demo/orgsyndb.toml` exists, `examples/demo/org/procedures/OSDB-0001-salicylic-acid.org` and `examples/demo/md/procedures/OSDB-0002-aspirin.md` exist, and neither `org/`, `md/` nor `site/static/` exists at the application root
