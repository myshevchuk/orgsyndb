## ADDED Requirements

<!-- "Sample procedure" is defined in the sample-procedures spec: a file in
org/procedures/ or md/procedures/ whose tags include sample-data. Values of
an Org source are read from its #+HUGO_TAGS and custom-front-matter lines, as
tests/sample_support.py already does. The existing requirements "Sample
marking", "Benign textbook chemistry", "Quantities agree" and "Samples
validate and export cleanly" apply to these samples unchanged. -->

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
- **THEN** its custom-front-matter lines set `structure_image` to `structures/osdb-0003.svg`, and `site/static/structures/osdb-0003.svg` exists

#### Scenario: Long sample
- **WHEN** a test reads `org/procedures/OSDB-0004-4-acetylbiphenyl.org`
- **THEN** its `Procedure` section has at least 15 numbered items, its `Notes` section at least 6, and its Reagents table at least four rows whose `mmol` is not `cat.`, one of them with a `Reagent` cell of at least 40 characters
