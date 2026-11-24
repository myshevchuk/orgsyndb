## Context

The demo collection (`examples/demo/`), its registry
(`webapp/demo/registry.json`) and the lab demo data set
(`webapp/demo/data.py`, `seed.py`) are one invented lab. The test
collection (`tests/fixtures/collection/`) mirrored the demo. The
requirements fix the demo's contents closely, by counts and lists; this
change loosens the lists where they would block growth and keeps every
named fact that other tests rely on.

## Goals / Non-Goals

**Goals:** a demo large enough to show the stock split by category
(end products, self-made intermediates, commercial chemicals) and
multi-step routes; every chemical a procedure uses traceable through
its CAS number to a registry substance that the inventory holds.

**Non-Goals:** the category views themselves; volume units; new
fields on vessels; experimentally correct quantities.

## Decisions

### Rules, not counts

The requirements name what other requirements and tests build on: the
seeds, the theme samples, the general procedure, `SEQ-0001`,
`SEQ-0002`, the six delivered articles and `NV-0007`. Everything else
is stated as a rule that each further sample, substance, sequence or
article meets, or as a minimum that growth cannot break. Adding a
procedure or a commercial chemical to the demo then needs no change to
the requirements.

### New samples are Markdown

The new samples are Markdown, the simpler of the two source formats to
write and check. The four Org samples stay as they are and keep
showing the Org export.

### A fixed test collection

The test collection is the fixture that build, site, search and
localization tests build. Had it kept mirroring the demo, each new
demo procedure would change the scenarios of those capabilities and
slow their tests. It holds the nine named samples, `SEQ-0001`,
`SEQ-0002` and a registry of the substances they name; the demo grows
without it. Scenarios that read the demo itself, such as its manifest,
its routes and the IDs issued after its import, name the demo's facts
or derive their values from its highest IDs.

### Chemicals are matched by CAS number

A Reagents row names a chemical by its name in the procedure's
language and its CAS number. The CAS number is the key into the
registry, because the name differs between languages and between
procedures (`NaOH`, `sodium hydroxide`, `Natronlauge`). A solution is
listed as its solute, so that `2 M hydrochloric acid` and `conc.
hydrochloric acid` both lead to the one substance `hydrogen-chloride`
and the one bottle in the inventory.

### Solvent and auxiliary rows

A solvent or a drying agent has no meaningful equivalents. Its row
writes `–` for `mmol` and `Equiv`, which exempts it from the quantity
rules as `cat.` exempts a catalyst. Its `Amount` is a volume or a mass
as the text uses it. Mixtures without a formula, such as petroleum
ether, are substances with a CAS number and no formula; the weight rule
applies only to substances with both.

### Liquids are weighed

Vessels know `mg`, `g`, `µmol` and `mmol`. A bottle of acetone is
entered as its mass. Volume units are deferred with the category views.

### Generated files

Molfiles are drawn from SMILES with RDKit, as the existing ones were
(`RDKit 2D` header). The registry's `digest` is recomputed by the
snapshot code, and `webapp/demo/manifest.json` is the output of
`tools/orgsyndb manifest` for the demo collection.

## Risks / Trade-offs

- A cheap model writes most of the chemistry → a second Codex model
  checks compounds, structures, CAS numbers and relations, and the
  orchestrator spot-checks CAS numbers against PubChem.
- Many tests read the demo or the test collection and may count their
  contents → they are brought to the new counts in the test stage, not
  by the data's author.
