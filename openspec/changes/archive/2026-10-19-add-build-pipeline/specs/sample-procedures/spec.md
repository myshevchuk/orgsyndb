## ADDED Requirements

<!-- These requirements are written for every procedure tagged sample-data,
so the samples change 3 adds are held to them by the same tests. "Sample
procedure" means a file in org/procedures/ or md/procedures/ whose tags
include sample-data; for an Org source the tags are read from #+HUGO_TAGS
and the other values from its export or its custom-front-matter lines. -->

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
- **WHEN** an integration test runs `tools/orgsyndb validate` on the repository's own `org/procedures/` and `md/procedures/`
- **THEN** it exits 0, and no line of the form `<path>:<field>: <severity>: <message>` is printed
