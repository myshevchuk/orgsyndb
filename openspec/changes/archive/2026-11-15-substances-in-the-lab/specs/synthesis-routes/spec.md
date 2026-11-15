## ADDED Requirements

### Requirement: Routes in the lab
The lab application SHALL draw a substance's route tree from the collection's procedures it keeps (collection-import "Imported rows"), by the rules of Derived routes with the depth 6 and the step budget 200. A step to a substance is a specific procedure that is not withdrawn whose entry is not withdrawn and has the substance among its products, or such an entry of a general procedure that is not withdrawn, numbered by its position; it starts from the entry's substrates in their order, and its yield is the product's. A substance has a route tree exactly when its tree goes past one step, and the tree is the list of the steps the substance keeps, as Derived routes writes it.

#### Scenario: Routes of the demo data
- **WHEN** the demo data set is written and a test draws the route tree of every substance in the lab
- **THEN** exactly `acetylsalicylic-acid`, `1-biphenyl-4-yl-ethanol` and `cinnamic-acid` have one
- **AND** the tree of `acetylsalicylic-acid` is the one step `OSDB-0002` with the yield 75, starting from `salicylic-acid`, expanded with the one step `OSDB-0001` at 80 that starts from `methyl-salicylate`, a plain leaf, and from `acetic-anhydride`, a plain leaf
- **AND** the tree of `1-biphenyl-4-yl-ethanol` holds `OSDB-0005` at 90 and entry 1 of `OSDB-0009` at 90, in that order, each starting from `4-acetylbiphenyl`, expanded with `OSDB-0004` at 85

#### Scenario: A protection and its removal in the lab
- **WHEN** the lab keeps three specific procedures, `OSDB-0001` making `b` from `a`, `OSDB-0002` making `a` from `b` and `OSDB-0003` making `c` from `b`, and a test draws the route trees of `a`, `b` and `c`
- **THEN** only `c` has one: `OSDB-0003` starting from `b`, expanded with the one step `OSDB-0001`, which starts from `a`, a plain leaf

#### Scenario: Withdrawn procedures leave the tree
- **WHEN** the demo data set is written, `OSDB-0007` is withdrawn, and a test draws the route tree of `cinnamic-acid`
- **THEN** it has none

#### Scenario: The budget in the lab
- **WHEN** the lab keeps a general procedure `OSDB-0001` of seven entries, entry `n` making `chain-<n>` from `chain-<n-1>`, and a test draws the route tree of `chain-7`
- **THEN** it nests six steps, for the entries 7 down to 2, and `chain-1` under the innermost is cut off with no steps
